"""Parallel Task API for attribute research."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.observability.run_usage import log_external_cost
from app.research.prompts import build_parallel_task_input, build_parallel_task_spec

logger = logging.getLogger(__name__)

PARALLEL_TASK_RUNS_URL = "https://api.parallel.ai/v1/tasks/runs"
VALID_PROCESSORS = frozenset({"base", "core", "lite", "pro"})


class ParallelResearchError(RuntimeError):
    pass


def normalize_parallel_processor(engine_model: str) -> str:
    cleaned = engine_model.strip().lower()
    if cleaned.startswith("task-"):
        cleaned = cleaned[5:]
    if cleaned in VALID_PROCESSORS:
        return cleaned
    settings = get_settings()
    return settings.parallel_task_processor


def _format_http_error(exc: httpx.HTTPStatusError) -> str:
    detail = exc.response.text.strip()
    try:
        payload = exc.response.json()
        if isinstance(payload, dict):
            err = payload.get("error")
            if isinstance(err, dict):
                detail = err.get("message") or err.get("detail") or detail
            elif isinstance(err, str):
                detail = err
            else:
                detail = payload.get("detail") or payload.get("message") or detail
    except Exception:
        pass
    return f"Parallel API error ({exc.response.status_code}): {detail or exc.response.reason_phrase}"


class ParallelResearchClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or get_settings().parallel_api_key

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        if not self.configured:
            raise ParallelResearchError("PARALLEL_API_KEY is not configured")
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    async def research_product(
        self,
        *,
        manufacturer_name: str,
        manufacturer_product_number: str,
        processor: str,
    ) -> dict[str, Any]:
        settings = get_settings()
        processor = normalize_parallel_processor(processor)
        if processor not in VALID_PROCESSORS:
            raise ParallelResearchError(
                f"Unsupported Parallel processor '{processor}'. "
                f"Use one of: {', '.join(sorted(VALID_PROCESSORS))}."
            )

        body = {
            "processor": processor,
            "input": build_parallel_task_input(
                manufacturer_name=manufacturer_name,
                manufacturer_product_number=manufacturer_product_number,
            ),
            "task_spec": build_parallel_task_spec(),
        }

        run_id = await self._create_task_run(body)
        result_payload = await self._wait_for_result(run_id)

        log_external_cost(
            service="parallel",
            phase=f"task-{processor}",
            units=1,
            unit_cost_usd=settings.parallel_task_cost_usd,
        )

        return self._extract_output_content(result_payload)

    async def _create_task_run(self, body: dict[str, Any]) -> str:
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
                            PARALLEL_TASK_RUNS_URL,
                            headers=self._headers(),
                            json=body,
                        )
                    response.raise_for_status()
                    payload = response.json()
                except httpx.HTTPStatusError as exc:
                    raise ParallelResearchError(_format_http_error(exc)) from exc
                except Exception as exc:
                    raise ParallelResearchError(str(exc)) from exc

                run_id = payload.get("run_id") if isinstance(payload, dict) else None
                if not run_id:
                    raise ParallelResearchError("Parallel task create did not return run_id")
                return str(run_id)

        raise ParallelResearchError("Parallel task create exhausted retries")

    async def _wait_for_result(self, run_id: str) -> dict[str, Any]:
        settings = get_settings()
        timeout_sec = min(max(settings.max_run_seconds - 15, 60), 3600)
        url = f"{PARALLEL_TASK_RUNS_URL}/{run_id}/result"
        client_timeout = float(timeout_sec + 30)

        try:
            async with httpx.AsyncClient(timeout=client_timeout) as client:
                response = await client.get(
                    url,
                    headers=self._headers(),
                    params={"timeout": timeout_sec},
                )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 408:
                raise ParallelResearchError(
                    f"Parallel task timed out after {timeout_sec}s (run still active)"
                ) from exc
            raise ParallelResearchError(_format_http_error(exc)) from exc
        except Exception as exc:
            raise ParallelResearchError(str(exc)) from exc

        if not isinstance(payload, dict):
            raise ParallelResearchError("Parallel task result was not a JSON object")
        return payload

    @staticmethod
    def _extract_output_content(result_payload: dict[str, Any]) -> dict[str, Any]:
        run = result_payload.get("run")
        if isinstance(run, dict) and run.get("status") == "failed":
            err = run.get("error")
            message = err.get("message") if isinstance(err, dict) else str(err or "Task run failed")
            raise ParallelResearchError(message)

        output = result_payload.get("output")
        if not isinstance(output, dict):
            raise ParallelResearchError("Parallel task result missing output")

        content = output.get("content")
        if isinstance(content, dict):
            return content
        if isinstance(content, str):
            from app.research.json_utils import parse_json_object

            return parse_json_object(content)

        raise ParallelResearchError("Parallel task returned no structured JSON content")
