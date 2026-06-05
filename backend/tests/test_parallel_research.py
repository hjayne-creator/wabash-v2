from app.adapters.parallel_research import normalize_parallel_processor
from app.config import get_settings
from app.research.prompts import build_parallel_task_input, build_parallel_task_spec


def test_normalize_parallel_processor_task_prefix():
    assert normalize_parallel_processor("task-core") == "core"


def test_normalize_parallel_processor_bare():
    assert normalize_parallel_processor("base") == "base"


def test_parallel_task_spec_attributes_allows_freeform_keys():
    spec = build_parallel_task_spec()
    attrs_schema = spec["output_schema"]["json_schema"]["properties"]["attributes"]
    assert attrs_schema["additionalProperties"] == {"type": "string"}
    assert "properties" not in attrs_schema or not attrs_schema.get("properties")


def test_parallel_task_input_has_no_attribute_targets():
    payload = build_parallel_task_input(
        manufacturer_name="JOST INTERNATIONAL",
        manufacturer_product_number="AX150L.T1.19",
    )
    assert "attribute_targets" not in payload
    assert payload["manufacturer_name"] == "JOST INTERNATIONAL"
    assert "AX150L.T1.19" in payload["query"]


def test_normalize_parallel_processor_fallback(monkeypatch):
    monkeypatch.setenv("PARALLEL_TASK_PROCESSOR", "core")
    get_settings.cache_clear()
    assert normalize_parallel_processor("search-basic") == "core"
    get_settings.cache_clear()
