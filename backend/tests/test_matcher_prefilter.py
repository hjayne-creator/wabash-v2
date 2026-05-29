from app.research.matcher import compute_product_match_score, compute_product_page_score
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
