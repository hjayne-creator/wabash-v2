"""Orchestrate attribute research runs."""
from __future__ import annotations

import logging
from typing import Any, Literal

from sqlmodel import Session

from app.adapters.brave_answers import BraveAnswersClient, BraveAnswersError, normalize_brave_model
from app.adapters.parallel_research import (
    ParallelResearchClient,
    ParallelResearchError,
    normalize_parallel_processor,
)
from app.adapters.perplexity_agent import PerplexityAgentClient, PerplexityAgentError, normalize_perplexity_model
from app.config import get_settings
from app.models.db import ProductAttribute, ResearchRun, dump_json, get_engine
from app.observability.run_usage import run_tracking
from app.reports.cost import build_cost_report, build_runtime_report
from app.research.attribute_matcher import load_active_attributes, match_attributes, match_result_to_dict
from app.research.json_utils import parse_json_object
from app.research.prompts import (
    build_brave_research_message,
    build_research_input,
    build_research_instructions,
)

logger = logging.getLogger(__name__)

EngineProvider = Literal["perplexity", "parallel", "brave"]


async def run_attribute_research(
    *,
    manufacturer_name: str,
    manufacturer_product_number: str,
    engine_provider: EngineProvider,
    engine_model: str,
) -> ResearchRun:
    manufacturer_name = manufacturer_name.strip()
    manufacturer_product_number = manufacturer_product_number.strip()
    settings = get_settings()

    if not engine_model.strip():
        if engine_provider == "perplexity":
            engine_model = settings.wabash_default_perplexity_model
        elif engine_provider == "brave":
            engine_model = settings.wabash_default_brave_model
        else:
            engine_model = f"task-{get_settings().parallel_task_processor}"

    with Session(get_engine()) as session:
        catalog = load_active_attributes(session)

    with run_tracking() as (collector, timer):
        timer.start_phase("research")
        status = "complete"
        message: str | None = None
        error_message: str | None = None
        raw: dict[str, Any] = {}

        try:
            if engine_provider == "perplexity":
                raw = await _run_perplexity(
                    manufacturer_name=manufacturer_name,
                    manufacturer_product_number=manufacturer_product_number,
                    engine_model=engine_model,
                )
            elif engine_provider == "brave":
                raw = await _run_brave(
                    manufacturer_name=manufacturer_name,
                    manufacturer_product_number=manufacturer_product_number,
                    engine_model=engine_model,
                )
            elif engine_provider == "parallel":
                raw = await _run_parallel(
                    manufacturer_name=manufacturer_name,
                    manufacturer_product_number=manufacturer_product_number,
                    engine_model=engine_model,
                    catalog=catalog,
                )
            else:
                raise ValueError(f"Unsupported engine provider: {engine_provider}")
        except (PerplexityAgentError, ParallelResearchError, BraveAnswersError, ValueError) as exc:
            status = "error"
            error_message = str(exc)
            raw = {"product_found": False, "attributes": {}, "sources": [], "notes": error_message}
        except Exception as exc:
            logger.exception("attribute research failed")
            status = "error"
            error_message = f"{type(exc).__name__}: {exc}"
            raw = {"product_found": False, "attributes": {}, "sources": [], "notes": error_message}
        finally:
            timer.end_phase()

        if not raw.get("product_found", True) and status == "complete":
            status = "no_product"
            message = "No matching product found."

        llm_attrs = raw.get("attributes") if isinstance(raw.get("attributes"), dict) else {}
        match_result = match_attributes(
            llm_attributes=llm_attrs,
            catalog=catalog,
            fuzzy_threshold=settings.attribute_fuzzy_threshold,
        )
        mapped_dict = match_result_to_dict(match_result)

        cost_lines, total_cost = build_cost_report(collector)
        _, runtime_ms = build_runtime_report(timer)

        if total_cost > settings.max_research_cost_usd and status == "complete":
            status = "partial"
            cap_msg = (
                f"Estimated cost ${total_cost:.4f} exceeds cap "
                f"${settings.max_research_cost_usd:.4f}."
            )
            message = f"{message} {cap_msg}".strip() if message else cap_msg

        run = ResearchRun(
            manufacturer_name=manufacturer_name,
            manufacturer_product_number=manufacturer_product_number,
            engine_provider=engine_provider,
            engine_model=engine_model,
            status=status,
            raw_output_json=dump_json(raw),
            mapped_output_json=dump_json(mapped_dict),
            fill_pct=match_result.fill_pct,
            attributes_filled=match_result.attributes_filled,
            attributes_total=match_result.attributes_total,
            total_cost_usd=total_cost,
            cost_lines_json=dump_json([line.model_dump() for line in cost_lines]),
            runtime_ms=runtime_ms,
            error_message=error_message,
            message=message,
        )

        with Session(get_engine()) as session:
            session.add(run)
            session.commit()
            session.refresh(run)

        return run


async def _run_perplexity(
    *,
    manufacturer_name: str,
    manufacturer_product_number: str,
    engine_model: str,
) -> dict[str, Any]:
    settings = get_settings()
    client = PerplexityAgentClient()
    if not client.configured:
        raise PerplexityAgentError(settings.missing_api_key_hint("PERPLEXITY_API_KEY"))

    model = normalize_perplexity_model(engine_model or settings.wabash_default_perplexity_model)
    instructions = build_research_instructions()
    user_input = build_research_input(
        manufacturer_name=manufacturer_name,
        manufacturer_product_number=manufacturer_product_number,
    )
    text, _payload = await client.research(model=model, input_text=user_input, instructions=instructions)
    parsed = parse_json_object(text)
    return _normalize_raw(parsed, manufacturer_name, manufacturer_product_number)


async def _run_brave(
    *,
    manufacturer_name: str,
    manufacturer_product_number: str,
    engine_model: str,
) -> dict[str, Any]:
    settings = get_settings()
    client = BraveAnswersClient()
    if not client.configured:
        raise BraveAnswersError(settings.missing_api_key_hint("BRAVE_API_KEY"))

    model = normalize_brave_model(engine_model or settings.wabash_default_brave_model)
    prompt = build_brave_research_message(
        manufacturer_name=manufacturer_name,
        manufacturer_product_number=manufacturer_product_number,
    )
    text, _payload = await client.research(model=model, input_text=prompt, instructions="")
    parsed = parse_json_object(text)
    return _normalize_raw(parsed, manufacturer_name, manufacturer_product_number)


async def _run_parallel(
    *,
    manufacturer_name: str,
    manufacturer_product_number: str,
    engine_model: str,
    catalog: list[ProductAttribute],
) -> dict[str, Any]:
    settings = get_settings()
    client = ParallelResearchClient()
    if not client.configured:
        raise ParallelResearchError(settings.missing_api_key_hint("PARALLEL_API_KEY"))

    processor = normalize_parallel_processor(engine_model)
    parsed = await client.research_product(
        manufacturer_name=manufacturer_name,
        manufacturer_product_number=manufacturer_product_number,
        processor=processor,
        attributes=catalog,
    )
    return _normalize_raw(parsed, manufacturer_name, manufacturer_product_number)


def _normalize_raw(
    parsed: dict[str, Any],
    manufacturer_name: str,
    manufacturer_product_number: str,
) -> dict[str, Any]:
    attrs = parsed.get("attributes")
    if not isinstance(attrs, dict):
        attrs = {}
    sources = parsed.get("sources")
    if not isinstance(sources, list):
        sources = []
    return {
        "product_found": bool(parsed.get("product_found", True)),
        "manufacturer_name": parsed.get("manufacturer_name") or manufacturer_name,
        "manufacturer_product_number": parsed.get("manufacturer_product_number") or manufacturer_product_number,
        "attributes": attrs,
        "sources": sources,
        "notes": parsed.get("notes"),
    }
