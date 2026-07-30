from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from rapidfuzz import fuzz

from product_catalog_matcher.persistence.models import CanonicalProduct, SupplierProduct

POLICY_VERSION = "deterministic-v1"

FACTOR_WEIGHTS = {
    "gtin": 0.30,
    "name": 0.20,
    "token": 0.15,
    "brand": 0.10,
    "category": 0.05,
    "mpn": 0.10,
    "quantity": 0.05,
    "semantic": 0.05,
}


class SemanticScorer(Protocol):
    def similarity(self, left: str, right: str) -> float:
        """Return cosine-like similarity constrained to the inclusive 0..1 range."""


@dataclass(frozen=True)
class FactorScore:
    name: str
    raw_score: float
    weight: float
    contribution: float
    evidence: dict[str, object]


@dataclass(frozen=True)
class ProductScore:
    canonical_product: CanonicalProduct
    score: float
    factors: tuple[FactorScore, ...]
    semantic_used: bool


def score_product_pair(
    source: SupplierProduct,
    target: CanonicalProduct,
    *,
    semantic_scorer: SemanticScorer | None = None,
) -> ProductScore:
    factor_inputs: list[tuple[str, float, dict[str, object]]] = [
        (
            "name",
            fuzz.ratio(source.normalized_name, target.normalized_name) / 100,
            {"source": source.normalized_name, "target": target.normalized_name},
        ),
        (
            "token",
            fuzz.token_set_ratio(source.normalized_name, target.normalized_name) / 100,
            {"source": source.normalized_name, "target": target.normalized_name},
        ),
    ]
    _append_exact_factor(
        factor_inputs,
        "gtin",
        source.normalized_gtin,
        target.gtin,
    )
    _append_similarity_factor(
        factor_inputs,
        "brand",
        source.normalized_brand,
        target.normalized_brand,
    )
    _append_similarity_factor(
        factor_inputs,
        "category",
        source.normalized_category,
        target.normalized_category,
    )
    _append_exact_factor(
        factor_inputs,
        "mpn",
        source.normalized_mpn,
        target.normalized_mpn,
    )
    quantity_score = _quantity_similarity(source, target)
    if quantity_score is not None:
        factor_inputs.append(
            (
                "quantity",
                quantity_score,
                {
                    "source": _quantity_evidence(source),
                    "target": _quantity_evidence(target),
                },
            )
        )

    semantic_used = semantic_scorer is not None
    if semantic_scorer is not None:
        semantic = _clamp(
            semantic_scorer.similarity(
                _semantic_text(source),
                _semantic_text(target),
            )
        )
        factor_inputs.append(
            (
                "semantic",
                semantic,
                {"model_input": "normalized name, brand, and category"},
            )
        )

    active_weight = sum(FACTOR_WEIGHTS[name] for name, _, _ in factor_inputs)
    factors = tuple(
        FactorScore(
            name=name,
            raw_score=_clamp(raw_score),
            weight=FACTOR_WEIGHTS[name] / active_weight,
            contribution=_clamp(raw_score) * FACTOR_WEIGHTS[name] / active_weight,
            evidence=evidence,
        )
        for name, raw_score, evidence in factor_inputs
    )
    return ProductScore(
        canonical_product=target,
        score=sum(factor.contribution for factor in factors),
        factors=factors,
        semantic_used=semantic_used,
    )


def _append_exact_factor(
    factors: list[tuple[str, float, dict[str, object]]],
    name: str,
    source: str | None,
    target: str | None,
) -> None:
    if source is not None and target is not None:
        factors.append(
            (
                name,
                float(source == target),
                {"source": source, "target": target, "exact": source == target},
            )
        )


def _append_similarity_factor(
    factors: list[tuple[str, float, dict[str, object]]],
    name: str,
    source: str | None,
    target: str | None,
) -> None:
    if source is not None and target is not None:
        factors.append(
            (
                name,
                fuzz.ratio(source, target) / 100,
                {"source": source, "target": target},
            )
        )


def _quantity_similarity(
    source: SupplierProduct,
    target: CanonicalProduct,
) -> float | None:
    if (
        source.unit_value is None
        or target.unit_value is None
        or source.unit_code is None
        or target.unit_code is None
        or source.unit_code != target.unit_code
    ):
        return None
    source_total = source.unit_value * (source.pack_quantity or Decimal("1"))
    target_total = target.unit_value * (target.pack_quantity or Decimal("1"))
    maximum = max(source_total, target_total)
    if maximum == 0:
        return 1.0
    return float(Decimal("1") - abs(source_total - target_total) / maximum)


def _quantity_evidence(product: SupplierProduct | CanonicalProduct) -> dict[str, str | None]:
    return {
        "pack_quantity": str(product.pack_quantity) if product.pack_quantity else None,
        "unit_value": str(product.unit_value) if product.unit_value else None,
        "unit_code": product.unit_code,
    }


def _semantic_text(product: SupplierProduct | CanonicalProduct) -> str:
    return " | ".join(
        value
        for value in (
            product.normalized_name,
            product.normalized_brand,
            product.normalized_category,
        )
        if value
    )


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
