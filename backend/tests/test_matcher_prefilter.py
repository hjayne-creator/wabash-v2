from app.research.matcher import (
    compute_product_match_score,
    compute_product_page_score,
    exact_mpn_in_body,
    exact_mpn_in_text,
)
from app.research.ranker import SOURCE_TIER_MANUFACTURER_PAGE


def test_compute_product_page_score_detects_product_signals():
    text = """
    ACME Valve X100
    Technical Specifications
    Part Number: X100
    Part Type: Solenoid Valve
    Weight: 1.2 kg
    Dimensions: 120mm x 40mm
    Download PDF datasheet
    """
    score, is_product_page, signals = compute_product_page_score(text)
    assert is_product_page is True
    assert score >= 60
    assert "technical_specifications" in signals
    assert "part_number" in signals


def test_compute_product_match_score_rewards_exact_evidence():
    text = """
    Product page
    Manufacturer: ACME Industrial
    Part Number: X-100
    ACME Industrial X-100 technical specifications
    """
    score = compute_product_match_score(
        text,
        manufacturer="ACME Industrial",
        mpn="X-100",
        tier=SOURCE_TIER_MANUFACTURER_PAGE,
    )
    assert score >= 90


def test_compute_product_page_score_boosts_when_target_mpn_and_mfg_present():
    text = """
    PEWAG H4247SC
    Manufacturer: PEWAG
    In stock. SKU 3942092.
    """
    score, is_product_page, signals = compute_product_page_score(
        text,
        manufacturer="PEWAG",
        mpn="H4247SC",
    )
    assert is_product_page is True
    assert score >= 35
    assert "target_product_evidence" in signals


def test_exact_mpn_in_text_rejects_nav_link_slug_only():
    nav_only = "[PEWAG chains h4247sc](https://www.finditparts.com/products/3942092/pewag-chains-h4247sc)"

    assert not exact_mpn_in_text(nav_only, "H4247SC")
    assert not exact_mpn_in_body(nav_only, "H4247SC")


def test_exact_mpn_in_text_accepts_part_number_line():
    body = "### Part Number\nH4247SC"

    assert exact_mpn_in_body(body, "H4247SC")
    assert exact_mpn_in_text(body, "H4247SC")


def test_exact_mpn_in_text_accepts_mpn_outside_urls_in_unstructured_text():
    dense = "Specification sheet for PEWAG model H4247SC dimensions and weight"

    assert exact_mpn_in_text(dense, "H4247SC")
