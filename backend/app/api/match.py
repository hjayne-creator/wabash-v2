from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.adapters.firecrawl_client import FirecrawlError
from app.adapters.serpapi_client import SerpapiError
from app.models.schemas import MatchRunRequest, MatchRunResponse
from app.observability.run_usage import run_tracking
from app.reports.cost import build_cost_report, build_runtime_report
from app.research.searcher import run_product_match

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/run", response_model=MatchRunResponse)
async def match_run(payload: MatchRunRequest) -> MatchRunResponse:
    try:
        with run_tracking() as (collector, timer):
            timer.start_phase("match_pipeline")
            bundle = await run_product_match(
                manufacturer_name=payload.manufacturer_name,
                manufacturer_product_number=payload.manufacturer_product_number,
            )
            timer.end_phase()
            cost_lines, total_cost = build_cost_report(collector)
            runtime_lines, total_runtime = build_runtime_report(timer)
    except (SerpapiError, FirecrawlError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Match run failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return MatchRunResponse(
        status=bundle.status,  # type: ignore[arg-type]
        message=bundle.message,
        manufacturer_name=bundle.manufacturer,
        manufacturer_product_number=bundle.mpn,
        candidates=bundle.candidates,
        sources=bundle.sources,
        cost_lines=cost_lines,
        total_cost_usd=total_cost,
        runtime_lines=runtime_lines,
        total_runtime_ms=total_runtime,
        audit={"candidate_count": len(bundle.candidates), "source_count": len(bundle.sources)},
    )
