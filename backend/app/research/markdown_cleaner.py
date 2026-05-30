"""Heuristic cleanup of Firecrawl PDP markdown before matching and LLM scoring."""
from __future__ import annotations

import re
_NOISE_SECTION_PHRASES = (
    "related parts",
    "related products",
    "you may also like",
    "complete the job",
    "related searches",
    "customers also bought",
    "recently viewed",
    "recommended products",
    "similar products",
    "cross reference",
    "check nearby stores",
)


def _line_is_noise_section(line: str) -> bool:
    normalized = re.sub(r"[*#\-]", " ", line).lower()
    return any(phrase in normalized for phrase in _NOISE_SECTION_PHRASES)

_IMG_LINE = re.compile(r"^\s*!\[[^\]]*\]\([^)]*\)\s*$")
_LINK = re.compile(r"\[([^\]]*)\]\((?:[^)(]|\([^)]*\))*\)")
_BARE_URL = re.compile(r"https?://\S+")

_PRODUCT_MARKERS = (
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

_BOILERPLATE_LINE = re.compile(
    r"^(?:"
    r"\[?Skip (?:Navigation|to Main Content)|"
    r"Add To Cart|"
    r"Quantity:?|"
    r"\d+\s*Available (?:for Delivery|at)|"
    r"Available at|"
    r"Check Nearby Stores|"
    r"Use My Location|"
    r"No nearby stores found|"
    r"Chat Now|"
    r"No Thanks|"
    r"Enable accessibility|"
    r"Open the accessibility menu|"
    r"protected by \*\*reCAPTCHA\*\*|"
    r"Recaptcha requires verification|"
    r"Close Notification|"
    r"Success|Warning|Error"
    r")\b",
    re.IGNORECASE,
)

_NAV_PATH_MARKERS = ("/categories/", "/top-sellers/", "/blog/", "/login", "/signup", "/orders/lookup")


def _line_has_product_marker(line: str) -> bool:
    lower = line.lower()
    return any(marker in lower for marker in _PRODUCT_MARKERS)


def _line_looks_like_product_content(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if _line_has_product_marker(stripped):
        return True
    heading = re.match(r"^(#{1,3})\s+(.+)$", stripped)
    if heading and not _NAV_PATH_MARKERS[0] in stripped:
        title = heading.group(2)
        if "](" not in title:
            return True
        if title.index("#") if "#" in title else 0 < title.index("]("):
            return True
    return False


def _should_drop_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    plain = re.sub(r"\*\*([^*]+)\*\*", r"\1", stripped)
    if _BOILERPLATE_LINE.search(plain):
        return True
    if any(marker in stripped for marker in _NAV_PATH_MARKERS):
        return True
    if stripped.count("](") >= 3 and not _line_has_product_marker(stripped):
        return True
    if stripped.startswith("- [") and "/categories/" in stripped:
        return True
    if re.match(r"^\[.+\]\(.+\)(?:\[.+\]\(.+\)){2,}", stripped) and not _line_has_product_marker(stripped):
        return True
    return False


def _strip_markdown_links(line: str) -> str:
    without_images = _IMG_LINE.sub("", line)
    text = _LINK.sub(lambda m: m.group(1).strip(), without_images)
    return _BARE_URL.sub("", text).strip()


def _skip_leading_nav(text: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if _line_looks_like_product_content(line):
            return "\n".join(lines[index:])
    return text


def _truncate_at_noise_section(text: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if _line_is_noise_section(line):
            return "\n".join(lines[:index]).rstrip()
    return text


def _collapse_blank_lines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text.strip())


def clean_pdp_markdown(markdown: str) -> str:
    """Remove ecommerce chrome while preserving product identity and spec blocks."""
    if not markdown.strip():
        return ""

    trimmed = _truncate_at_noise_section(markdown)
    trimmed = _skip_leading_nav(trimmed)

    kept: list[str] = []
    for line in trimmed.splitlines():
        if _IMG_LINE.match(line) or _should_drop_line(line):
            continue
        cleaned_line = _strip_markdown_links(line)
        if cleaned_line:
            kept.append(cleaned_line)

    return _collapse_blank_lines("\n".join(kept))


def _score_anchor_position(text: str, position: int, mpn: str) -> int:
    line_start = text.rfind("\n", 0, position) + 1
    line_end = text.find("\n", position)
    if line_end == -1:
        line_end = len(text)
    line = text[line_start:line_end]
    lower = line.lower()

    score = 0
    if _line_has_product_marker(line):
        score += 20
    if re.match(r"^#{1,3}\s+", line.strip()):
        score += 15
    if mpn and mpn.lower() in lower:
        score += 10
    if line.count("](") >= 2:
        score -= 15
    if any(marker in line for marker in _NAV_PATH_MARKERS):
        score -= 20
    if re.search(r"\]\([^)]*/products/", line, re.IGNORECASE) and not _line_has_product_marker(line):
        score -= 5
    return score


def _find_excerpt_anchor(text: str, *, mpn: str, manufacturer: str) -> int:
    if not text:
        return 0

    candidates: list[tuple[int, int]] = []

    if mpn.strip():
        pattern = re.compile(re.escape(mpn.strip()), flags=re.IGNORECASE)
        for match in pattern.finditer(text):
            candidates.append((match.start(), _score_anchor_position(text, match.start(), mpn)))

    for marker in _PRODUCT_MARKERS:
        marker_pattern = re.compile(rf"^#{{0,3}}\s*.*{re.escape(marker)}", re.IGNORECASE | re.MULTILINE)
        for match in marker_pattern.finditer(text):
            candidates.append((match.start(), 18))

    for match in re.finditer(r"^#{1}\s+\S", text, re.MULTILINE):
        candidates.append((match.start(), _score_anchor_position(text, match.start(), mpn)))

    if manufacturer.strip():
        mfg_pattern = re.compile(re.escape(manufacturer.strip()), flags=re.IGNORECASE)
        for match in mfg_pattern.finditer(text):
            candidates.append((match.start(), _score_anchor_position(text, match.start(), mpn) + 5))

    if not candidates:
        return 0

    candidates.sort(key=lambda item: (-item[1], item[0]))
    return candidates[0][0]


def product_focused_excerpt(
    markdown: str,
    *,
    mpn: str,
    manufacturer: str = "",
    max_chars: int,
    before_chars: int = 2_000,
) -> str:
    """Return a char-limited slice centered on product identity signals."""
    text = markdown.strip()
    if not text:
        return ""
    if len(text) <= max_chars:
        return text

    anchor = _find_excerpt_anchor(text, mpn=mpn, manufacturer=manufacturer)
    start = max(0, anchor - before_chars)
    end = min(len(text), start + max_chars)
    if end - start < max_chars:
        start = max(0, end - max_chars)

    excerpt = text[start:end].strip()
    if start > 0:
        excerpt = "[…]\n" + excerpt
    if end < len(text):
        excerpt = excerpt + "\n[…]"
    return excerpt


def process_scraped_markdown(raw: str, url: str, settings=None) -> str:
    """Clean PDP markdown and apply scrape size limits."""
    from app.research.scrape_limits import cap_scraped_markdown

    cleaned = clean_pdp_markdown(raw)
    return cap_scraped_markdown(cleaned, url, settings)


def normalized_mpn_in_body(text: str, mpn: str) -> bool:
    """Alias for matcher body-only MPN detection."""
    from app.research.matcher import exact_mpn_in_body

    return exact_mpn_in_body(text, mpn)
