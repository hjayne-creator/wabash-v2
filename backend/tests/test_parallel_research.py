from app.adapters.parallel_research import normalize_parallel_processor
from app.config import get_settings
from app.models.db import ProductAttribute
from app.research.prompts import build_parallel_task_spec


def test_normalize_parallel_processor_task_prefix():
    assert normalize_parallel_processor("task-core") == "core"


def test_normalize_parallel_processor_bare():
    assert normalize_parallel_processor("base") == "base"


def test_parallel_task_spec_attributes_has_properties():
    catalog = [
        ProductAttribute(key="material", label="Material", hint="Primary material"),
        ProductAttribute(key="length", label="Length"),
    ]
    spec = build_parallel_task_spec(attributes=catalog)
    attrs_schema = spec["output_schema"]["json_schema"]["properties"]["attributes"]
    assert attrs_schema["properties"]
    assert "Material" in attrs_schema["properties"]
    assert "Length" in attrs_schema["properties"]
    assert "additionalProperties" not in attrs_schema or attrs_schema["additionalProperties"] is False


def test_normalize_parallel_processor_fallback(monkeypatch):
    monkeypatch.setenv("PARALLEL_TASK_PROCESSOR", "core")
    get_settings.cache_clear()
    assert normalize_parallel_processor("search-basic") == "core"
    get_settings.cache_clear()
