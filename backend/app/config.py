from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent


def _discover_env_files() -> tuple[Path, ...]:
    candidates = (_REPO_ROOT / ".env", _BACKEND_DIR / ".env")
    return tuple(p for p in candidates if p.is_file())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_discover_env_files(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    openai_api_key: str | None = None
    perplexity_api_key: str | None = None
    parallel_api_key: str | None = None
    brave_api_key: str | None = None
    firecrawl_api_key: str | None = None

    @staticmethod
    def _coerce_blank_api_key(value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator(
        "openai_api_key",
        "perplexity_api_key",
        "parallel_api_key",
        "brave_api_key",
        "firecrawl_api_key",
        mode="before",
    )
    @classmethod
    def _normalize_api_keys(cls, value: object) -> object:
        return cls._coerce_blank_api_key(value)

    database_url: str = "sqlite:///./wabash_v2.db"
    app_host: str = Field(default="0.0.0.0", validation_alias=AliasChoices("APP_HOST", "HOST"))
    app_port: int = Field(default=8001, validation_alias=AliasChoices("APP_PORT", "PORT"))
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @field_validator("app_port", mode="before")
    @classmethod
    def _coerce_port(cls, value: object) -> object:
        if value == "" or value is None:
            return None
        return value

    auth_username: str = "admin"
    auth_password: str | None = None
    auth_session_secret: str | None = None
    auth_session_ttl_seconds: int = Field(default=60 * 60 * 12, ge=60)
    auth_cookie_secure: bool = False
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    auth_cookie_domain: str | None = None

    wabash_default_research_engine: Literal["perplexity", "parallel", "brave", "openai", "firecrawl"] = Field(
        default="perplexity",
        validation_alias=AliasChoices("WABASH_DEFAULT_RESEARCH_ENGINE"),
    )
    wabash_default_firecrawl_model: str = Field(
        default="spark-1-mini",
        validation_alias=AliasChoices("WABASH_DEFAULT_FIRECRAWL_MODEL"),
    )
    wabash_default_openai_model: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices("WABASH_DEFAULT_OPENAI_MODEL"),
    )
    wabash_default_brave_model: str = Field(
        default="brave",
        validation_alias=AliasChoices("WABASH_DEFAULT_BRAVE_MODEL"),
    )
    wabash_default_perplexity_model: str = Field(
        default="preset:pro-search",
        validation_alias=AliasChoices("WABASH_DEFAULT_PERPLEXITY_MODEL"),
    )
    parallel_task_processor: str = Field(
        default="base",
        validation_alias=AliasChoices("PARALLEL_TASK_PROCESSOR"),
    )
    max_research_cost_usd: float = Field(
        default=0.06,
        validation_alias=AliasChoices("WABASH_MAX_RESEARCH_COST_USD"),
    )
    perplexity_agent_cost_usd: float = Field(default=0.02)
    brave_answers_search_cost_usd: float = Field(
        default=0.004,
        validation_alias=AliasChoices("BRAVE_ANSWERS_SEARCH_COST_USD"),
    )
    parallel_task_cost_usd: float = Field(
        default=0.02,
        validation_alias=AliasChoices("PARALLEL_TASK_COST_USD", "PARALLEL_SEARCH_COST_USD"),
    )
    openai_web_search_cost_usd: float = Field(
        default=0.01,
        validation_alias=AliasChoices("OPENAI_WEB_SEARCH_COST_USD"),
    )
    firecrawl_agent_cost_usd: float = Field(
        default=0.03,
        validation_alias=AliasChoices("FIRECRAWL_AGENT_COST_USD"),
    )
    firecrawl_usd_per_credit: float = Field(
        default=0.004,
        validation_alias=AliasChoices("FIRECRAWL_USD_PER_CREDIT"),
    )
    firecrawl_agent_max_credits: int = Field(
        default=100,
        ge=1,
        validation_alias=AliasChoices("FIRECRAWL_AGENT_MAX_CREDITS"),
    )
    firecrawl_agent_poll_interval_sec: int = Field(
        default=5,
        ge=2,
        validation_alias=AliasChoices("FIRECRAWL_AGENT_POLL_INTERVAL_SEC"),
    )
    firecrawl_agent_poll_retries: int = Field(
        default=12,
        ge=1,
        validation_alias=AliasChoices("FIRECRAWL_AGENT_POLL_RETRIES"),
    )
    firecrawl_agent_min_wait_seconds: int = Field(
        default=600,
        ge=120,
        validation_alias=AliasChoices("FIRECRAWL_AGENT_MIN_WAIT_SECONDS"),
    )
    max_run_seconds: int = Field(default=300, ge=30)
    attribute_fuzzy_threshold: int = Field(default=90, ge=70, le=100)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def env_file_paths(self) -> list[Path]:
        return list(_discover_env_files())

    def missing_api_key_hint(self, env_name: str) -> str:
        paths = self.env_file_paths
        parts = [
            f"Set {env_name} in backend/.env or the repository root .env for local development.",
            "Restart the backend after changing local .env files.",
        ]
        if paths:
            parts.append(f"Loaded env files: {', '.join(str(p) for p in paths)}.")
        else:
            parts.append(f"No .env found at {_BACKEND_DIR / '.env'} or {_REPO_ROOT / '.env'}.")
        return " ".join(parts)

    @model_validator(mode="after")
    def _cross_origin_cookie_defaults(self) -> "Settings":
        if not self.auth_password:
            return self
        cross_origin = any(
            origin.startswith("https://")
            and "localhost" not in origin
            and "127.0.0.1" not in origin
            for origin in self.cors_origin_list
        )
        if cross_origin:
            if self.auth_cookie_samesite == "lax":
                self.auth_cookie_samesite = "none"
            if not self.auth_cookie_secure:
                self.auth_cookie_secure = True
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
