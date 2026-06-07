"""OpenAI Responses API client with web search for attribute research."""
from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.observability.run_usage import log_external_cost, log_llm_usage, monotonic_ms
from app.research.prompts import build_openai_research_output_format

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
WEB_SEARCH_TOOL: dict[str, str] = {"type": "web_search"}

MODEL_ALIASES: dict[str, str] = {
    "gpt-4o-mini": DEFAULT_OPENAI_MODEL,
    "openai/gpt-4o-mini": DEFAULT_OPENAI_MODEL,
    "gpt-5-mini": "gpt-5-mini-2025-08-07",
    "gpt-5-mini-2025-08-07": "gpt-5-mini-2025-08-07",
}


class OpenAIResearchError(RuntimeError):
    pass


def normalize_openai_model(model: str) -> str:
    cleaned = model.strip()
    if not cleaned:
        return DEFAULT_OPENAI_MODEL
    return MODEL_ALIASES.get(cleaned, cleaned)


def _count_web_search_calls(response: Any) -> int:
    output = getattr(response, "output", None)
    if not isinstance(output, list):
        return 0
    return sum(1 for item in output if getattr(item, "type", None) == "web_search_call")


def _extract_output_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    output = getattr(response, "output", None)
    if not isinstance(output, list):
        return ""

    parts: list[str] = []
    for item in output:
        if getattr(item, "type", None) != "message":
            continue
        content = getattr(item, "content", None)
        if not isinstance(content, list):
            continue
        for block in content:
            if getattr(block, "type", None) == "output_text":
                text = getattr(block, "text", "")
                if text:
                    parts.append(str(text))
    return "\n".join(parts)


class OpenAIResearchClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or get_settings().openai_api_key
        self._client: AsyncOpenAI | None = None

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _client_or_raise(self) -> AsyncOpenAI:
        if not self.configured:
            raise OpenAIResearchError("OPENAI_API_KEY is not configured")
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def research(
        self,
        *,
        model: str,
        input_text: str,
        instructions: str,
    ) -> tuple[str, dict[str, Any]]:
        model = normalize_openai_model(model)
        client = self._client_or_raise()

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
                    response = await client.responses.create(
                        model=model,
                        instructions=instructions,
                        input=input_text,
                        tools=[WEB_SEARCH_TOOL],
                        tool_choice="required",
                        text=build_openai_research_output_format(),
                        max_output_tokens=4096,
                    )
                except Exception as exc:
                    log_llm_usage(
                        provider="openai",
                        model=model,
                        status="error",
                        attempt_number=attempt_number,
                        started_at_ms=started_at_ms,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                    raise OpenAIResearchError(str(exc)) from exc

                text = _extract_output_text(response)
                if not text.strip():
                    message = "OpenAI response missing output text"
                    log_llm_usage(
                        provider="openai",
                        model=model,
                        status="error",
                        attempt_number=attempt_number,
                        started_at_ms=started_at_ms,
                        error=message,
                    )
                    raise OpenAIResearchError(message)

                log_llm_usage(
                    provider="openai",
                    model=model,
                    status="success",
                    attempt_number=attempt_number,
                    started_at_ms=started_at_ms,
                    response=response,
                )

                search_calls = _count_web_search_calls(response)
                if search_calls > 0:
                    settings = get_settings()
                    log_external_cost(
                        service="openai",
                        phase="web_search",
                        units=search_calls,
                        unit_cost_usd=settings.openai_web_search_cost_usd,
                    )

                return text, {
                    "model": model,
                    "content": text,
                    "web_search_calls": search_calls,
                }

        raise OpenAIResearchError("OpenAI research exhausted retries")
