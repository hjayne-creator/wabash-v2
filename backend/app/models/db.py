"""SQLModel tables and engine setup."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select

from app.attribute_seeds import DEFAULT_ATTRIBUTE_SEEDS
from app.config import get_settings


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ProductAttribute(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(unique=True, index=True)
    label: str
    aliases_json: str = Field(default="[]")
    hint: Optional[str] = None
    sort_order: int = Field(default=0, index=True)
    active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    def aliases_list(self) -> list[str]:
        try:
            parsed = json.loads(self.aliases_json or "[]")
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except json.JSONDecodeError:
            pass
        return []

    def set_aliases(self, aliases: list[str]) -> None:
        self.aliases_json = json.dumps(aliases)


class ResearchRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=_now, index=True)
    manufacturer_name: str = Field(index=True)
    manufacturer_product_number: str = Field(index=True)
    engine_provider: str
    engine_model: str
    status: str = Field(index=True)
    raw_output_json: str = Field(default="{}")
    mapped_output_json: str = Field(default="{}")
    fill_pct: float = 0.0
    attributes_filled: int = 0
    attributes_total: int = 0
    total_cost_usd: float = 0.0
    cost_lines_json: str = Field(default="[]")
    runtime_ms: int = 0
    error_message: Optional[str] = None
    message: Optional[str] = None


class LLMPriceCard(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    provider: str = Field(index=True)
    model: str = Field(index=True)
    input_per_million_usd: float = 0.0
    output_per_million_usd: float = 0.0
    effective_from: datetime = Field(default_factory=_now, index=True)
    effective_to: Optional[datetime] = Field(default=None, index=True)
    active: bool = Field(default=True, index=True)
    notes: Optional[str] = None


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
        _engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)
    return _engine


def init_db() -> None:
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        existing_keys = {r.key for r in session.exec(select(ProductAttribute)).all()}
        for idx, seed in enumerate(DEFAULT_ATTRIBUTE_SEEDS):
            key = seed["key"]
            if key in existing_keys:
                continue
            attr = ProductAttribute(
                key=key,
                label=seed["label"],
                hint=seed.get("hint"),
                sort_order=idx,
                active=True,
            )
            attr.set_aliases(seed.get("aliases", []))
            session.add(attr)

        existing_price_models = {
            (r.provider, r.model) for r in session.exec(select(LLMPriceCard)).all()
        }
        default_model_prices = [
            ("openai", "gpt-4o-mini", 0.15, 0.60),
            ("openai", "gpt-5-mini-2025-08-07", 0.25, 2.00),
            ("perplexity", "openai/gpt-4o-mini", 0.15, 0.60),
            ("perplexity", "preset:pro-search", 0.50, 2.00),
            ("brave", "brave", 5.0, 5.0),
            ("parallel", "task-base", 0.0, 0.0),
            ("parallel", "task-core", 0.0, 0.0),
        ]
        for provider, model, input_per_million_usd, output_per_million_usd in default_model_prices:
            if (provider, model) not in existing_price_models:
                session.add(
                    LLMPriceCard(
                        provider=provider,
                        model=model,
                        input_per_million_usd=input_per_million_usd,
                        output_per_million_usd=output_per_million_usd,
                    )
                )

        session.commit()


def dump_json(data: Any) -> str:
    return json.dumps(data, default=str)
