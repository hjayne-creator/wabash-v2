"""Parse JSON from LLM text responses."""
from __future__ import annotations

import json
import re
from typing import Any


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        raise ValueError("Empty response")
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped)
    if fence:
        parsed = json.loads(fence.group(1).strip())
        if isinstance(parsed, dict):
            return parsed
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        parsed = json.loads(stripped[start : end + 1])
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("Could not parse JSON object from model response")
