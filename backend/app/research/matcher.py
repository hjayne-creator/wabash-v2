from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.research.ranker import (
    MANUFACTURER_SOURCE_TIERS,
    MATCH_TRUSTED_TIERS,
    SOURCE_TIER_COMPETITOR,
)

# Cap how much of a huge page we scan for coincidental MPN hits.
_MATCH_SCAN_LIMIT = 100_000
_COLOCATE_WINDOW = 800
_PRODUCT_PAGE_SCAN_LIMIT = 120_000

RESEARCH_TIER_EXACT_MANUFACTURER = "exact_manufacturer"
RESEARCH_TIER_FAMILY_SERIES = "family_series"
RESEARCH_TIER_COMPETITOR_PROXY = "competitor_proxy"
RESEARCH_TIER_NONE = "none"

_PRODUCT_SIGNAL_PATTERNS: tuple[tuple[str, tuple[str, ...], int], ...] = (
    ("technical_specifications", ("technical specifications", "specifications", "spec sheet"), 25),
    ("part_number", ("part number", "mpn", "manufacturer part number", "model number"), 22),
    ("part_type", ("part type", "product type", "type:"), 8),
    ("weight", ("weight", "lbs", "kg"), 8),
    ("dimensions", ("dimensions", "dimension", "size", "length", "width", "height"), 8),
    ("datasheet_pdf", ("datasheet", "download pdf", ".pdf", "pdf"), 10),
    ("availability", ("in stock", "lead time", "minimum order", "moq"), 6),
    ("sku_or_upc", ("sku", "upc", "ean"), 6),
    ("product_metadata", ("features", "attributes", "specs"), 7),
)


def normalize_mpn(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value or "").upper()


def normalize_manufacturer(value: str) -> str:
    s = re.sub(r"[^\w\s]", " ", value or "", flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip().lower()


def normalize_family_hint(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value or "").upper()


def normalize_product_inputs(manufacturer: str, mpn: str) -> tuple[str, str]:
    """Strip a duplicated MPN from the manufacturer field when users paste both together."""
    mfg = (manufacturer or "").strip()
    part = (mpn or "").strip()
    if not part:
        return mfg, part

    pattern = re.compile(rf"\b{re.escape(part)}\b", flags=re.IGNORECASE)
    mfg = pattern.sub("", mfg)
    mfg = re.sub(r"\s+", " ", mfg).strip(" ,;-")
    return mfg, part


def manufacturer_matches(source_text: str, manufacturer: str, *, threshold: float = 0.72) -> bool:
    norm_source = normalize_manufacturer(source_text)
    norm_target = normalize_manufacturer(manufacturer)
    if not norm_target:
        return False
    if norm_target in norm_source:
        return True
    tokens = [t for t in norm_target.split() if len(t) >= 3]
    if tokens and sum(1 for t in tokens if t in norm_source) >= max(1, len(tokens) - 1):
        return True
    return SequenceMatcher(None, norm_target, norm_source).ratio() >= threshold


_MPN_BODY_LINK = re.compile(r"\[([^\]]*)\]\((?:[^)(]|\([^)]*\))*\)")
_MPN_BODY_BARE_URL = re.compile(r"https?://\S+")
_MPN_BODY_PRODUCT_MARKERS = (
    "part number",
    "part #",
    "part:",
    "mpn",
    "manufacturer part",
    "brand:",
    "specifications",
    "technical specifications",
    "vmrs",
    "model number",
    "sku",
    "upc",
)


def _strip_links_for_mpn_scan(line: str) -> str:
    text = _MPN_BODY_LINK.sub(lambda match: match.group(1).strip(), line)
    return _MPN_BODY_BARE_URL.sub("", text).strip()


def _text_without_urls(text: str) -> str:
    return _MPN_BODY_BARE_URL.sub(" ", text[:_MATCH_SCAN_LIMIT])


def _line_has_mpn_product_marker(line: str) -> bool:
    lower = line.lower()
    return any(marker in lower for marker in _MPN_BODY_PRODUCT_MARKERS)


def exact_mpn_in_body(text: str, mpn: str) -> bool:
    """True when MPN appears in visible body text, not only in link labels or URLs."""
    target = normalize_mpn(mpn)
    part = mpn.strip()
    if not target or not part:
        return False

    for line in text.splitlines():
        raw = line.strip()
        if not raw:
            continue
        visible = _strip_links_for_mpn_scan(line)
        if target not in normalize_mpn(visible):
            continue
        if _line_has_mpn_product_marker(raw) or _line_has_mpn_product_marker(visible):
            return True
        if re.fullmatch(rf"{re.escape(part)}", visible.strip(), re.IGNORECASE):
            return True
        if re.search(rf"(?:part|mpn|sku|model)\s*[:#]?\s*{re.escape(part)}", visible, re.IGNORECASE):
            return True
        if _MPN_BODY_LINK.fullmatch(raw) and not _line_has_mpn_product_marker(visible):
            continue
        if re.search(rf"\b{re.escape(part)}\b", visible, re.IGNORECASE):
            return True

    stripped = text.strip()
    if "\n" not in stripped and not _MPN_BODY_LINK.search(stripped):
        visible = _strip_links_for_mpn_scan(_text_without_urls(stripped))
        if re.search(rf"\b{re.escape(part)}\b", visible, re.IGNORECASE):
            return True
    return False


def exact_mpn_in_text(text: str, mpn: str) -> bool:
    return exact_mpn_in_body(text, mpn)


def family_hint_in_text(text: str, family_hint: str) -> bool:
    target = normalize_family_hint(family_hint)
    if not target or len(target) < 2:
        return False
    compact = normalize_family_hint(text[:_MATCH_SCAN_LIMIT])
    if target in compact:
        return True
    pattern = re.escape(family_hint.strip())
    if pattern and re.search(pattern, text[:_MATCH_SCAN_LIMIT], flags=re.IGNORECASE):
        return True
    return False


def mpn_and_manufacturer_cooccur(text: str, manufacturer: str, mpn: str) -> bool:
    """Require MPN and manufacturer to appear near each other in the same source."""
    if not exact_mpn_in_text(text, mpn):
        return False

    scan = _text_without_urls(text)
    pattern = re.compile(re.escape(mpn.strip()), flags=re.IGNORECASE)
    for match in pattern.finditer(scan):
        start = max(0, match.start() - _COLOCATE_WINDOW)
        end = min(len(scan), match.end() + _COLOCATE_WINDOW)
        if manufacturer_matches(scan[start:end], manufacturer):
            return True
    return False


def source_supports_product_match(
    text: str,
    *,
    manufacturer: str,
    mpn: str,
    tier: str,
) -> bool:
    if tier not in MATCH_TRUSTED_TIERS:
        return False
    return mpn_and_manufacturer_cooccur(text, manufacturer, mpn)


def source_supports_exact_manufacturer_match(
    text: str,
    *,
    manufacturer: str,
    mpn: str,
    tier: str,
) -> bool:
    if tier not in MANUFACTURER_SOURCE_TIERS:
        return False
    return mpn_and_manufacturer_cooccur(text, manufacturer, mpn)


def source_supports_family_match(
    text: str,
    *,
    manufacturer: str,
    family_hint: str,
    tier: str,
) -> bool:
    if tier not in MANUFACTURER_SOURCE_TIERS:
        return False
    if not family_hint_in_text(text, family_hint):
        return False
    return manufacturer_matches(text, manufacturer)


def source_supports_competitor_match(text: str, *, tier: str) -> bool:
    return tier == SOURCE_TIER_COMPETITOR and bool(text.strip())


def product_page_signals(text: str) -> tuple[list[str], int]:
    scan = (text or "")[:_PRODUCT_PAGE_SCAN_LIMIT]
    lowered = scan.lower()
    matched: list[str] = []
    total = 0
    for signal, terms, weight in _PRODUCT_SIGNAL_PATTERNS:
        if any(term in lowered for term in terms):
            matched.append(signal)
            total += weight
    return matched, min(total, 100)


def compute_product_page_score(
    text: str,
    *,
    manufacturer: str = "",
    mpn: str = "",
) -> tuple[int, bool, list[str]]:
    signals, score = product_page_signals(text)
    if manufacturer and mpn and exact_mpn_in_text(text, mpn) and manufacturer_matches(text, manufacturer):
        if "target_product_evidence" not in signals:
            signals = [*signals, "target_product_evidence"]
        score = min(100, score + 40)
    # A medium threshold keeps recall while filtering obvious non-product pages.
    return score, score >= 35, signals


def compute_product_match_score(
    text: str,
    *,
    manufacturer: str,
    mpn: str,
    tier: str,
) -> int:
    if not text.strip():
        return 0

    mpn_match = exact_mpn_in_text(text, mpn)
    manufacturer_match = manufacturer_matches(text, manufacturer)
    colocated = mpn_and_manufacturer_cooccur(text, manufacturer, mpn)

    score = 0
    if mpn_match:
        score += 55
    if manufacturer_match:
        score += 25
    if colocated:
        score += 15
    if tier in MATCH_TRUSTED_TIERS and (mpn_match or colocated):
        score += 5
    return min(score, 100)


@dataclass
class MatchAssessment:
    verified: bool
    reason: str
    manufacturer_match: bool
    mpn_match: bool
    trusted_source_count: int = 0


@dataclass
class ResearchTierAssessment:
    research_tier: str
    verified: bool
    reason: str
    manufacturer_match: bool
    mpn_match: bool
    family_match: bool
    trusted_source_count: int = 0


def assess_product_match(
    *,
    manufacturer: str,
    mpn: str,
    sources: list[tuple[str, str, str]],
) -> MatchAssessment:
    """Assess match using per-source (text, tier, url) tuples from trusted sources only."""
    trusted_hits = 0
    any_mpn = False
    any_manufacturer = False

    for text, tier, _url in sources:
        if not text or tier not in MATCH_TRUSTED_TIERS:
            continue
        if exact_mpn_in_text(text, mpn):
            any_mpn = True
        if manufacturer_matches(text, manufacturer):
            any_manufacturer = True
        if source_supports_product_match(text, manufacturer=manufacturer, mpn=mpn, tier=tier):
            trusted_hits += 1

    if trusted_hits >= 1:
        return MatchAssessment(
            True,
            "Exact MPN and manufacturer evidence found on a trusted source.",
            any_manufacturer,
            any_mpn,
            trusted_hits,
        )
    if any_mpn and not any_manufacturer:
        return MatchAssessment(
            False,
            "Exact MPN found but manufacturer name could not be verified in sources.",
            any_manufacturer,
            any_mpn,
            trusted_hits,
        )
    if any_mpn:
        return MatchAssessment(
            False,
            "MPN appeared in sources but not with the manufacturer on a trusted product page.",
            any_manufacturer,
            any_mpn,
            trusted_hits,
        )
    return MatchAssessment(
        False,
        "Exact product match could not be verified.",
        any_manufacturer,
        any_mpn,
        trusted_hits,
    )


def assess_research_tier(
    *,
    manufacturer: str,
    mpn: str,
    family_hint: str,
    sources: list[tuple[str, str, str, bool]],
) -> ResearchTierAssessment:
    """Resolve three-tier hierarchy: (text, tier, url, scrape_ok) tuples."""
    exact_hits = 0
    family_hits = 0
    competitor_hits = 0
    any_mpn = False
    any_manufacturer = False
    any_family = False

    for text, tier, _url, scrape_ok in sources:
        if not text or not scrape_ok:
            continue
        if exact_mpn_in_text(text, mpn):
            any_mpn = True
        if manufacturer_matches(text, manufacturer):
            any_manufacturer = True
        if family_hint and family_hint_in_text(text, family_hint):
            any_family = True
        if source_supports_exact_manufacturer_match(text, manufacturer=manufacturer, mpn=mpn, tier=tier):
            exact_hits += 1
        elif family_hint and source_supports_family_match(
            text, manufacturer=manufacturer, family_hint=family_hint, tier=tier
        ):
            family_hits += 1
        elif source_supports_competitor_match(text, tier=tier):
            competitor_hits += 1

    if exact_hits >= 1:
        return ResearchTierAssessment(
            RESEARCH_TIER_EXACT_MANUFACTURER,
            True,
            "Exact MPN and manufacturer evidence found on manufacturer site.",
            any_manufacturer,
            any_mpn,
            any_family,
            exact_hits,
        )
    if family_hits >= 1:
        return ResearchTierAssessment(
            RESEARCH_TIER_FAMILY_SERIES,
            True,
            "Product family/series evidence found on manufacturer site (exact MPN may not appear).",
            any_manufacturer,
            any_mpn,
            any_family,
            family_hits,
        )
    if competitor_hits >= 1:
        return ResearchTierAssessment(
            RESEARCH_TIER_COMPETITOR_PROXY,
            True,
            "No manufacturer data found; using competitor product pages as research proxy.",
            any_manufacturer,
            any_mpn,
            any_family,
            competitor_hits,
        )
    if any_mpn and not any_manufacturer:
        return ResearchTierAssessment(
            RESEARCH_TIER_NONE,
            False,
            "Exact MPN found but manufacturer name could not be verified in sources.",
            any_manufacturer,
            any_mpn,
            any_family,
            0,
        )
    if any_mpn:
        return ResearchTierAssessment(
            RESEARCH_TIER_NONE,
            False,
            "MPN appeared in sources but not with the manufacturer on a trusted product page.",
            any_manufacturer,
            any_mpn,
            any_family,
            0,
        )
    return ResearchTierAssessment(
        RESEARCH_TIER_NONE,
        False,
        "Product match could not be verified at any research tier.",
        any_manufacturer,
        any_mpn,
        any_family,
        0,
    )
