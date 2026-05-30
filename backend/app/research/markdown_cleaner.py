"""Heuristic cleanup of Firecrawl PDP markdown before matching and LLM scoring."""
from __future__ import annotations

import re

_NOISE_SECTION_PHRASES = (
    "related parts",
    "related products",
    "you may also like",
    "complete the job",
    "related searches",
    "popular searches",
    "popular products",
    "customers also bought",
    "recently viewed",
    "recommended products",
    "similar products",
    "cross reference",
    "check nearby stores",
    "find other stores",
    "customer reviews",
    "questions & answers",
    "questions and answers",
    "write a review",
    "ask a question",
    "review guidelines",
    "prop 65 warning",
)

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
    "part description",
    "vmrs",
    "model number",
    "sku",
    "upc",
    "msrp:",
)

_BOILERPLATE_LINE = re.compile(
    r"^(?:"
    r"\[?Skip (?:Navigation|to Main Content)|"
    r"Add To Cart|"
    r"Quantity:?|"
    r"\d+\s*Available (?:for Delivery|at)|"
    r"Available at|"
    r"Check Nearby Stores|"
    r"Find Other Stores|"
    r"Use My Location|"
    r"No nearby stores found|"
    r"Chat Now|"
    r"No Thanks|"
    r"Enable accessibility|"
    r"Open the accessibility menu|"
    r"protected by \*\*reCAPTCHA\*\*|"
    r"Recaptcha requires verification|"
    r"Please complete the reCAPTCHA|"
    r"Close Notification|"
    r"Success|Warning|Error|"
    r"Address is Required|"
    r"Maximum character limit|"
    r"Details \\| Directions|"
    r"Open till|"
    r"Closed until|"
    r"POPULAR SEARCHES|"
    r"POPULAR PRODUCTS|"
    r"Add Vehicle|"
    r"Sign In|"
    r"Create an Account|"
    r"Join eCash|"
    r"View All Benefits|"
    r"Shop All \d+ Categories|"
    r"Categories|"
    r"Parts Finder|"
    r"Find Service|"
    r"Diagrams|"
    r"Quick Order|"
    r"Quick CHECKOUT|"
    r"Buy withPay|"
    r"Minus-Plus\+|"
    r"Collapse All|"
    r"No HassleReturn Policy|"
    r"Free Economy shipping|"
    r"Limited availability at this price|"
    r"Write a Review|"
    r"Ask a question|"
    r"Cancel|"
    r"Display Name|"
    r"Order Number|"
    r"Upload Images|"
    r"Review Title|"
    r"Your Review|"
    r"Your Question|"
    r"Email Address|"
    r"Rating\*|"
    r"PICKUP|"
    r"SHIP|"
    r"PARCEL ELIGIBLE|"
    r"Styling span|"
    r"Get it est\.|"
    r"Get it by |"
    r"quick checkout|"
    r"minus-plus|"
    r"orders placed over the weekend|"
    r"^Not available$|"
    r"^Available$"
    r")\b",
    re.IGNORECASE,
)

_STORE_DISTANCE = re.compile(r"^(?:\d+\.\d+ miles|> 250 miles)$", re.IGNORECASE)
_STORE_PHONE = re.compile(r"^\(\d{3}\) \d{3}-\d{4}$")
_STAR_RATING = re.compile(r"^[★☆]+")
_NAV_PATH_MARKERS = ("/categories/", "/top-sellers/", "/blog/", "/login", "/signup", "/orders/lookup")
_NAV_BULLET_HINTS = (
    "service center",
    "truck repair",
    "trailer repair",
    "parts finder",
    "air springs",
    "brake rotors",
    "view all service",
)


def _line_has_product_marker(line: str) -> bool:
    lower = line.lower()
    return any(marker in lower for marker in _PRODUCT_MARKERS)


def _line_looks_like_product_content(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if _line_is_noise_section(line):
        return False
    if _line_has_product_marker(stripped):
        return True
    if re.search(r"\bpart\s*#", stripped, re.IGNORECASE):
        return True
    if re.search(r"\bmpn\s*#", stripped, re.IGNORECASE):
        return True
    if re.match(r"^#\s+\S", stripped) and re.search(r"\b[A-Z0-9]{3,}[A-Z0-9\-]*\b", stripped):
        return True
    heading = re.match(r"^(#{1,3})\s+(.+)$", stripped)
    if heading and not any(marker in stripped for marker in _NAV_PATH_MARKERS):
        title = heading.group(2)
        if _line_has_product_marker(title) or re.search(r"\b[A-Z0-9]{3,}[A-Z0-9\-]*\b", title):
            return True
    return False


def _should_drop_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    plain = re.sub(r"\*\*([^*]+)\*\*", r"\1", stripped)
    if _BOILERPLATE_LINE.search(plain):
        return True
    if _STORE_DISTANCE.match(plain):
        return True
    if _STORE_PHONE.match(plain):
        return True
    if _STAR_RATING.match(plain):
        return True
    if any(marker in stripped for marker in _NAV_PATH_MARKERS):
        return True
    if stripped.count("](") >= 3 and not _line_has_product_marker(stripped):
        return True
    if stripped.startswith("- [") and "/categories/" in stripped:
        return True
    if stripped.startswith("- ") and not _line_has_product_marker(stripped):
        lower = stripped.lower()
        if any(hint in lower for hint in _NAV_BULLET_HINTS):
            return True
    if re.match(r"^\[.+\]\(.+\)(?:\[.+\]\(.+\)){2,}", stripped) and not _line_has_product_marker(stripped):
        return True
    if re.match(r"^!\S", stripped):
        return True
    if re.match(r"^Get it est\.", plain, re.IGNORECASE):
        return True
    if re.search(r"quick\s*checkout", plain, re.IGNORECASE):
        return True
    if re.match(r"^[A-Za-z .'-]+, [A-Z]{2}$", plain):
        return True
    return False


def _strip_markdown_links(line: str) -> str:
    without_images = _IMG_LINE.sub("", line)
    text = _LINK.sub(lambda match: match.group(1).strip(), without_images)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = text.replace("\\|", "|")
    return _BARE_URL.sub("", text).strip()


def _line_is_noise_section(line: str) -> bool:
    normalized = re.sub(r"[*#\-]", " ", line).lower()
    return any(phrase in normalized for phrase in _NOISE_SECTION_PHRASES)


def _line_is_noise_section_header(line: str) -> bool:
    stripped = line.strip()
    if not _line_is_noise_section(stripped):
        return False
    if re.match(r"^#{1,6}\s+", stripped):
        return True
    if re.match(r"^\*{1,2}.+\*{1,2}\s*$", stripped):
        return True
    return False


def _skip_leading_nav(text: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if _line_looks_like_product_content(line):
            return "\n".join(lines[index:])
    return text


def _truncate_at_noise_section(text: str) -> str:
    """Drop trailing sections like reviews/Q&A once product content has started."""
    lines = text.splitlines()
    seen_product = False
    kept: list[str] = []
    for line in lines:
        if _line_looks_like_product_content(line):
            seen_product = True
        if seen_product and _line_is_noise_section_header(line):
            break
        kept.append(line)
    return "\n".join(kept).rstrip()


def _dedupe_consecutive_lines(lines: list[str]) -> list[str]:
    deduped: list[str] = []
    previous: str | None = None
    seen_blocks: set[str] = set()
    for line in lines:
        if line == previous:
            continue
        block_key = re.sub(r"\s+", " ", line.lower())
        if block_key in seen_blocks and _line_has_product_marker(line):
            continue
        if block_key in seen_blocks and re.search(r"\bpart\s*#", line, re.IGNORECASE):
            continue
        deduped.append(line)
        previous = line
        seen_blocks.add(block_key)
    return deduped


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

    kept = _dedupe_consecutive_lines(kept)
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
    before_chars: int = 800,
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
