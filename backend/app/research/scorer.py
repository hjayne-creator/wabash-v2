from __future__ import annotations

import json
import logging
import re

from pydantic import BaseModel, Field, ValidationError

from app.config import get_settings
from app.observability.run_usage import llm_step_context
from app.workflow.llm_router import LLMClientError, complete_text, provider_for_model

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You score how well a scraped product detail page matches a target manufacturer and manufacturer product number (MPN).

Return ONLY valid JSON (no markdown fences) with this shape:
{
  "overall_similarity_pct": <integer 0-100>,
  "criteria": [
    {"name": "Manufacturer match", "score_pct": <0-100>, "rationale": "<short>"},
    {"name": "MPN / SKU match", "score_pct": <0-100>, "rationale": "<short>"},
    {"name": "Product title alignment", "score_pct": <0-100>, "rationale": "<short>"},
    {"name": "Description relevance", "score_pct": <0-100>, "rationale": "<short>"},
    {"name": "Specs / attributes overlap", "score_pct": <0-100>, "rationale": "<short>"},
    {"name": "Page type (PDP vs listing)", "score_pct": <0-100>, "rationale": "<short>"}
  ]
}

Scoring guidance:
- 100 = exact/confident match on that criterion; 0 = no evidence.
- Penalize category pages, search results, and unrelated products heavily in "Page type" and overall.
- overall_similarity_pct should reflect weighted judgment across criteria, not a simple average.
- Weighting for overall similarity (approximate): MPN / SKU match 35%, Manufacturer match 20%, Product title alignment 20%, Specs / attributes overlap 15%, Page type 7%, Description relevance 3%.
- Treat exact normalized MPN matches in URL slug and scraped body as strong evidence, even when punctuation/hyphenation differs (e.g., 23471--3T80-71 vs 234713T8071).
- Description relevance is the weakest signal; generic ecommerce copy or short snippets should not meaningfully drag down an otherwise exact product match.
- If MPN is exact and manufacturer aligns, overall should generally be >= 80 unless there is strong contradiction (wrong product type, different manufacturer, or listing/search page).
- Treat SERP title/snippet as weak prior hints only. Do not rely on them to override contradictory scraped content.
- If scraped content does not look like a product detail page, cap confidence and avoid high overall scores.
"""


class _CriterionPayload(BaseModel):
    name: str
    score_pct: int = Field(ge=0, le=100)
    rationale: str = ""


class _ScorePayload(BaseModel):
    overall_similarity_pct: int = Field(ge=0, le=100)
    criteria: list[_CriterionPayload]


def _extract_json_object(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM response did not contain a JSON object.")
    return json.loads(stripped[start : end + 1])


async def score_source_match(
    *,
    manufacturer: str,
    mpn: str,
    url: str,
    serp_title: str,
    serp_snippet: str,
    tier: str,
    markdown: str,
    rule_mpn_found: bool,
    rule_manufacturer_match: bool,
) -> tuple[int, list[_CriterionPayload], str | None]:
    settings = get_settings()
    model = settings.wabash_match_model
    provider = provider_for_model(model)
    excerpt = markdown[: settings.wabash_scorer_max_chars]

    weak_title = serp_title[:160]
    weak_snippet = serp_snippet[:220]
    user = f"""Target manufacturer: {manufacturer}
Target MPN: {mpn}

Source URL: {url}
Source tier (heuristic): {tier}
Weak prior hint (SERP title, optional): {weak_title}
Weak prior hint (SERP snippet, optional): {weak_snippet}
Rule-based MPN detected in scrape: {rule_mpn_found}
Rule-based manufacturer match in scrape: {rule_manufacturer_match}

Scraped PDP content (markdown excerpt):
{excerpt}
"""

    try:
        with llm_step_context(step_no=1, step_name=f"score:{url[:48]}"):
            raw = await complete_text(model=model, provider=provider, system=_SYSTEM_PROMPT, user=user)
        payload = _ScorePayload.model_validate(_extract_json_object(raw))
        return payload.overall_similarity_pct, payload.criteria, None
    except (LLMClientError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        logger.warning("Scoring failed for %s: %s", url, exc)
        return 0, [], str(exc)
