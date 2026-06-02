"""Prompt builders for attribute research."""
from __future__ import annotations

from app.models.db import ProductAttribute


def build_research_instructions(*, attributes: list[ProductAttribute]) -> str:
    lines = [
        "You are a research expert for commercial transportation parts.",
        "Help research as many product attributes as possible for the given product.",
        "Use manufacturer sites, data sheets, and resellers as sources of truth.",
        "If you cannot find a matching product, set product_found to false and return empty attributes.",
        "Respond with valid JSON only, no markdown fences.",
        "",
        "Target attribute keys (use these exact keys when possible):",
    ]
    for attr in attributes:
        hint = f" — {attr.hint}" if attr.hint else ""
        alias_note = ""
        if attr.aliases_list():
            alias_note = f" (also known as: {', '.join(attr.aliases_list()[:5])})"
        lines.append(f"- {attr.label}{hint}{alias_note}")
    lines.extend(
        [
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
    return "\n".join(lines)


def build_parallel_instructions() -> str:
    # Parallel already receives attribute targets and an output JSON schema separately.
    # Keeping this short avoids repeating large attribute lists in both text and JSON.
    return "\n".join(
        [
            "You are a research expert for commercial transportation parts.",
            "Research as many product attributes as possible for the given product.",
            "Use manufacturer sites, data sheets, and reputable resellers as sources of truth.",
            "If you cannot find a matching product, set product_found to false and return empty attributes.",
            "Respond with valid JSON only (no markdown fences).",
            "Populate only attributes supported by evidence; use empty string when not found.",
            "Always include sources with url and title.",
        ]
    )


def build_research_input(*, manufacturer_name: str, manufacturer_product_number: str) -> str:
    return (
        f"Research product attributes for:\n"
        f"Manufacturer: {manufacturer_name}\n"
        f"Manufacturer product number (MPN): {manufacturer_product_number}\n"
        f"Return comprehensive attributes and cite sources."
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
