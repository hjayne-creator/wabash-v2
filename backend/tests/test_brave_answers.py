import json

import pytest
import respx
from httpx import Response

from app.adapters.brave_answers import BraveAnswersClient, _build_user_message, normalize_brave_model
from app.research.attribute_researcher import run_attribute_research
from app.research.prompts import build_brave_research_message
from app.models.db import init_db


def test_build_brave_research_message_is_search_first():
    message = build_brave_research_message(
        manufacturer_name="JOST INTERNATIONAL",
        manufacturer_product_number="AX150L.T1.19",
    )
    assert "JOST INTERNATIONAL" in message
    assert "AX150L.T1.19" in message
    assert message.index("JOST INTERNATIONAL") < message.index("Return valid JSON")
    assert "Target attribute labels" not in message


def test_build_user_message_combines_instructions_and_input():
    message = _build_user_message(
        instructions="Return JSON only.",
        input_text="Research ACME X1.",
    )
    assert message.startswith("Return JSON only.")
    assert message.endswith("Research ACME X1.")


def test_normalize_brave_model():
    assert normalize_brave_model("brave") == "brave"
    assert normalize_brave_model("brave:research") == "brave"
    assert normalize_brave_model("default") == "brave"


@respx.mock
@pytest.mark.asyncio
async def test_brave_research_run_persists(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("BRAVE_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()
    init_db()

    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "product_found": True,
                            "manufacturer_name": "ACME",
                            "manufacturer_product_number": "X1",
                            "attributes": {"Material": "Steel", "Length": "10 in"},
                            "sources": [{"url": "https://example.com", "title": "Example"}],
                        }
                    )
                }
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    }
    respx.post("https://api.search.brave.com/res/v1/chat/completions").mock(
        return_value=Response(
            200,
            json=payload,
            headers={"X-Request-Queries": "1", "X-Request-Total-Cost": "0.008"},
        )
    )

    run = await run_attribute_research(
        manufacturer_name="ACME",
        manufacturer_product_number="X1",
        engine_provider="brave",
        engine_model="brave",
    )

    assert run.id is not None
    assert run.status in ("complete", "partial")
    assert run.attributes_filled >= 1
    assert run.fill_pct > 0


@respx.mock
@pytest.mark.asyncio
async def test_brave_client_sync_research():
    payload = {
        "choices": [{"message": {"content": '{"product_found": true}'}}],
    }
    route = respx.post("https://api.search.brave.com/res/v1/chat/completions").mock(
        return_value=Response(200, json=payload, headers={"X-Request-Queries": "1"})
    )

    client = BraveAnswersClient(api_key="test-key")
    text, _ = await client.research(
        model="brave",
        input_text="Research ACME X1",
        instructions="Return JSON only.",
    )
    assert "product_found" in text
    request = route.calls[0].request
    body = json.loads(request.content.decode())
    assert len(body["messages"]) == 1
    assert body["messages"][0]["role"] == "user"
    assert body["stream"] is False
    assert "Return JSON only." in body["messages"][0]["content"]
    assert "Research ACME X1" in body["messages"][0]["content"]
