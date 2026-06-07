from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from app.models.db import ResearchRun, get_engine
from app.models.schemas import (
    CostLineItem,
    ResearchEngineOption,
    ResearchRunRequest,
    ResearchRunResponse,
    ResearchRunSummary,
    RuntimeLineItem,
    parse_stored_json,
)
from app.research.attribute_matcher import load_active_attributes
from app.research.attribute_researcher import run_attribute_research
from app.research.engines import list_research_engines
from app.research.prompts import build_engine_research_display

router = APIRouter()


def _run_to_response(run: ResearchRun) -> ResearchRunResponse:
    raw = parse_stored_json(run.raw_output_json)
    mapped_payload = parse_stored_json(run.mapped_output_json)
    mapped_raw = mapped_payload.get("mapped", {}) if isinstance(mapped_payload, dict) else {}
    cost_lines = parse_stored_json(run.cost_lines_json)
    if not isinstance(cost_lines, list):
        cost_lines = []

    research_query = raw.get("research_query") if isinstance(raw.get("research_query"), str) else None
    research_prompt = raw.get("research_prompt") if isinstance(raw.get("research_prompt"), str) else None
    if not research_query or not research_prompt:
        with Session(get_engine()) as session:
            catalog = load_active_attributes(session)
        fallback_query, fallback_prompt = build_engine_research_display(
            engine_provider=run.engine_provider,
            manufacturer_name=run.manufacturer_name,
            manufacturer_product_number=run.manufacturer_product_number,
            attributes=catalog,
        )
        research_query = research_query or fallback_query
        research_prompt = research_prompt or fallback_prompt

    return ResearchRunResponse(
        id=run.id or 0,
        status=run.status,  # type: ignore[arg-type]
        message=run.message,
        manufacturer_name=run.manufacturer_name,
        manufacturer_product_number=run.manufacturer_product_number,
        engine_provider=run.engine_provider,
        engine_model=run.engine_model,
        research_query=research_query,
        research_prompt=research_prompt,
        product_found=bool(raw.get("product_found", False)),
        raw_output=raw if isinstance(raw, dict) else {},
        mapped=mapped_raw,
        unmapped_from_llm=mapped_payload.get("unmapped_from_llm", {}) if isinstance(mapped_payload, dict) else {},
        missing=mapped_payload.get("missing", []) if isinstance(mapped_payload, dict) else [],
        fill_pct=run.fill_pct,
        attributes_filled=run.attributes_filled,
        attributes_total=run.attributes_total,
        sources=raw.get("sources", []) if isinstance(raw.get("sources"), list) else [],
        cost_lines=[CostLineItem(**line) for line in cost_lines if isinstance(line, dict)],
        total_cost_usd=run.total_cost_usd,
        runtime_lines=[RuntimeLineItem(phase="research", duration_ms=run.runtime_ms)],
        total_runtime_ms=run.runtime_ms,
        error_message=run.error_message,
    )


@router.get("/engines", response_model=list[ResearchEngineOption])
def get_engines() -> list[ResearchEngineOption]:
    return [ResearchEngineOption(**engine) for engine in list_research_engines()]


@router.post("/run", response_model=ResearchRunResponse)
async def run_research(body: ResearchRunRequest) -> ResearchRunResponse:
    if not body.manufacturer_name.strip() or not body.manufacturer_product_number.strip():
        raise HTTPException(status_code=400, detail="Manufacturer name and product number are required.")
    try:
        run = await run_attribute_research(
            manufacturer_name=body.manufacturer_name,
            manufacturer_product_number=body.manufacturer_product_number,
            engine_provider=body.engine_provider,
            engine_model=body.engine_model,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _run_to_response(run)


@router.get("/runs", response_model=list[ResearchRunSummary])
def list_runs(limit: int = 50) -> list[ResearchRunSummary]:
    limit = max(1, min(limit, 200))
    with Session(get_engine()) as session:
        rows = session.exec(
            select(ResearchRun).order_by(ResearchRun.created_at.desc()).limit(limit)
        ).all()
    return [
        ResearchRunSummary(
            id=row.id or 0,
            created_at=row.created_at,
            manufacturer_name=row.manufacturer_name,
            manufacturer_product_number=row.manufacturer_product_number,
            engine_provider=row.engine_provider,
            engine_model=row.engine_model,
            status=row.status,
            fill_pct=row.fill_pct,
            attributes_filled=row.attributes_filled,
            attributes_total=row.attributes_total,
            total_cost_usd=row.total_cost_usd,
            runtime_ms=row.runtime_ms,
            message=row.message,
            error_message=row.error_message,
        )
        for row in rows
    ]


@router.get("/runs/{run_id}", response_model=ResearchRunResponse)
def get_run(run_id: int) -> ResearchRunResponse:
    with Session(get_engine()) as session:
        run = session.get(ResearchRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return _run_to_response(run)
