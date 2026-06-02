import json

import pytest
import respx
from httpx import Response

from app.research.attribute_researcher import run_attribute_research
from app.models.db import init_db


@pytest.fixture(autouse=True)
def _db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    from app.config import get_settings

    get_settings.cache_clear()
    init_db()
    yield
    get_settings.cache_clear()


@respx.mock
@pytest.mark.asyncio
async def test_perplexity_research_run_persists(monkeypatch):
    monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()

    payload = {
        "output_text": json.dumps(
            {
                "product_found": True,
                "manufacturer_name": "ACME",
                "manufacturer_product_number": "X1",
                "attributes": {"Material": "Steel", "Length": "10 in"},
                "sources": [{"url": "https://example.com", "title": "Example"}],
            }
        ),
        "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
    }
    respx.post("https://api.perplexity.ai/v1/agent").mock(
        return_value=Response(200, json=payload)
    )

    run = await run_attribute_research(
        manufacturer_name="ACME",
        manufacturer_product_number="X1",
        engine_provider="perplexity",
        engine_model="openai/gpt-5-mini",
    )

    assert run.id is not None
    assert run.status in ("complete", "partial")
    assert run.attributes_filled >= 1
    assert run.fill_pct > 0
