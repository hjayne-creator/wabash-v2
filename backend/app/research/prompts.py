"""Prompt builders for attribute research."""
from __future__ import annotations

import json

from app.models.db import ProductAttribute

_RESEARCH_JSON_SCHEMA_EXAMPLE = """{
  "product_found": boolean,
  "manufacturer_name": string,
  "manufacturer_product_number": string,
  "attributes": { "<attribute label>": "<value>", ... },
  "sources": [{ "url": string, "title": string }],
  "notes": string (optional)
}"""


def _research_instruction_bullets(*, include_sources_reminder: bool = False) -> list[str]:
    bullets = [
        "- Research as many product attributes as possible for the given product.",
        "- Use manufacturer websites, data sheets, and reseller listings as sources of truth.",
        "- Set `product_found` to `true` when the exact part is found or when a clearly equivalent "
        "listing is found, including alternate manufacturer product number formatting.",
        "- If no matching product can be found, set `product_found` to `false` and return empty attributes.",
        "- Populate only attributes that are supported by evidence.",
        "- Use an empty string for any unknown value.",
        "- Keep attribute values short and concise.",
        "- Respond with valid JSON only.",
        "- Do not use markdown fences.",
    ]
    if include_sources_reminder:
        bullets.insert(6, "- Always include sources with url and title.")
    return bullets


def _build_structured_research_instructions(*, include_sources_reminder: bool = False) -> str:
    return "\n".join(
        [
            "# Role and Objective",
            "You are a research specialist for commercial transportation parts.",
            "",
            "# Instructions",
            *_research_instruction_bullets(include_sources_reminder=include_sources_reminder),
            "",
            "# Output Format",
            "Return a JSON object that follows this schema:",
            "```json",
            _RESEARCH_JSON_SCHEMA_EXAMPLE,
            "```",
        ]
    )


def build_research_instructions() -> str:
    """System/instructions prompt for Perplexity and OpenAI (split message APIs)."""
    return _build_structured_research_instructions()


def build_openai_research_instructions() -> str:
    """OpenAI-recommended structured prompt; same rules as other engines."""
    return build_research_instructions()


def build_parallel_instructions() -> str:
    """Behavioral instructions for Parallel; output shape is enforced by task_spec."""
    return "\n".join(
        [
            "# Role and Objective",
            "You are a research specialist for commercial transportation parts.",
            "",
            "# Instructions",
            *_research_instruction_bullets(include_sources_reminder=True),
            "",
            "# Output Format",
            "Return structured JSON matching the provided output schema.",
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
    """Search-first single-message prompt for Brave Answers (user role only)."""
    user_query = build_research_input(
        manufacturer_name=manufacturer_name,
        manufacturer_product_number=manufacturer_product_number,
    )
    return "\n\n".join(
        [
            user_query,
            "# Role and Objective",
            "You are a research specialist for commercial transportation parts.",
            "",
            "# Instructions",
            *_research_instruction_bullets(),
            "",
            "# Output Format",
            "Return a JSON object that follows this schema:",
            "```json",
            _RESEARCH_JSON_SCHEMA_EXAMPLE,
            "```",
        ]
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


def build_engine_research_display(
    *,
    engine_provider: str,
    manufacturer_name: str,
    manufacturer_product_number: str,
    attributes: list[ProductAttribute] | None = None,
) -> tuple[str, str]:
    """Return (search query, full prompt) sent to the research engine."""
    catalog = attributes or []
    query = build_research_input(
        manufacturer_name=manufacturer_name,
        manufacturer_product_number=manufacturer_product_number,
    )
    if engine_provider == "brave":
        prompt = build_brave_research_message(
            manufacturer_name=manufacturer_name,
            manufacturer_product_number=manufacturer_product_number,
        )
    elif engine_provider == "parallel":
        task_input = build_parallel_task_input(
            manufacturer_name=manufacturer_name,
            manufacturer_product_number=manufacturer_product_number,
            attributes=catalog,
        )
        prompt = json.dumps(task_input, indent=2)
    elif engine_provider == "firecrawl":
        prompt = build_firecrawl_agent_prompt(
            manufacturer_name=manufacturer_name,
            manufacturer_product_number=manufacturer_product_number,
            attributes=catalog,
        )
    elif engine_provider == "openai":
        instructions = build_openai_research_instructions()
        prompt = f"{instructions}\n\n--- User input ---\n\n{query}"
    else:
        instructions = build_research_instructions()
        prompt = f"{instructions}\n\n--- User input ---\n\n{query}"
    return query, prompt


def build_firecrawl_agent_prompt(
    *,
    manufacturer_name: str,
    manufacturer_product_number: str,
    attributes: list[ProductAttribute],
) -> str:
    parts = [
        f"Extract all product attributes for the {manufacturer_name} {manufacturer_product_number}.",
        "Prioritize data from the official manufacturer followed by reseller listings.",
        "Include technical specifications, installation manuals, and links to technical drawings.",
        "Populate the structured output with discovered attributes and cite sources.",
    ]
    if attributes:
        labels = ", ".join(attr.label for attr in attributes[:40])
        parts.append(f"Target catalog attribute labels: {labels}.")
    return " ".join(parts)


def build_firecrawl_agent_schema(*, attributes: list[ProductAttribute]) -> dict[str, object]:
    return build_parallel_task_spec(attributes=attributes)["output_schema"]["json_schema"]


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
