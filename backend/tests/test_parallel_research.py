from app.adapters.parallel_research import normalize_parallel_processor
from app.config import get_settings
from app.models.db import ProductAttribute
from app.research.prompts import build_brave_research_message, build_parallel_task_input, build_parallel_task_spec


def _sample_attributes() -> list[ProductAttribute]:
    return [
        ProductAttribute(key="weight", label="Weight", hint="Product weight"),
        ProductAttribute(key="material", label="Material"),
    ]


def test_normalize_parallel_processor_task_prefix():
    assert normalize_parallel_processor("task-core") == "core"


def test_normalize_parallel_processor_bare():
    assert normalize_parallel_processor("base") == "base"


def test_parallel_task_spec_attributes_uses_catalog_properties():
    attributes = _sample_attributes()
    spec = build_parallel_task_spec(attributes=attributes)
    attrs_schema = spec["output_schema"]["json_schema"]["properties"]["attributes"]
    assert attrs_schema["additionalProperties"] is False
    assert "Weight" in attrs_schema["properties"]
    assert "Material" in attrs_schema["properties"]


def test_parallel_task_spec_attributes_fallback_when_catalog_empty():
    spec = build_parallel_task_spec(attributes=[])
    attrs_schema = spec["output_schema"]["json_schema"]["properties"]["attributes"]
    assert "specification" in attrs_schema["properties"]


def test_parallel_task_input_includes_attribute_targets():
    attributes = _sample_attributes()
    payload = build_parallel_task_input(
        manufacturer_name="JOST INTERNATIONAL",
        manufacturer_product_number="AX150L.T1.19",
        attributes=attributes,
    )
    assert payload["attribute_targets"] == [
        {"label": "Weight", "hint": "Product weight"},
        {"label": "Material"},
    ]
    assert payload["manufacturer_name"] == "JOST INTERNATIONAL"
    assert "AX150L.T1.19" in payload["query"]


def test_build_brave_research_message_returns_string():
    message = build_brave_research_message(
        manufacturer_name="JOST INTERNATIONAL",
        manufacturer_product_number="AX150L.T1.19",
    )
    assert isinstance(message, str)
    assert "Keep attribute values short and concise." in message
    assert "# Output Format" in message
    assert '"product_found": boolean' in message


def test_normalize_parallel_processor_fallback(monkeypatch):
    monkeypatch.setenv("PARALLEL_TASK_PROCESSOR", "core")
    get_settings.cache_clear()
    assert normalize_parallel_processor("search-basic") == "core"
    get_settings.cache_clear()
