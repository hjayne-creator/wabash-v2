"""Legacy router stub — V2 uses engine-specific adapters."""
from __future__ import annotations

from app.adapters.llm_clients import LLMClientError, OpenAIClient


async def complete_text(*, model: str, provider: str, system: str, user: str) -> str:
    if provider in ("openai", "parallel"):
        return await OpenAIClient().complete_text(model=model, system=system, user=user)
    raise LLMClientError(f"Unsupported provider: {provider}")
