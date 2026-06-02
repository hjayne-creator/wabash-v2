"""Perplexity Agent API client."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.observability.run_usage import log_external_cost, log_llm_usage, monotonic_ms

logger = logging.getLogger(__name__)

PERPLEXITY_AGENT_URL = "https://api.perplexity.ai/v1/agent"

# Perplexity Agent API uses provider/model IDs (not OpenAI direct names).
MODEL_ALIASES: dict[str, str] = {
    "openai/gpt-4o-mini": "openai/gpt-5-mini",
    "gpt-4o-mini": "openai/gpt-5-mini",
    "openai/gpt-4o": "openai/gpt-5",
}


class PerplexityAgentError(RuntimeError):
    pass


def normalize_perplexity_model(model: str) -> str:
    cleaned = model.strip()
    if cleaned.startswith("preset:"):
        return cleaned
    return MODEL_ALIASES.get(cleaned, cleaned)


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
    return f"Perplexity API error ({exc.response.status_code}): {detail or exc.response.reason_phrase}"


class PerplexityAgentClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or get_settings().perplexity_api_key

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        if not self.configured:
            raise PerplexityAgentError("PERPLEXITY_API_KEY is not configured")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _extract_output_text(payload: dict[str, Any]) -> str:
        if payload.get("output_text"):
            return str(payload["output_text"])
        output = payload.get("output")
        if isinstance(output, list):
            parts: list[str] = []
            for item in output:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "message":
                    content = item.get("content")
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "output_text":
                                parts.append(str(block.get("text", "")))
                    elif isinstance(content, str):
                        parts.append(content)
            if parts:
                return "\n".join(parts)
        raise PerplexityAgentError("Perplexity response missing output text")

    async def research(
        self,
        *,
        model: str,
        input_text: str,
        instructions: str,
    ) -> tuple[str, dict[str, Any]]:
        model = normalize_perplexity_model(model)
        body: dict[str, Any] = {
            "input": input_text,
            "instructions": instructions,
            "stream": False,
        }
        price_model = model
        if model.startswith("preset:"):
            body["preset"] = model.removeprefix("preset:")
            price_model = f"preset:{body['preset']}"
        else:
            body["model"] = model

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(min=1, max=8),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        ):
            with attempt:
                started_at_ms = monotonic_ms()
                attempt_number = attempt.retry_state.attempt_number
                try:
                    async with httpx.AsyncClient(timeout=180.0) as client:
                        response = await client.post(
                            PERPLEXITY_AGENT_URL,
                            headers=self._headers(),
                            json=body,
                        )
                    response.raise_for_status()
                    payload = response.json()
                except httpx.HTTPStatusError as exc:
                    message = _format_http_error(exc)
                    log_llm_usage(
                        provider="perplexity",
                        model=price_model,
                        status="error",
                        attempt_number=attempt_number,
                        started_at_ms=started_at_ms,
                        error=message,
                    )
                    raise PerplexityAgentError(message) from exc
                except Exception as exc:
                    log_llm_usage(
                        provider="perplexity",
                        model=price_model,
                        status="error",
                        attempt_number=attempt_number,
                        started_at_ms=started_at_ms,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                    raise PerplexityAgentError(str(exc)) from exc

                usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
                pseudo_response = type(
                    "PerplexityUsage",
                    (),
                    {
                        "usage": type(
                            "U",
                            (),
                            {
                                "prompt_tokens": usage.get("input_tokens", usage.get("prompt_tokens", 0)),
                                "completion_tokens": usage.get("output_tokens", usage.get("completion_tokens", 0)),
                                "total_tokens": usage.get("total_tokens", 0),
                            },
                        )()
                    },
                )()
                log_llm_usage(
                    provider="perplexity",
                    model=price_model,
                    status="success",
                    attempt_number=attempt_number,
                    started_at_ms=started_at_ms,
                    response=pseudo_response,
                )
                settings = get_settings()
                log_external_cost(
                    service="perplexity",
                    phase="agent",
                    units=1,
                    unit_cost_usd=settings.perplexity_agent_cost_usd,
                )
                return self._extract_output_text(payload), payload

        raise PerplexityAgentError("Perplexity agent exhausted retries")
