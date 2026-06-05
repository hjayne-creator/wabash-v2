"""Available research engines exposed to the UI."""
from __future__ import annotations

from app.config import get_settings

# Valid Perplexity Agent API model IDs (see GET https://api.perplexity.ai/v1/models).
PERPLEXITY_MODEL_OPTIONS: list[dict[str, str]] = [
    {
        "model": "preset:pro-search",
        "display_name": "Perplexity Pro Search",
        "description": "Default — Perplexity preset with built-in web search",
    },
    {
        "model": "preset:fast-search",
        "display_name": "Perplexity Fast Search",
        "description": "Faster, lighter web search preset",
    },
    {
        "model": "openai/gpt-5-mini",
        "display_name": "OpenAI GPT-5 Mini",
        "description": "Fast, cost-effective web research",
    },
    {
        "model": "openai/gpt-5.4-mini",
        "display_name": "OpenAI GPT-5.4 Mini",
        "description": "Newer mini model via Perplexity Agent",
    },
    {
        "model": "openai/gpt-5.4-nano",
        "display_name": "OpenAI GPT-5.4 Nano",
        "description": "Lowest-cost OpenAI model on Perplexity",
    },
]

BRAVE_MODEL_OPTIONS: list[dict[str, str]] = [
    {
        "model": "brave",
        "display_name": "Brave Answers",
        "description": "Single web search with grounded answers",
    },
]


def list_research_engines() -> list[dict]:
    settings = get_settings()
    default_model = settings.wabash_default_perplexity_model
    engines: list[dict] = []

    for option in PERPLEXITY_MODEL_OPTIONS:
        engines.append(
            {
                "provider": "perplexity",
                "model": option["model"],
                "display_name": option["display_name"],
                "description": option["description"],
                "is_default": (
                    settings.wabash_default_research_engine == "perplexity"
                    and option["model"] == default_model
                ),
            }
        )

    # Ensure configured default appears even if not in curated list.
    if not any(e["provider"] == "perplexity" and e["model"] == default_model for e in engines):
        engines.insert(
            0,
            {
                "provider": "perplexity",
                "model": default_model,
                "display_name": "Perplexity Agent (configured default)",
                "description": "From WABASH_DEFAULT_PERPLEXITY_MODEL",
                "is_default": settings.wabash_default_research_engine == "perplexity",
            },
        )

    brave_default_model = settings.wabash_default_brave_model
    for option in BRAVE_MODEL_OPTIONS:
        engines.append(
            {
                "provider": "brave",
                "model": option["model"],
                "display_name": option["display_name"],
                "description": option["description"],
                "is_default": (
                    settings.wabash_default_research_engine == "brave"
                    and option["model"] == brave_default_model
                ),
            }
        )

    if not any(e["provider"] == "brave" and e["model"] == brave_default_model for e in engines):
        engines.append(
            {
                "provider": "brave",
                "model": brave_default_model,
                "display_name": "Brave Answers (configured default)",
                "description": "From WABASH_DEFAULT_BRAVE_MODEL",
                "is_default": settings.wabash_default_research_engine == "brave",
            }
        )

    parallel_model = f"task-{settings.parallel_task_processor}"
    engines.append(
        {
            "provider": "parallel",
            "model": parallel_model,
            "display_name": "Parallel Task API",
            "description": (
                f"Parallel Task API ({settings.parallel_task_processor} processor) — "
                "web research with structured JSON output"
            ),
            "is_default": settings.wabash_default_research_engine == "parallel",
        }
    )
    return engines
