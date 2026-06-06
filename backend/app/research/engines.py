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

OPENAI_MODEL_OPTIONS: list[dict[str, str]] = [
    {
        "model": "gpt-4o-mini",
        "display_name": "GPT-4o Mini",
        "description": "OpenAI Responses API with built-in web search — fast, cost-effective attribute research",
    },
    {
        "model": "gpt-5-mini-2025-08-07",
        "display_name": "GPT-5 Mini",
        "description": "OpenAI Responses API with built-in web search — newer mini model with stronger reasoning",
    },
]

BRAVE_MODEL_OPTIONS: list[dict[str, str]] = [
    {
        "model": "brave",
        "display_name": "Brave Answers",
        "description": "Single web search with grounded answers",
    },
]

FIRECRAWL_MODEL_OPTIONS: list[dict[str, str]] = [
    {
        "model": "spark-1-mini",
        "display_name": "Firecrawl Agent (spark-1-mini)",
        "description": "Autonomous web research — cost-effective agent for product attribute extraction",
    },
    {
        "model": "spark-1-pro",
        "display_name": "Firecrawl Agent (spark-1-pro)",
        "description": "Autonomous web research — higher accuracy for complex product lookups",
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

    openai_default_model = settings.wabash_default_openai_model
    for option in OPENAI_MODEL_OPTIONS:
        engines.append(
            {
                "provider": "openai",
                "model": option["model"],
                "display_name": option["display_name"],
                "description": option["description"],
                "is_default": (
                    settings.wabash_default_research_engine == "openai"
                    and option["model"] == openai_default_model
                ),
            }
        )

    if not any(e["provider"] == "openai" and e["model"] == openai_default_model for e in engines):
        engines.append(
            {
                "provider": "openai",
                "model": openai_default_model,
                "display_name": "OpenAI (configured default)",
                "description": "From WABASH_DEFAULT_OPENAI_MODEL",
                "is_default": settings.wabash_default_research_engine == "openai",
            }
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

    firecrawl_default_model = settings.wabash_default_firecrawl_model
    for option in FIRECRAWL_MODEL_OPTIONS:
        engines.append(
            {
                "provider": "firecrawl",
                "model": option["model"],
                "display_name": option["display_name"],
                "description": option["description"],
                "is_default": (
                    settings.wabash_default_research_engine == "firecrawl"
                    and option["model"] == firecrawl_default_model
                ),
            }
        )

    if not any(e["provider"] == "firecrawl" and e["model"] == firecrawl_default_model for e in engines):
        engines.append(
            {
                "provider": "firecrawl",
                "model": firecrawl_default_model,
                "display_name": "Firecrawl Agent (configured default)",
                "description": "From WABASH_DEFAULT_FIRECRAWL_MODEL",
                "is_default": settings.wabash_default_research_engine == "firecrawl",
            }
        )

    return engines
