"""Prompt builders for attribute research."""
from __future__ import annotations

from app.models.db import ProductAttribute


def build_research_instructions() -> str:
    return "\n".join(
        [
            "You are a research expert for commercial transportation parts.",
            "Help research as many product attributes as possible for the given product.",
            "Use manufacturer sites, data sheets, and resellers as sources of truth.",
            "Set product_found to true when the exact part or a clearly equivalent listing is found "
            "(including alternate MPN formatting).",
            "If you cannot find a matching product, set product_found to false and return empty attributes.",
            "Populate only attributes supported by evidence; use an empty string when unknown.",
            "Keep attribute values short and concise.",
            "Respond with valid JSON only, no markdown fences.",
            "",
            "JSON schema:",
            "{",
            '  "product_found": boolean,',
            '  "manufacturer_name": string,',
            '  "manufacturer_product_number": string,',
            '  "attributes": { "<attribute label>": "<value>", ... },',
            '  "sources": [{ "url": string, "title": string }],',
            '  "notes": string (optional)',
            "}",
        ]
    )


def build_parallel_instructions() -> str:
    return "\n".join(
        [
            "You are a research expert for commercial transportation parts.",
            "Research as many product attributes as possible for the given product.",
            "Use manufacturer sites, data sheets, and reputable resellers as sources of truth.",
            "Set product_found to true when the exact part or a clearly equivalent listing is found "
            "(including alternate MPN formatting).",
            "If you cannot find a matching product, set product_found to false and return empty attributes.",
            "Populate only attributes supported by evidence; use empty string when not found.",
            "Always include sources with url and title.",
            "Keep attribute values short and concise.",
            "Respond with valid JSON only (no markdown fences).",
            ]
    )


def build_research_input(*, manufacturer_name: str, manufacturer_product_number: str) -> str:
    return (
        f"Find specifications and datasheets for {manufacturer_name} part "
        f"{manufacturer_product_number} (commercial transportation / industrial parts).\n"
        "Search manufacturer websites, PDF datasheets, and reputable parts catalogs.\n"
        "Return comprehensive attributes and cite sources."
    )


def build_brave_research_message(
    *,
    manufacturer_name: str,
    manufacturer_product_number: str,
) -> str:
    """Compact, search-first prompt for Brave Answers (single-message API)."""
    return (
        f"Find specifications and datasheets for {manufacturer_name} part "
        f"{manufacturer_product_number} (commercial transportation / industrial parts).\n"
        "Search manufacturer websites, PDF datasheets, and reputable parts catalogs.\n"
        "Set product_found to true when the exact part or a clearly equivalent listing is found "
        "(including alternate MPN formatting).\n"
        "Populate only attributes supported by evidence; use an empty string when unknown.\n"
        "Keep attribute values short and concise.\n\n"
        "Return valid JSON only (no markdown fences):\n"
        "{\n"
        '  "product_found": boolean,\n'
        '  "manufacturer_name": string,\n'
        '  "manufacturer_product_number": string,\n'
        '  "attributes": { "<attribute label>": "<value>", ... },\n'
        '  "sources": [{ "url": string, "title": string }],\n'
        '  "notes": string (optional)\n'
        "}"
    )


def build_parallel_task_input(
    *,
    manufacturer_name: str,
    manufacturer_product_number: str,
    attributes: list[ProductAttribute],
) -> dict[str, object]:
    targets: list[dict[str, str]] = []
    for attr in attributes:
        entry: dict[str, str] = {"label": attr.label}
        if attr.hint:
            entry["hint"] = attr.hint
        aliases = attr.aliases_list()
        if aliases:
            entry["aliases"] = ", ".join(aliases[:8])
        targets.append(entry)
    return {
        "manufacturer_name": manufacturer_name,
        "manufacturer_product_number": manufacturer_product_number,
        "instructions": build_parallel_instructions(),
        "attribute_targets": targets,
        "query": build_research_input(
            manufacturer_name=manufacturer_name,
            manufacturer_product_number=manufacturer_product_number,
        ),
    }


def _parallel_attribute_field_schema(attr: ProductAttribute) -> dict[str, str]:
    parts = [f"Value for catalog attribute '{attr.label}'."]
    if attr.hint:
        parts.append(attr.hint)
    aliases = attr.aliases_list()
    if aliases:
        parts.append(f"Also known as: {', '.join(aliases[:8])}.")
    parts.append("If not found from authoritative sources, return an empty string.")
    return {"type": "string", "description": " ".join(parts)}


def _parallel_attributes_object_schema(
    attributes: list[ProductAttribute],
) -> dict[str, object]:
    """Parallel Task API requires non-empty `properties` on every object schema."""
    properties: dict[str, object] = {
        attr.label: _parallel_attribute_field_schema(attr) for attr in attributes
    }
    if not properties:
        properties = {
            "specification": {
                "type": "string",
                "description": "Any discovered product specification when no catalog is configured.",
            }
        }
    return {
        "type": "object",
        "description": (
            "Discovered product specifications keyed by catalog attribute label. "
            "Populate only fields with evidence; use empty string when not found."
        ),
        "additionalProperties": False,
        "properties": properties,
    }


def build_parallel_task_spec(*, attributes: list[ProductAttribute]) -> dict[str, object]:
    return {
        "output_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "product_found": {
                        "type": "boolean",
                        "description": (
                            "True if a matching product was identified from authoritative sources; "
                            "otherwise false."
                        ),
                    },
                    "manufacturer_name": {"type": "string"},
                    "manufacturer_product_number": {"type": "string"},
                    "attributes": _parallel_attributes_object_schema(attributes),
                    "sources": {
                        "type": "array",
                        "description": "URLs used as evidence, prefer manufacturer and datasheet pages.",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "url": {"type": "string"},
                                "title": {"type": "string"},
                            },
                            "required": ["url", "title"],
                        },
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional caveats, conflicts, or gaps in the research.",
                    },
                },
                "required": [
                    "product_found",
                    "manufacturer_name",
                    "manufacturer_product_number",
                    "attributes",
                    "sources",
                ],
            },
        }
    }
