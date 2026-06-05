"""Brave Answers API client (OpenAI-compatible chat completions)."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.observability.run_usage import log_external_cost, log_llm_usage, monotonic_ms

logger = logging.getLogger(__name__)

BRAVE_ANSWERS_URL = "https://api.search.brave.com/res/v1/chat/completions"
BRAVE_MODEL = "brave"

MODEL_ALIASES: dict[str, str] = {
    "default": BRAVE_MODEL,
    "single": BRAVE_MODEL,
    "brave-default": BRAVE_MODEL,
    "brave:research": BRAVE_MODEL,
}


class BraveAnswersError(RuntimeError):
    pass


def normalize_brave_model(model: str) -> str:
    cleaned = model.strip().lower()
    if cleaned in MODEL_ALIASES:
        return MODEL_ALIASES[cleaned]
    if cleaned == BRAVE_MODEL:
        return cleaned
    return BRAVE_MODEL


def _format_http_error(exc: httpx.HTTPStatusError) -> str:
    detail = exc.response.text.strip()
    try:
        payload = exc.response.json()
        if isinstance(payload, dict):
            err = payload.get("error")
            if isinstance(err, dict):
                detail = err.get("message") or err.get("detail") or detail
                meta = err.get("meta")
                if isinstance(meta, dict):
                    errors = meta.get("errors")
                    if isinstance(errors, list) and errors:
                        messages = [
                            str(item.get("msg"))
                            for item in errors
                            if isinstance(item, dict) and item.get("msg")
                        ]
                        if messages:
                            detail = f"{detail} ({'; '.join(messages)})"
            elif isinstance(err, str):
                detail = err
            else:
                detail = payload.get("detail") or payload.get("message") or detail
    except Exception:
        pass
    return f"Brave Answers API error ({exc.response.status_code}): {detail or exc.response.reason_phrase}"


def _parse_usage_headers(headers: httpx.Headers) -> dict[str, float | int]:
    usage: dict[str, float | int] = {}
    mapping = {
        "x-request-queries": "queries",
        "x-request-tokens-in": "input_tokens",
        "x-request-tokens-out": "output_tokens",
        "x-request-total-cost": "total_cost_usd",
    }
    for header_key, field in mapping.items():
        raw = headers.get(header_key)
        if raw is None:
            continue
        try:
            usage[field] = float(raw) if field == "total_cost_usd" else int(float(raw))
        except ValueError:
            continue
    if "input_tokens" in usage or "output_tokens" in usage:
        usage["total_tokens"] = int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))
    return usage


def _build_user_message(*, instructions: str, input_text: str) -> str:
    """Brave Answers accepts exactly one message (user role only)."""
    instructions = instructions.strip()
    input_text = input_text.strip()
    if instructions and input_text:
        return f"{instructions}\n\n{input_text}"
    return instructions or input_text


def _extract_message_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise BraveAnswersError("Brave Answers response missing choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise BraveAnswersError("Brave Answers response missing message")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise BraveAnswersError("Brave Answers response missing content")
    return content


class BraveAnswersClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or get_settings().brave_api_key

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        if not self.configured:
            raise BraveAnswersError("BRAVE_API_KEY is not configured")
        return {
            "x-subscription-token": self.api_key,
            "Content-Type": "application/json",
        }

    async def research(
        self,
        *,
        model: str,
        input_text: str,
        instructions: str,
    ) -> tuple[str, dict[str, Any]]:
        model = normalize_brave_model(model)
        messages = [
            {
                "role": "user",
                "content": _build_user_message(instructions=instructions, input_text=input_text),
            }
        ]

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
                    text, usage_meta, payload = await self._research_sync(messages=messages)
                except httpx.HTTPStatusError as exc:
                    message = _format_http_error(exc)
                    log_llm_usage(
                        provider="brave",
                        model=model,
                        status="error",
                        attempt_number=attempt_number,
                        started_at_ms=started_at_ms,
                        error=message,
                    )
                    raise BraveAnswersError(message) from exc
                except Exception as exc:
                    log_llm_usage(
                        provider="brave",
                        model=model,
                        status="error",
                        attempt_number=attempt_number,
                        started_at_ms=started_at_ms,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                    raise BraveAnswersError(str(exc)) from exc

                pseudo_response = type(
                    "BraveUsage",
                    (),
                    {
                        "usage": type(
                            "U",
                            (),
                            {
                                "prompt_tokens": usage_meta.get("input_tokens", 0),
                                "completion_tokens": usage_meta.get("output_tokens", 0),
                                "total_tokens": usage_meta.get("total_tokens", 0),
                            },
                        )()
                    },
                )()
                log_llm_usage(
                    provider="brave",
                    model=model,
                    status="success",
                    attempt_number=attempt_number,
                    started_at_ms=started_at_ms,
                    response=pseudo_response,
                )

                settings = get_settings()
                total_cost = usage_meta.get("total_cost_usd")
                if isinstance(total_cost, (int, float)) and total_cost > 0:
                    log_external_cost(
                        service="brave",
                        phase=model,
                        units=1,
                        unit_cost_usd=float(total_cost),
                    )
                else:
                    log_external_cost(
                        service="brave",
                        phase=model,
                        units=int(usage_meta.get("queries", 1) or 1),
                        unit_cost_usd=settings.brave_answers_search_cost_usd,
                    )

                return text, payload

        raise BraveAnswersError("Brave Answers exhausted retries")

    async def _research_sync(
        self,
        *,
        messages: list[dict[str, str]],
    ) -> tuple[str, dict[str, float | int], dict[str, Any]]:
        body = {
            "stream": False,
            "messages": messages,
        }
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(BRAVE_ANSWERS_URL, headers=self._headers(), json=body)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise BraveAnswersError("Brave Answers returned non-JSON response")
        usage_meta = _parse_usage_headers(response.headers)
        return _extract_message_content(payload), usage_meta, payload
