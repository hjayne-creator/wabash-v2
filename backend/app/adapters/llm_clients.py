"""OpenAI client for Parallel engine structuring."""
from __future__ import annotations

from openai import AsyncOpenAI
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.observability.run_usage import log_llm_usage, monotonic_ms


class LLMClientError(RuntimeError):
    pass


class OpenAIClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or get_settings().openai_api_key
        self._client: AsyncOpenAI | None = None

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _client_or_raise(self) -> AsyncOpenAI:
        if not self.configured:
            raise LLMClientError("OPENAI_API_KEY is not configured")
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def complete_text(
        self,
        *,
        model: str,
        system: str,
        user: str,
        max_tokens: int = 4096,
    ) -> str:
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
                    response = await client.chat.completions.create(
                        model=model,
                        max_completion_tokens=max_tokens,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                    )
                except Exception as exc:
                    log_llm_usage(
                        provider="parallel",
                        model=f"structure-{model}",
                        status="error",
                        attempt_number=attempt_number,
                        started_at_ms=started_at_ms,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                    raise
                log_llm_usage(
                    provider="parallel",
                    model=f"structure-{model}",
                    status="success",
                    attempt_number=attempt_number,
                    started_at_ms=started_at_ms,
                    response=response,
                )
                return response.choices[0].message.content or ""
        raise LLMClientError("OpenAI text completion exhausted retries")
