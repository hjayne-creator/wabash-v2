from pathlib import Path

from app.research.matcher import exact_mpn_in_body
from app.research.markdown_cleaner import (
    clean_pdp_markdown,
    normalized_mpn_in_body,
    product_focused_excerpt,
)

_EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"


def _scrape_from_example(name: str) -> str:
    text = (_EXAMPLES_DIR / name).read_text()
    marker = "Scraped PDP content (markdown excerpt):\n"
    start = text.index(marker) + len(marker)
    return text[start:].strip()


def test_clean_pdp_markdown_strips_related_parts_and_images():
    raw = _scrape_from_example("example1.md")

    cleaned = clean_pdp_markdown(raw)

    assert "Related Parts" not in cleaned
    assert "Add To Cart" not in cleaned
    assert "cdn.partsconnect" not in cleaned
    assert "H2247SC:PWG" in cleaned
    assert "Manufacturer Part Number" in cleaned
    assert "Specifications" in cleaned


def test_clean_pdp_markdown_drops_category_navigation():
    raw = _scrape_from_example("example2.md")

    cleaned = clean_pdp_markdown(raw)

    assert "/categories/" not in cleaned
    assert "Shop by Manufacturer" not in cleaned
    assert "FinditParts Logo" not in cleaned


def test_product_focused_excerpt_prefers_product_block_over_prefix():
    raw = _scrape_from_example("example1.md")
    cleaned = clean_pdp_markdown(raw)

    excerpt = product_focused_excerpt(
        cleaned,
        mpn="H4247SC",
        manufacturer="PEWAG",
        max_chars=2_000,
    )

    assert "Manufacturer Part Number" in excerpt
    assert "Related Parts" not in excerpt
    assert excerpt.index("Manufacturer Part Number") < 400


def test_product_focused_excerpt_keeps_fleetpride_identity():
    raw = _scrape_from_example("example4.md")
    cleaned = clean_pdp_markdown(raw)

    excerpt = product_focused_excerpt(
        cleaned,
        mpn="H4247SC",
        manufacturer="PEWAG",
        max_chars=1_500,
    )

    assert "H4247SC" in excerpt
    assert "PEWAG" in excerpt
    assert "Related Searches" not in excerpt
    assert "Complete The Job" not in excerpt


def test_normalized_mpn_in_body_ignores_url_slug_only_hits():
    nav_only = "[PEWAG chains h4247sc](https://www.finditparts.com/products/3942092/pewag-chains-h4247sc)"
    body_hit = "### Part Number\nH4247SC"

    assert not normalized_mpn_in_body(nav_only, "H4247SC")
    assert not exact_mpn_in_body(nav_only, "H4247SC")
    assert normalized_mpn_in_body(body_hit, "H4247SC")
