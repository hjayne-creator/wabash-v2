from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


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
    unit_cost_usd: float | None = None


class RuntimeLineItem(BaseModel):
    phase: str
    duration_ms: int


class ResearchEngineOption(BaseModel):
    provider: Literal["perplexity", "parallel", "brave", "openai", "firecrawl"]
    model: str
    display_name: str
    description: str
    is_default: bool = False


class ResearchRunRequest(BaseModel):
    manufacturer_name: str
    manufacturer_product_number: str
    engine_provider: Literal["perplexity", "parallel", "brave", "openai", "firecrawl"] = "perplexity"
    engine_model: str = ""


class MappedAttributeOut(BaseModel):
    key: str
    label: str
    value: str
    confidence: Literal["exact", "alias", "fuzzy"]
    source_key: str


class ResearchRunResponse(BaseModel):
    id: int
    status: Literal["complete", "partial", "no_product", "error"]
    message: str | None = None
    manufacturer_name: str
    manufacturer_product_number: str
    engine_provider: str
    engine_model: str
    research_query: str | None = None
    research_prompt: str | None = None
    product_found: bool
    raw_output: dict[str, Any] = Field(default_factory=dict)
    mapped: dict[str, MappedAttributeOut] = Field(default_factory=dict)
    unmapped_from_llm: dict[str, str] = Field(default_factory=dict)
    missing: list[str] = Field(default_factory=list)
    fill_pct: float = 0.0
    attributes_filled: int = 0
    attributes_total: int = 0
    sources: list[dict[str, str]] = Field(default_factory=list)
    cost_lines: list[CostLineItem] = Field(default_factory=list)
    total_cost_usd: float = 0.0
    runtime_lines: list[RuntimeLineItem] = Field(default_factory=list)
    total_runtime_ms: int = 0
    error_message: str | None = None


class ResearchRunSummary(BaseModel):
    id: int
    created_at: datetime
    manufacturer_name: str
    manufacturer_product_number: str
    engine_provider: str
    engine_model: str
    status: str
    fill_pct: float
    attributes_filled: int
    attributes_total: int
    total_cost_usd: float
    runtime_ms: int
    message: str | None = None
    error_message: str | None = None


class ProductAttributeIn(BaseModel):
    key: str
    label: str
    aliases: list[str] = Field(default_factory=list)
    hint: str | None = None
    sort_order: int = 0
    active: bool = True

    @field_validator("key")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        cleaned = value.strip().lower().replace(" ", "_")
        if not cleaned:
            raise ValueError("key is required")
        return cleaned


class ProductAttributeOut(BaseModel):
    id: int
    key: str
    label: str
    aliases: list[str]
    hint: str | None
    sort_order: int
    active: bool
    created_at: datetime
    updated_at: datetime


class ProductAttributeUpdate(BaseModel):
    label: str | None = None
    aliases: list[str] | None = None
    hint: str | None = None
    sort_order: int | None = None
    active: bool | None = None


def parse_stored_json(text: str) -> Any:
    try:
        return json.loads(text or "{}")
    except json.JSONDecodeError:
        return {}
