import pytest

from app.research.json_utils import parse_json_object


def test_parse_json_object_accepts_plain_json():
    parsed = parse_json_object('{"product_found": true, "attributes": {}}')
    assert parsed["product_found"] is True


def test_parse_json_object_strips_markdown_fence():
    text = '```json\n{"product_found": false}\n```'
    assert parse_json_object(text)["product_found"] is False


def test_parse_json_object_repairs_trailing_commas():
    text = '{"product_found": true, "attributes": {"Material": "Steel",},}'
    parsed = parse_json_object(text)
    assert parsed["attributes"]["Material"] == "Steel"


def test_parse_json_object_raises_on_invalid_json():
    with pytest.raises(ValueError, match="Could not parse JSON object"):
        parse_json_object("{not json")
