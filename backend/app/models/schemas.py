from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MatchRunRequest(BaseModel):
    manufacturer_name: str
    manufacturer_product_number: str


class CostLineItem(BaseModel):
    phase: str
    service: str | None = None
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    input_cost_usd: float = 0.0
    output_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    units: int | None = None


class RuntimeLineItem(BaseModel):
    phase: str
    duration_ms: int


class CandidateRecord(BaseModel):
    rank: int
    url: str
    title: str
    snippet: str
    domain: str
    tier: str
    serp_score: float


class MatchCriterion(BaseModel):
    name: str
    score_pct: int = Field(ge=0, le=100)
    rationale: str = ""


class ScoredSource(BaseModel):
    url: str
    title: str
    snippet: str
    domain: str
    tier: str
    scrape_ok: bool
    scrape_error: str | None = None
    is_product_page: bool | None = None
    product_page_score: int | None = None
    product_match_score: int | None = None
    product_page_signals: list[str] = Field(default_factory=list)
    markdown_excerpt: str = ""
    rule_mpn_found: bool = False
    rule_manufacturer_match: bool = False
    overall_similarity_pct: int | None = None
    criteria: list[MatchCriterion] = Field(default_factory=list)
    score_error: str | None = None


class MatchRunResponse(BaseModel):
    status: Literal["complete", "partial", "no_candidates"]
    message: str | None = None
    manufacturer_name: str
    manufacturer_product_number: str
    candidates: list[CandidateRecord] = Field(default_factory=list)
    sources: list[ScoredSource] = Field(default_factory=list)
    cost_lines: list[CostLineItem] = Field(default_factory=list)
    total_cost_usd: float = 0.0
    runtime_lines: list[RuntimeLineItem] = Field(default_factory=list)
    total_runtime_ms: int = 0
    audit: dict[str, Any] = Field(default_factory=dict)
