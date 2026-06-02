"""Deterministic mapping from LLM attribute keys to catalog attributes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from rapidfuzz import fuzz
from sqlmodel import Session, select

from app.models.db import ProductAttribute

MatchConfidence = Literal["exact", "alias", "fuzzy"]


@dataclass
class MappedAttributeValue:
    key: str
    label: str
    value: str
    confidence: MatchConfidence
    source_key: str


@dataclass
class AttributeMatchResult:
    mapped: dict[str, MappedAttributeValue]
    unmapped_from_llm: dict[str, str]
    missing: list[str]
    fill_pct: float
    attributes_filled: int
    attributes_total: int


def _normalize_key(key: str) -> str:
    cleaned = key.lower().strip()
    for ch in ("-", "_", "/", ".", ","):
        cleaned = cleaned.replace(ch, " ")
    return " ".join(cleaned.split())


def load_active_attributes(session: Session) -> list[ProductAttribute]:
    rows = session.exec(
        select(ProductAttribute)
        .where(ProductAttribute.active.is_(True))
        .order_by(ProductAttribute.sort_order, ProductAttribute.label)
    ).all()
    return list(rows)


def match_attributes(
    *,
    llm_attributes: dict[str, Any],
    catalog: list[ProductAttribute],
    fuzzy_threshold: int = 90,
) -> AttributeMatchResult:
    alias_map: dict[str, ProductAttribute] = {}
    fuzzy_candidates: list[tuple[str, ProductAttribute]] = []

    for attr in catalog:
        norm_label = _normalize_key(attr.label)
        alias_map[norm_label] = attr
        fuzzy_candidates.append((norm_label, attr))
        alias_map[_normalize_key(attr.key)] = attr
        fuzzy_candidates.append((_normalize_key(attr.key), attr))
        for alias in attr.aliases_list():
            norm_alias = _normalize_key(alias)
            alias_map[norm_alias] = attr
            fuzzy_candidates.append((norm_alias, attr))

    mapped: dict[str, MappedAttributeValue] = {}
    unmapped: dict[str, str] = {}

    for raw_key, raw_value in llm_attributes.items():
        if raw_value is None:
            continue
        value = str(raw_value).strip()
        if not value:
            continue
        norm_key = _normalize_key(str(raw_key))
        target: ProductAttribute | None = alias_map.get(norm_key)
        confidence: MatchConfidence | None = "exact" if target else None
        source_key = str(raw_key)

        if target is None:
            for candidate_norm, candidate_attr in fuzzy_candidates:
                score = max(
                    fuzz.ratio(norm_key, candidate_norm),
                    fuzz.partial_ratio(norm_key, candidate_norm),
                    fuzz.token_sort_ratio(norm_key, candidate_norm),
                )
                if score >= fuzzy_threshold:
                    target = candidate_attr
                    confidence = "fuzzy"
                    break

        if target is None:
            unmapped[str(raw_key)] = value
            continue

        if confidence is None:
            confidence = "alias"

        mapped[target.key] = MappedAttributeValue(
            key=target.key,
            label=target.label,
            value=value,
            confidence=confidence,
            source_key=source_key,
        )

    missing = [a.label for a in catalog if a.key not in mapped]
    total = len(catalog)
    filled = len(mapped)
    fill_pct = round((filled / total) * 100, 1) if total else 0.0

    return AttributeMatchResult(
        mapped=mapped,
        unmapped_from_llm=unmapped,
        missing=missing,
        fill_pct=fill_pct,
        attributes_filled=filled,
        attributes_total=total,
    )


def match_result_to_dict(result: AttributeMatchResult) -> dict[str, Any]:
    return {
        "mapped": {
            k: {
                "key": v.key,
                "label": v.label,
                "value": v.value,
                "confidence": v.confidence,
                "source_key": v.source_key,
            }
            for k, v in result.mapped.items()
        },
        "unmapped_from_llm": result.unmapped_from_llm,
        "missing": result.missing,
        "fill_pct": result.fill_pct,
        "attributes_filled": result.attributes_filled,
        "attributes_total": result.attributes_total,
    }
