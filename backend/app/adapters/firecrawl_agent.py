"""Firecrawl Agent API for attribute research."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.models.db import ProductAttribute
from app.observability.run_usage import log_external_cost
from app.research.prompts import build_firecrawl_agent_prompt, build_firecrawl_agent_schema

logger = logging.getLogger(__name__)

FIRECRAWL_AGENT_URL = "https://api.firecrawl.dev/v2/agent"
VALID_MODELS = frozenset({"spark-1-mini", "spark-1-pro"})


class FirecrawlAgentError(RuntimeError):
    pass


def normalize_firecrawl_model(engine_model: str) -> str:
    cleaned = engine_model.strip().lower()
    if cleaned in VALID_MODELS:
        return cleaned
    return get_settings().wabash_default_firecrawl_model


def _format_http_error(exc: httpx.HTTPStatusError) -> str:
    detail = exc.response.text.strip()
    try:
        payload = exc.response.json()
        if isinstance(payload, dict):
            detail = payload.get("error") or payload.get("detail") or payload.get("message") or detail
            if isinstance(detail, dict):
                detail = detail.get("message") or detail.get("detail") or str(detail)
    except Exception:
        pass
    return f"Firecrawl API error ({exc.response.status_code}): {detail or exc.response.reason_phrase}"


class FirecrawlAgentClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or get_settings().firecrawl_api_key

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        if not self.configured:
            raise FirecrawlAgentError("FIRECRAWL_API_KEY is not configured")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def research_product(
        self,
        *,
        manufacturer_name: str,
        manufacturer_product_number: str,
        model: str,
        attributes: list[ProductAttribute],
    ) -> dict[str, Any]:
        settings = get_settings()
        model = normalize_firecrawl_model(model)
        if model not in VALID_MODELS:
            raise FirecrawlAgentError(
                f"Unsupported Firecrawl model '{model}'. Use one of: {', '.join(sorted(VALID_MODELS))}."
            )

        body = {
            "prompt": build_firecrawl_agent_prompt(
                manufacturer_name=manufacturer_name,
                manufacturer_product_number=manufacturer_product_number,
                attributes=attributes,
            ),
            "model": model,
            "schema": build_firecrawl_agent_schema(attributes=attributes),
            "maxCredits": settings.firecrawl_agent_max_credits,
        }

        job_id = await self._start_agent(body)
        result_payload = await self._wait_for_result(job_id)
        data = self._extract_output_content(result_payload)

        credits_used = result_payload.get("creditsUsed")
        if isinstance(credits_used, (int, float)) and credits_used > 0:
            log_external_cost(
                service="firecrawl",
                phase=f"agent-{model}",
                units=int(credits_used),
                unit_cost_usd=settings.firecrawl_usd_per_credit,
            )
        else:
            log_external_cost(
                service="firecrawl",
                phase=f"agent-{model}",
                units=1,
                unit_cost_usd=settings.firecrawl_agent_cost_usd,
            )

        return data

    async def _start_agent(self, body: dict[str, Any]) -> str:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(min=1, max=8),
            retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
            reraise=True,
        ):
            with attempt:
                try:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.post(
                            FIRECRAWL_AGENT_URL,
                            headers=self._headers(),
                            json=body,
                        )
                    response.raise_for_status()
                    payload = response.json()
                except httpx.HTTPStatusError as exc:
                    raise FirecrawlAgentError(_format_http_error(exc)) from exc
                except Exception as exc:
                    raise FirecrawlAgentError(str(exc)) from exc

                if not isinstance(payload, dict) or not payload.get("success"):
                    raise FirecrawlAgentError("Firecrawl agent start did not return success")
                job_id = payload.get("id")
                if not job_id:
                    raise FirecrawlAgentError("Firecrawl agent start did not return job id")
                return str(job_id)

        raise FirecrawlAgentError("Firecrawl agent start exhausted retries")

    async def _wait_for_result(self, job_id: str) -> dict[str, Any]:
        settings = get_settings()
        timeout_sec = min(max(settings.max_run_seconds - 15, 120), 3600)
        poll_interval_sec = settings.firecrawl_agent_poll_interval_sec
        url = f"{FIRECRAWL_AGENT_URL}/{job_id}"
        deadline = time.monotonic() + timeout_sec

        while True:
            if time.monotonic() >= deadline:
                raise FirecrawlAgentError(f"Firecrawl agent timed out after {timeout_sec}s")

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(url, headers=self._headers())
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPStatusError as exc:
                raise FirecrawlAgentError(_format_http_error(exc)) from exc
            except Exception as exc:
                raise FirecrawlAgentError(str(exc)) from exc

            if not isinstance(payload, dict):
                raise FirecrawlAgentError("Firecrawl agent status was not a JSON object")

            status = payload.get("status")
            if status == "completed":
                if not payload.get("success", True):
                    raise FirecrawlAgentError(payload.get("error") or "Firecrawl agent completed with success=false")
                return payload
            if status == "failed":
                raise FirecrawlAgentError(payload.get("error") or "Firecrawl agent job failed")
            if status == "cancelled":
                raise FirecrawlAgentError("Firecrawl agent job was cancelled")

            await asyncio.sleep(poll_interval_sec)

    @staticmethod
    def _extract_output_content(result_payload: dict[str, Any]) -> dict[str, Any]:
        data = result_payload.get("data")
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            from app.research.json_utils import parse_json_object

            return parse_json_object(data)
        raise FirecrawlAgentError("Firecrawl agent returned no structured data")
