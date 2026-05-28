"""SQLModel tables and engine setup."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select

from app.config import get_settings
from app.domain_blocklist import (
    DEFAULT_AUTHORIZED_DISTRIBUTOR_SEEDS,
    DEFAULT_BLOCKED_DOMAIN_SEEDS,
    normalize_blocked_domain_key,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class BlockedDomain(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    domain: str = Field(unique=True, index=True)


class AuthorizedDistributor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    domain: str = Field(unique=True, index=True)


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
        existing_blocked = {r.domain for r in session.exec(select(BlockedDomain)).all()}
        for seed in DEFAULT_BLOCKED_DOMAIN_SEEDS:
            domain = normalize_blocked_domain_key(seed)
            if domain and domain not in existing_blocked:
                session.add(BlockedDomain(domain=domain))

        existing_auth = {r.domain for r in session.exec(select(AuthorizedDistributor)).all()}
        for seed in DEFAULT_AUTHORIZED_DISTRIBUTOR_SEEDS:
            domain = normalize_blocked_domain_key(seed)
            if domain and domain not in existing_auth:
                session.add(AuthorizedDistributor(domain=domain))

        existing_price_models = {
            (r.provider, r.model) for r in session.exec(select(LLMPriceCard)).all()
        }
        default_model_prices = [
            ("openai", "gpt-4o-mini", 0.15, 0.60),
            ("openai", "gpt-4o", 2.50, 10.0),
            ("anthropic", "claude-3-5-haiku-latest", 0.80, 4.0),
            ("anthropic", "claude-sonnet-4-6", 3.0, 15.0),
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
