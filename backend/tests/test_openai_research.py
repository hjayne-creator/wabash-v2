import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.adapters.openai_research import (
    OpenAIResearchClient,
    _count_web_search_calls,
    _extract_output_text,
    normalize_openai_model,
)
from app.observability.usage_extract import extract_openai_usage


def test_normalize_openai_model():
    assert normalize_openai_model("gpt-4o-mini") == "gpt-4o-mini"
    assert normalize_openai_model("openai/gpt-4o-mini") == "gpt-4o-mini"
    assert normalize_openai_model("gpt-5-mini") == "gpt-5-mini-2025-08-07"
    assert normalize_openai_model("gpt-5-mini-2025-08-07") == "gpt-5-mini-2025-08-07"
    assert normalize_openai_model("") == "gpt-4o-mini"


def test_extract_openai_usage_supports_responses_api():
    usage = extract_openai_usage(
        SimpleNamespace(
            usage=SimpleNamespace(
                input_tokens=120,
                output_tokens=80,
                total_tokens=200,
            )
        )
    )
    assert usage == {"input_tokens": 120, "output_tokens": 80, "total_tokens": 200}


def test_count_web_search_calls():
    response = SimpleNamespace(
        output=[
            SimpleNamespace(type="web_search_call"),
            SimpleNamespace(type="message"),
            SimpleNamespace(type="web_search_call"),
        ]
    )
    assert _count_web_search_calls(response) == 2


def test_extract_output_text_from_message_blocks():
    response = SimpleNamespace(
        output_text="",
        output=[
            SimpleNamespace(
                type="message",
                content=[SimpleNamespace(type="output_text", text='{"product_found": true}')],
            )
        ],
    )
    assert _extract_output_text(response) == '{"product_found": true}'


@pytest.mark.asyncio
async def test_openai_research_uses_responses_api_with_web_search():
    payload = {
        "product_found": True,
        "manufacturer_name": "PEWAG",
        "manufacturer_product_number": "H4247SC",
        "attributes": {"Material": "Steel"},
        "sources": [{"url": "https://example.com", "title": "Example"}],
    }
    mock_response = SimpleNamespace(
        output_text=json.dumps(payload),
        usage=SimpleNamespace(input_tokens=100, output_tokens=50, total_tokens=150),
        output=[SimpleNamespace(type="web_search_call")],
    )
    mock_create = AsyncMock(return_value=mock_response)

    with patch("app.adapters.openai_research.AsyncOpenAI") as mock_client_cls:
        mock_client_cls.return_value.responses.create = mock_create
        client = OpenAIResearchClient(api_key="test-key")
        text, meta = await client.research(
            model="gpt-4o-mini",
            input_text="Find PEWAG H4247SC specs.",
            instructions="Return JSON only.",
        )

    assert json.loads(text) == payload
    assert meta["web_search_calls"] == 1
    mock_create.assert_awaited_once()
    kwargs = mock_create.await_args.kwargs
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["tools"] == [{"type": "web_search"}]
    assert kwargs["tool_choice"] == "required"
    assert kwargs["text"]["format"]["type"] == "json_schema"
    assert kwargs["text"]["format"]["name"] == "attribute_research"
    assert kwargs["instructions"] == "Return JSON only."
    assert kwargs["input"] == "Find PEWAG H4247SC specs."
