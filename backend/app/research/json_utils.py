"""Parse JSON from LLM text responses."""
from __future__ import annotations

import json
import re
from typing import Any


def _repair_json(text: str) -> str:
    """Fix common LLM JSON mistakes before parsing."""
    repaired = re.sub(r",(\s*[}\]])", r"\1", text)
    return repaired


def _loads_dict(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            parsed = json.loads(_repair_json(text))
        except json.JSONDecodeError:
            return None
    if isinstance(parsed, dict):
        return parsed
    return None


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        raise ValueError("Empty response")

    parsed = _loads_dict(stripped)
    if parsed is not None:
        return parsed

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped)
    if fence:
        parsed = _loads_dict(fence.group(1).strip())
        if parsed is not None:
            return parsed

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        parsed = _loads_dict(stripped[start : end + 1])
        if parsed is not None:
            return parsed

    raise ValueError("Could not parse JSON object from model response")
