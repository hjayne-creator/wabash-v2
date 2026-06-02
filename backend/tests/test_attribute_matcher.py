from app.models.db import ProductAttribute
from app.research.attribute_matcher import match_attributes


def _attr(key: str, label: str, aliases: list[str] | None = None) -> ProductAttribute:
    row = ProductAttribute(key=key, label=label, sort_order=0, active=True)
    row.set_aliases(aliases or [])
    return row


def test_exact_label_match():
    catalog = [_attr("material", "Material")]
    result = match_attributes(llm_attributes={"Material": "Steel"}, catalog=catalog)
    assert result.attributes_filled == 1
    assert result.mapped["material"].value == "Steel"
    assert result.mapped["material"].confidence == "exact"


def test_alias_match():
    catalog = [_attr("material", "Material", ["housing material"])]
    result = match_attributes(llm_attributes={"Housing Material": "Aluminum"}, catalog=catalog)
    assert "material" in result.mapped
    assert result.mapped["material"].confidence in ("exact", "alias")


def test_fuzzy_match():
    catalog = [_attr("voltage", "Voltage", ["rated voltage"])]
    result = match_attributes(llm_attributes={"Voltage Rating": "12V"}, catalog=catalog, fuzzy_threshold=85)
    assert "voltage" in result.mapped
    assert result.mapped["voltage"].confidence == "fuzzy"


def test_unmapped_keys_collected():
    catalog = [_attr("material", "Material")]
    result = match_attributes(llm_attributes={"Material": "Steel", "RandomField": "X"}, catalog=catalog)
    assert result.unmapped_from_llm == {"RandomField": "X"}
    assert "Material" not in result.unmapped_from_llm
