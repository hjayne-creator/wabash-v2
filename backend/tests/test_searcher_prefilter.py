import asyncio

from app.adapters.serpapi_client import OrganicResult
from app.research import searcher


def test_apply_match_floor_skips_non_product_pages():
    floored = searcher._apply_match_floor(
        overall_pct=50,
        tier=searcher.SOURCE_TIER_MANUFACTURER_PAGE,
        rule_mpn_found=True,
        rule_manufacturer_match=True,
        is_product_page=False,
    )
    assert floored == 50


def test_clamp_non_product_page_score_caps_high_scores():
    clamped = searcher._clamp_non_product_page_score(overall_pct=92, is_product_page=False)
    assert clamped == searcher.NON_PRODUCT_PAGE_SCORE_CAP


def test_scrape_needs_retry_for_thin_or_missing_evidence():
    thin = "Part page"
    assert searcher._scrape_needs_retry(markdown=thin, manufacturer="TRAMEC SLOAN", mpn="451032Y")

    rich_but_missing_target = "Technical specifications and dimensions for tubing products."
    assert searcher._scrape_needs_retry(
        markdown=rich_but_missing_target,
        manufacturer="TRAMEC SLOAN",
        mpn="451032Y",
    )

    rich_with_target = (
        "TRAMEC SLOAN 451032Y part number. " + ("specification details " * 120)
    )
    assert (
        searcher._scrape_needs_retry(
            markdown=rich_with_target,
            manufacturer="TRAMEC SLOAN",
            mpn="451032Y",
        )
        is False
    )


def _set_prefilter_settings(*, top_n: int, page_min: int, match_min: int, fallback_n: int) -> dict[str, int]:
    settings = searcher.get_settings()
    previous = {
        "prefilter_crawl_top_n": settings.prefilter_crawl_top_n,
        "prefilter_product_page_min_score": settings.prefilter_product_page_min_score,
        "prefilter_product_match_min_score": settings.prefilter_product_match_min_score,
        "prefilter_fallback_keep_top_n": settings.prefilter_fallback_keep_top_n,
        "research_candidate_limit": settings.research_candidate_limit,
    }
    settings.prefilter_crawl_top_n = top_n
    settings.prefilter_product_page_min_score = page_min
    settings.prefilter_product_match_min_score = match_min
    settings.prefilter_fallback_keep_top_n = fallback_n
    settings.research_candidate_limit = top_n
    return previous


def _restore_prefilter_settings(previous: dict[str, int]) -> None:
    settings = searcher.get_settings()
    for key, value in previous.items():
        setattr(settings, key, value)


def test_run_product_match_prefilter_scrapes_top_five(monkeypatch):
    previous = _set_prefilter_settings(top_n=5, page_min=35, match_min=60, fallback_n=2)
    scraped_urls: list[str] = []

    async def fake_run_serp_queries(_serp, _queries, *, blocked_keys):
        del blocked_keys
        return [
            OrganicResult(
                position=i + 1,
                title=f"ACME X-100 Result {i + 1}",
                url=f"https://example{i + 1}.com/product/x-100",
                snippet="technical specifications part number x-100",
                domain=f"example{i + 1}.com",
            )
            for i in range(7)
        ]

    async def fake_scrape_candidate(candidate, **kwargs):
        del kwargs
        scraped_urls.append(candidate.result.url)
        markdown = "ACME X-100 technical specifications part number X-100 weight dimensions"
        return markdown, True, None

    async def fake_score_source_match(**kwargs):
        del kwargs
        return 88, [], None

    monkeypatch.setattr(searcher, "_load_domain_sets", lambda: (frozenset(), frozenset()))
    monkeypatch.setattr(searcher, "_run_serp_queries", fake_run_serp_queries)
    monkeypatch.setattr(searcher, "_scrape_candidate", fake_scrape_candidate)
    monkeypatch.setattr(searcher, "score_source_match", fake_score_source_match)

    try:
        bundle = asyncio.run(
            searcher.run_product_match(
                manufacturer_name="ACME",
                manufacturer_product_number="X-100",
            )
        )
    finally:
        _restore_prefilter_settings(previous)

    assert len(scraped_urls) == 5
    assert len(bundle.candidates) == 5
    assert all(source.is_product_page is True for source in bundle.sources)


def test_run_product_match_prefilter_fallback_keeps_best_two(monkeypatch):
    previous = _set_prefilter_settings(top_n=5, page_min=80, match_min=90, fallback_n=2)

    async def fake_run_serp_queries(_serp, _queries, *, blocked_keys):
        del blocked_keys
        return [
            OrganicResult(
                position=i + 1,
                title=f"Result {i + 1}",
                url=f"https://example{i + 1}.com/product/x-100",
                snippet="",
                domain=f"example{i + 1}.com",
            )
            for i in range(3)
        ]

    async def fake_prefilter_candidates(ranked, **kwargs):
        del kwargs
        scores = [42, 35, 20]
        page_scores = [45, 40, 30]
        out = []
        for idx, candidate in enumerate(ranked):
            out.append(
                searcher.PrefilterEvaluation(
                    candidate=candidate,
                    markdown="ACME X-100 page",
                    scrape_ok=True,
                    scrape_error=None,
                    is_product_page=False,
                    product_page_score=page_scores[idx],
                    product_match_score=scores[idx],
                    product_page_signals=["part_number"],
                )
            )
        return out

    async def fake_score_source_match(**kwargs):
        del kwargs
        return 70, [], None

    monkeypatch.setattr(searcher, "_load_domain_sets", lambda: (frozenset(), frozenset()))
    monkeypatch.setattr(searcher, "_run_serp_queries", fake_run_serp_queries)
    monkeypatch.setattr(searcher, "_prefilter_candidates", fake_prefilter_candidates)
    monkeypatch.setattr(searcher, "score_source_match", fake_score_source_match)

    try:
        bundle = asyncio.run(
            searcher.run_product_match(
                manufacturer_name="ACME",
                manufacturer_product_number="X-100",
            )
        )
    finally:
        _restore_prefilter_settings(previous)

    assert len(bundle.candidates) == 2
    assert bundle.candidates[0].url == "https://example1.com/product/x-100"
    assert bundle.candidates[1].url == "https://example2.com/product/x-100"
