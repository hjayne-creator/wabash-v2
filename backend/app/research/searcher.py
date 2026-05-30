from __future__ import annotations

import logging
from dataclasses import dataclass

from app.adapters.firecrawl_client import FirecrawlClient, FirecrawlError, is_pdf_url
from app.adapters.serpapi_client import SerpapiClient
from app.config import get_settings
from app.domain_blocklist import merged_blocked_keys
from app.models.schemas import CandidateRecord, MatchCriterion, ScoredSource
from app.observability.run_usage import log_external_cost
from app.research.matcher import (
    compute_product_match_score,
    compute_product_page_score,
    exact_mpn_in_text,
    manufacturer_matches,
    normalize_product_inputs,
    source_supports_exact_manufacturer_match,
    source_supports_product_match,
)
from app.research.ranker import (
    SCRAPE_SKIP_TIERS,
    RankedCandidate,
    SOURCE_TIER_AUTHORIZED_DISTRIBUTOR,
    SOURCE_TIER_DATASHEET,
    SOURCE_TIER_MANUFACTURER_PAGE,
    rank_results,
)
from app.research.markdown_cleaner import process_scraped_markdown, product_focused_excerpt
from app.research.scrape_limits import (
    pdf_host_is_trusted,
    remote_pdf_byte_size,
)
from app.research.scorer import score_source_match
from sqlmodel import Session, select

from app.models.db import AuthorizedDistributor, BlockedDomain, get_engine

logger = logging.getLogger(__name__)
MATCH_FLOOR_TIERS = frozenset(
    {
        SOURCE_TIER_MANUFACTURER_PAGE,
        SOURCE_TIER_DATASHEET,
        SOURCE_TIER_AUTHORIZED_DISTRIBUTOR,
    }
)
NON_PRODUCT_PAGE_SCORE_CAP = 55
WEAK_SCRAPE_MIN_CHARS = 1_200


def _apply_match_floor(
    *,
    overall_pct: int | None,
    tier: str,
    rule_mpn_found: bool,
    rule_manufacturer_match: bool,
    is_product_page: bool | None,
) -> int | None:
    """Keep exact trusted matches from scoring too low on noisy scraped text."""
    if overall_pct is None:
        return None
    if is_product_page is False:
        return overall_pct
    if tier in MATCH_FLOOR_TIERS and rule_mpn_found and rule_manufacturer_match:
        return max(overall_pct, 80)
    return overall_pct


def _clamp_non_product_page_score(*, overall_pct: int | None, is_product_page: bool | None) -> int | None:
    if overall_pct is None:
        return None
    if is_product_page is False:
        return min(overall_pct, NON_PRODUCT_PAGE_SCORE_CAP)
    return overall_pct


def _scrape_needs_retry(*, markdown: str, manufacturer: str, mpn: str) -> bool:
    if not markdown.strip():
        return True
    if len(markdown) < WEAK_SCRAPE_MIN_CHARS:
        return True
    has_mpn = exact_mpn_in_text(markdown, mpn)
    has_mfg = manufacturer_matches(markdown, manufacturer)
    return not (has_mpn and has_mfg)


@dataclass
class MatchBundle:
    manufacturer: str
    mpn: str
    candidates: list[CandidateRecord]
    sources: list[ScoredSource]
    status: str
    message: str | None


@dataclass
class PrefilterEvaluation:
    candidate: RankedCandidate
    markdown: str
    scrape_ok: bool
    scrape_error: str | None
    is_product_page: bool | None
    product_page_score: int | None
    product_match_score: int | None
    product_page_signals: list[str]


def _load_domain_sets() -> tuple[frozenset[str], frozenset[str]]:
    with Session(get_engine()) as session:
        blocked = [r.domain for r in session.exec(select(BlockedDomain)).all()]
        authorized = [r.domain for r in session.exec(select(AuthorizedDistributor)).all()]
    return merged_blocked_keys(blocked, ()), frozenset(authorized)


async def _run_serp_queries(
    serp: SerpapiClient,
    queries: list[str],
    *,
    blocked_keys: frozenset[str],
) -> list:
    settings = get_settings()
    organic = []
    seen_urls: set[str] = set()
    for query in queries:
        results = await serp.search(query, num=10, blocked_hosts=tuple(sorted(blocked_keys)))
        log_external_cost(service="serpapi", phase="search", units=1, unit_cost_usd=settings.serpapi_cost_usd)
        for result in results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                organic.append(result)
    return organic


async def _scrape_candidate(
    candidate: RankedCandidate,
    *,
    firecrawl: FirecrawlClient,
    manufacturer: str,
    mpn: str,
    authorized_domains: frozenset[str],
) -> tuple[str, bool, str | None]:
    settings = get_settings()
    url = candidate.result.url

    if candidate.tier in SCRAPE_SKIP_TIERS:
        return "", False, "Skipped low-confidence or listing-page tier."

    trusted_pdf_tiers = {
        SOURCE_TIER_MANUFACTURER_PAGE,
        SOURCE_TIER_DATASHEET,
        SOURCE_TIER_AUTHORIZED_DISTRIBUTOR,
    }
    if is_pdf_url(url) and candidate.tier not in trusted_pdf_tiers:
        return "", False, "Skipped low-confidence PDF source."

    if is_pdf_url(url) and not pdf_host_is_trusted(
        url,
        manufacturer=manufacturer,
        authorized_domains=authorized_domains,
    ):
        return "", False, "Skipped PDF on untrusted host."

    if is_pdf_url(url) and settings.research_pdf_max_bytes > 0:
        byte_size = await remote_pdf_byte_size(url)
        if byte_size is not None and byte_size > settings.research_pdf_max_bytes:
            mb = byte_size / (1024 * 1024)
            cap_mb = settings.research_pdf_max_bytes / (1024 * 1024)
            return (
                "",
                False,
                f"Skipped oversized PDF ({mb:.1f} MB; limit {cap_mb:.1f} MB).",
            )

    try:
        response = await firecrawl.scrape(url)
        log_external_cost(
            service="firecrawl", phase="scrape", units=1, unit_cost_usd=settings.firecrawl_cost_usd
        )
        markdown = process_scraped_markdown(FirecrawlClient.extract_markdown(response), url, settings)
        if not markdown:
            return "", False, "Firecrawl returned empty content."
        if not is_pdf_url(url) and _scrape_needs_retry(markdown=markdown, manufacturer=manufacturer, mpn=mpn):
            try:
                retry_wait = max(settings.firecrawl_wait_for_ms or 0, 2_500)
                retry_response = await firecrawl.scrape(
                    url,
                    only_main_content=False,
                    wait_for_ms=retry_wait,
                )
                log_external_cost(
                    service="firecrawl",
                    phase="scrape",
                    units=1,
                    unit_cost_usd=settings.firecrawl_cost_usd,
                )
                retry_markdown = process_scraped_markdown(
                    FirecrawlClient.extract_markdown(retry_response),
                    url,
                    settings,
                )
                if retry_markdown:
                    old_evidence = int(exact_mpn_in_text(markdown, mpn)) + int(
                        manufacturer_matches(markdown, manufacturer)
                    )
                    new_evidence = int(exact_mpn_in_text(retry_markdown, mpn)) + int(
                        manufacturer_matches(retry_markdown, manufacturer)
                    )
                    if new_evidence > old_evidence or (
                        new_evidence == old_evidence and len(retry_markdown) > len(markdown)
                    ):
                        markdown = retry_markdown
            except FirecrawlError as retry_exc:
                logger.info("Firecrawl broad retry failed for %s: %s", url, retry_exc)
        return markdown, True, None
    except FirecrawlError as exc:
        logger.warning("Firecrawl failed for %s: %s", url, exc)
        return "", False, str(exc)


async def _prefilter_candidates(
    ranked: list[RankedCandidate],
    *,
    firecrawl: FirecrawlClient,
    manufacturer: str,
    mpn: str,
    authorized_domains: frozenset[str],
) -> list[PrefilterEvaluation]:
    settings = get_settings()
    evaluations: list[PrefilterEvaluation] = []
    for candidate in ranked[: settings.prefilter_crawl_top_n]:
        markdown, scrape_ok, scrape_error = await _scrape_candidate(
            candidate,
            firecrawl=firecrawl,
            manufacturer=manufacturer,
            mpn=mpn,
            authorized_domains=authorized_domains,
        )
        if scrape_ok and markdown:
            product_page_score, is_product_page, product_page_signals = compute_product_page_score(
                markdown,
                manufacturer=manufacturer,
                mpn=mpn,
            )
            product_match_score = compute_product_match_score(
                markdown,
                manufacturer=manufacturer,
                mpn=mpn,
                tier=candidate.tier,
            )
        else:
            product_page_score = None
            is_product_page = None
            product_match_score = None
            product_page_signals = []

        evaluations.append(
            PrefilterEvaluation(
                candidate=candidate,
                markdown=markdown,
                scrape_ok=scrape_ok,
                scrape_error=scrape_error,
                is_product_page=is_product_page,
                product_page_score=product_page_score,
                product_match_score=product_match_score,
                product_page_signals=product_page_signals,
            )
        )
    return evaluations


async def run_product_match(
    *,
    manufacturer_name: str,
    manufacturer_product_number: str,
) -> MatchBundle:
    settings = get_settings()
    manufacturer, mpn = normalize_product_inputs(manufacturer_name, manufacturer_product_number)
    serp = SerpapiClient()
    firecrawl = FirecrawlClient()
    blocked_keys, authorized_keys = _load_domain_sets()

    base_queries = [
        f'"{mpn}" {manufacturer}',
        f"{manufacturer} {mpn} specifications",
        f"{manufacturer} {mpn} datasheet",
        f"{manufacturer} {mpn} product",
    ]
    organic = await _run_serp_queries(serp, base_queries, blocked_keys=blocked_keys)
    ranked = rank_results(
        organic,
        manufacturer=manufacturer,
        authorized_domains=authorized_keys,
        limit=max(settings.research_candidate_limit, settings.prefilter_crawl_top_n),
    )
    if not ranked:
        return MatchBundle(
            manufacturer=manufacturer,
            mpn=mpn,
            candidates=[],
            sources=[],
            status="no_candidates",
            message="No product pages found. Try alternate spelling or a shorter manufacturer name.",
        )

    prefilter_evaluations = await _prefilter_candidates(
        ranked,
        firecrawl=firecrawl,
        manufacturer=manufacturer,
        mpn=mpn,
        authorized_domains=authorized_keys,
    )
    passed_prefilter = [
        ev
        for ev in prefilter_evaluations
        if ev.scrape_ok
        and (ev.product_page_score or 0) >= settings.prefilter_product_page_min_score
        and (ev.product_match_score or 0) >= settings.prefilter_product_match_min_score
    ]
    selected = passed_prefilter
    if not selected:
        fallback_sorted = sorted(
            prefilter_evaluations,
            key=lambda ev: (
                not ev.scrape_ok,
                -(ev.product_match_score or 0),
                -(ev.product_page_score or 0),
                -ev.candidate.score,
            ),
        )
        selected = fallback_sorted[: settings.prefilter_fallback_keep_top_n]

    selected = selected[: settings.research_candidate_limit]
    selected_by_url = {ev.candidate.result.url: ev for ev in selected}
    candidates = [
        CandidateRecord(
            rank=idx + 1,
            url=ev.candidate.result.url,
            title=ev.candidate.result.title,
            snippet=ev.candidate.result.snippet,
            domain=ev.candidate.result.domain,
            tier=ev.candidate.tier,
            serp_score=ev.candidate.score,
        )
        for idx, ev in enumerate(selected)
    ]

    sources: list[ScoredSource] = []
    scrape_failures = 0

    for candidate in [ev.candidate for ev in selected]:
        pre = selected_by_url[candidate.result.url]
        markdown = pre.markdown
        scrape_ok = pre.scrape_ok
        scrape_error = pre.scrape_error
        if not scrape_ok:
            scrape_failures += 1

        rule_mpn = False
        rule_mfg = False
        if scrape_ok and markdown:
            rule_mpn = exact_mpn_in_text(markdown, mpn) or source_supports_product_match(
                markdown, manufacturer=manufacturer, mpn=mpn, tier=candidate.tier
            )
            rule_mfg = manufacturer_matches(markdown, manufacturer) or source_supports_exact_manufacturer_match(
                markdown, manufacturer=manufacturer, mpn=mpn, tier=candidate.tier
            )

        overall_pct: int | None = None
        criteria: list[MatchCriterion] = []
        score_error: str | None = None

        if scrape_ok and markdown:
            overall_pct, raw_criteria, score_error = await score_source_match(
                manufacturer=manufacturer,
                mpn=mpn,
                url=candidate.result.url,
                serp_title=candidate.result.title,
                serp_snippet=candidate.result.snippet,
                tier=candidate.tier,
                markdown=markdown,
                rule_mpn_found=rule_mpn,
                rule_manufacturer_match=rule_mfg,
            )
            overall_pct = _apply_match_floor(
                overall_pct=overall_pct,
                tier=candidate.tier,
                rule_mpn_found=rule_mpn,
                rule_manufacturer_match=rule_mfg,
                is_product_page=pre.is_product_page,
            )
            overall_pct = _clamp_non_product_page_score(
                overall_pct=overall_pct,
                is_product_page=pre.is_product_page,
            )
            criteria = [
                MatchCriterion(name=c.name, score_pct=c.score_pct, rationale=c.rationale)
                for c in raw_criteria
            ]

        excerpt_limit = 2_000
        sources.append(
            ScoredSource(
                url=candidate.result.url,
                title=candidate.result.title,
                snippet=candidate.result.snippet,
                domain=candidate.result.domain,
                tier=candidate.tier,
                scrape_ok=scrape_ok,
                scrape_error=scrape_error,
                is_product_page=pre.is_product_page,
                product_page_score=pre.product_page_score,
                product_match_score=pre.product_match_score,
                product_page_signals=pre.product_page_signals,
                markdown_excerpt=(
                    product_focused_excerpt(
                        markdown,
                        mpn=mpn,
                        manufacturer=manufacturer,
                        max_chars=excerpt_limit,
                    )
                    if markdown
                    else ""
                ),
                rule_mpn_found=rule_mpn,
                rule_manufacturer_match=rule_mfg,
                overall_similarity_pct=overall_pct,
                criteria=criteria,
                score_error=score_error,
            )
        )

    sources.sort(key=lambda s: (s.overall_similarity_pct is None, -(s.overall_similarity_pct or 0)))

    if scrape_failures == len(selected):
        status = "partial"
        message = "Candidates were found but were not scraped due to low match score."
    elif scrape_failures > 0:
        status = "partial"
        message = "Some candidates could not be scraped or scored."
    else:
        status = "complete"
        message = None

    return MatchBundle(
        manufacturer=manufacturer,
        mpn=mpn,
        candidates=candidates,
        sources=sources,
        status=status,
        message=message,
    )
