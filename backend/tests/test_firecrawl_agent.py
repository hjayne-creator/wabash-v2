import json

import pytest
import respx
from httpx import Response

from app.adapters.firecrawl_agent import FirecrawlAgentClient, normalize_firecrawl_model
from app.config import get_settings
from app.models.db import ProductAttribute, init_db
from app.research.attribute_researcher import run_attribute_research
from app.research.prompts import build_firecrawl_agent_prompt, build_firecrawl_agent_schema


def _sample_attributes() -> list[ProductAttribute]:
    return [
        ProductAttribute(key="weight", label="Weight", hint="Product weight"),
        ProductAttribute(key="material", label="Material"),
    ]


def test_normalize_firecrawl_model():
    assert normalize_firecrawl_model("spark-1-mini") == "spark-1-mini"
    assert normalize_firecrawl_model("spark-1-pro") == "spark-1-pro"


def test_build_firecrawl_agent_prompt():
    prompt = build_firecrawl_agent_prompt(
        manufacturer_name="WHITING DOOR",
        manufacturer_product_number="ML5035",
        attributes=_sample_attributes(),
    )
    assert "WHITING DOOR" in prompt
    assert "ML5035" in prompt
    assert "official manufacturer" in prompt
    assert "Target catalog attribute labels" in prompt


def test_build_firecrawl_agent_schema_uses_catalog():
    schema = build_firecrawl_agent_schema(attributes=_sample_attributes())
    attrs_schema = schema["properties"]["attributes"]
    assert "Weight" in attrs_schema["properties"]
    assert "Material" in attrs_schema["properties"]


@respx.mock
@pytest.mark.asyncio
async def test_firecrawl_research_run_persists(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setenv("FIRECRAWL_USD_PER_CREDIT", "0.004")
    monkeypatch.setenv("FIRECRAWL_AGENT_POLL_INTERVAL_SEC", "2")
    get_settings.cache_clear()
    init_db()

    job_id = "11111111-1111-1111-1111-111111111111"
    respx.post("https://api.firecrawl.dev/v2/agent").mock(
        return_value=Response(200, json={"success": True, "id": job_id})
    )
    respx.get(f"https://api.firecrawl.dev/v2/agent/{job_id}").mock(
        return_value=Response(
            200,
            json={
                "success": True,
                "status": "completed",
                "creditsUsed": 150,
                "data": {
                    "product_found": True,
                    "manufacturer_name": "WHITING DOOR",
                    "manufacturer_product_number": "ML5035",
                    "attributes": {"Weight": "10 lb", "Material": "Steel"},
                    "sources": [{"url": "https://example.com", "title": "Example"}],
                },
            },
        )
    )

    run = await run_attribute_research(
        manufacturer_name="WHITING DOOR",
        manufacturer_product_number="ML5035",
        engine_provider="firecrawl",
        engine_model="spark-1-mini",
    )

    assert run.id is not None
    assert run.status in ("complete", "partial")
    assert run.attributes_filled >= 1
    assert run.fill_pct > 0
    assert run.total_cost_usd == pytest.approx(0.6)


@respx.mock
@pytest.mark.asyncio
async def test_firecrawl_client_research_product():
    job_id = "22222222-2222-2222-2222-222222222222"
    start_route = respx.post("https://api.firecrawl.dev/v2/agent").mock(
        return_value=Response(200, json={"success": True, "id": job_id})
    )
    status_route = respx.get(f"https://api.firecrawl.dev/v2/agent/{job_id}").mock(
        return_value=Response(
            200,
            json={
                "success": True,
                "status": "completed",
                "creditsUsed": 8,
                "data": json.dumps(
                    {
                        "product_found": True,
                        "manufacturer_name": "ACME",
                        "manufacturer_product_number": "X1",
                        "attributes": {"Weight": "5 lb"},
                        "sources": [],
                    }
                ),
            },
        )
    )

    client = FirecrawlAgentClient(api_key="test-key")
    result = await client.research_product(
        manufacturer_name="ACME",
        manufacturer_product_number="X1",
        model="spark-1-mini",
        attributes=[],
    )

    assert result["product_found"] is True
    assert start_route.called
    assert status_route.called
