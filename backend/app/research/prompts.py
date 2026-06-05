"""Prompt builders for attribute research."""
from __future__ import annotations


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
            "Respond with valid JSON only (no markdown fences).",
            "Populate only attributes supported by evidence; use empty string when not found.",
            "Always include sources with url and title.",
        ]
    )


def build_research_input(*, manufacturer_name: str, manufacturer_product_number: str) -> str:
    return (
        f"Find specifications and datasheets for {manufacturer_name} part "
        f"{manufacturer_product_number} (commercial transportation / trailer parts).\n"
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
        f"{manufacturer_product_number} (commercial transportation / trailer parts).\n"
        "Search manufacturer websites, PDF datasheets, and reputable parts catalogs.\n"
        "Set product_found to true when the exact part or a clearly equivalent listing is found "
        "(including alternate MPN formatting).\n"
        "Populate only attributes supported by evidence; use an empty string when unknown.\n\n"
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
) -> dict[str, object]:
    return {
        "manufacturer_name": manufacturer_name,
        "manufacturer_product_number": manufacturer_product_number,
        "instructions": build_parallel_instructions(),
        "query": build_research_input(
            manufacturer_name=manufacturer_name,
            manufacturer_product_number=manufacturer_product_number,
        ),
    }


def _parallel_attributes_object_schema() -> dict[str, object]:
    return {
        "type": "object",
        "description": (
            "Discovered product specifications keyed by attribute name or label. "
            "Populate only fields with evidence; use empty string when not found."
        ),
        "additionalProperties": {"type": "string"},
    }


def build_parallel_task_spec() -> dict[str, object]:
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
                    "attributes": _parallel_attributes_object_schema(),
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
