from app.adapters.serpapi_client import OrganicResult
from app.research.ranker import (
    SOURCE_TIER_ECOMMERCE,
    SOURCE_TIER_LISTING_PAGE,
    SOURCE_TIER_OTHER,
    classify_result,
    looks_like_listing_page,
    rank_results,
)


def test_listing_page_filtered_from_ranked_results():
    organic = [
        OrganicResult(
            position=1,
            title="All Products",
            url="https://example.com/products",
            snippet="Browse our catalog",
            domain="example.com",
        ),
        OrganicResult(
            position=2,
            title="ML5035 Spec Sheet",
            url="https://whitingdoor.com/products/ml5035",
            snippet="ML5035 door",
            domain="whitingdoor.com",
        ),
    ]
    ranked = rank_results(organic, manufacturer="WHITING DOOR", authorized_domains=frozenset(), limit=5)
    assert len(ranked) == 1
    assert ranked[0].result.url.endswith("ml5035")


def test_looks_like_listing_search_path():
    result = OrganicResult(
        position=1,
        title="Search results",
        url="https://shop.example.com/search?q=ml5035",
        snippet="",
        domain="shop.example.com",
    )
    assert looks_like_listing_page(result)
    tier, score = classify_result(result, manufacturer="ACME", authorized_domains=frozenset())
    assert tier == SOURCE_TIER_LISTING_PAGE
    assert score == 0.0


def test_distributor_product_path_classified_as_ecommerce_not_other():
    result = OrganicResult(
        position=1,
        title="PEWAG Chains H4247SC",
        url="https://www.finditparts.com/products/3942092/pewag-chains-h4247sc",
        snippet="PEWAG tire chains",
        domain="www.finditparts.com",
    )
    tier, score = classify_result(result, manufacturer="PEWAG", authorized_domains=frozenset())
    assert tier == SOURCE_TIER_ECOMMERCE
    assert score == 45.0


def test_title_only_manufacturer_without_product_path_stays_other():
    result = OrganicResult(
        position=1,
        title="PEWAG product overview",
        url="https://example.com/about/pewag",
        snippet="",
        domain="example.com",
    )
    tier, score = classify_result(result, manufacturer="PEWAG", authorized_domains=frozenset())
    assert tier == SOURCE_TIER_OTHER
    assert score == 35.0
