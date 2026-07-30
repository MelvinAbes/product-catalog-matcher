from decimal import Decimal
from uuid import uuid4

import pytest

from product_catalog_matcher.domain import MatchDecision
from product_catalog_matcher.matching.policy import classify_best_candidate
from product_catalog_matcher.matching.scoring import ProductScore, score_product_pair
from product_catalog_matcher.persistence.models import CanonicalProduct, SupplierProduct


class FixedSemanticScorer:
    def __init__(self, score: float) -> None:
        self.score = score

    def similarity(self, left: str, right: str) -> float:
        assert left
        assert right
        return self.score


def source_product(**overrides: object) -> SupplierProduct:
    values = {
        "id": uuid4(),
        "supplier_id": uuid4(),
        "import_batch_id": uuid4(),
        "source_record_id": "C-1",
        "source_row_number": 2,
        "record_status": "valid",
        "raw_data": {},
        "name": "Kite Steel Travel Mug 500 ml",
        "normalized_name": "kite steel travel mug 500 ml",
        "brand": "Kite Works",
        "normalized_brand": "kite works",
        "category": "Home > Drinkware",
        "normalized_category": "home > drinkware",
        "gtin": "4006381333931",
        "normalized_gtin": "04006381333931",
        "sku": "C-1",
        "manufacturer_part_number": "KW-TM-500",
        "normalized_mpn": "kwtm500",
        "description": None,
        "normalized_description": None,
        "pack_quantity": Decimal("1"),
        "unit_value": Decimal("500"),
        "unit_code": "ml",
        "fingerprint": "a" * 64,
    }
    values.update(overrides)
    return SupplierProduct(**values)


def canonical_product(**overrides: object) -> CanonicalProduct:
    values = {
        "id": uuid4(),
        "name": "Kite Works Steel Travel Mug 500ml",
        "normalized_name": "kite works steel travel mug 500ml",
        "brand": "Kite Works",
        "normalized_brand": "kite works",
        "category": "Home > Drinkware",
        "normalized_category": "home > drinkware",
        "gtin": "04006381333931",
        "manufacturer_part_number": "KW-TM-500",
        "normalized_mpn": "kwtm500",
        "pack_quantity": Decimal("1"),
        "unit_value": Decimal("500"),
        "unit_code": "ml",
    }
    values.update(overrides)
    return CanonicalProduct(**values)


def test_exact_attributes_create_an_explainable_high_score() -> None:
    result = score_product_pair(source_product(), canonical_product())

    assert result.score > 0.9
    assert {factor.name for factor in result.factors} == {
        "brand",
        "category",
        "gtin",
        "mpn",
        "name",
        "quantity",
        "token",
    }
    assert sum(factor.contribution for factor in result.factors) == pytest.approx(result.score)
    assert sum(factor.weight for factor in result.factors) == pytest.approx(1)


def test_conflicting_identifier_penalizes_an_otherwise_similar_product() -> None:
    exact = score_product_pair(source_product(), canonical_product())
    conflict = score_product_pair(
        source_product(),
        canonical_product(gtin="00036000291452"),
    )

    assert exact.score - conflict.score > 0.3
    gtin_factor = next(factor for factor in conflict.factors if factor.name == "gtin")
    assert gtin_factor.raw_score == 0
    assert gtin_factor.evidence["exact"] is False


def test_semantic_score_is_optional_and_visible() -> None:
    result = score_product_pair(
        source_product(),
        canonical_product(),
        semantic_scorer=FixedSemanticScorer(0.75),
    )

    assert result.semantic_used is True
    semantic = next(factor for factor in result.factors if factor.name == "semantic")
    assert semantic.raw_score == 0.75


def test_close_runner_up_routes_high_score_to_review() -> None:
    best = ProductScore(
        canonical_product=canonical_product(),
        score=0.94,
        factors=(),
        semantic_used=False,
    )
    close_second = ProductScore(
        canonical_product=canonical_product(),
        score=0.91,
        factors=(),
        semantic_used=False,
    )

    result = classify_best_candidate(
        [best, close_second],
        auto_match_threshold=0.88,
        review_threshold=0.65,
        minimum_winning_margin=0.08,
    )

    assert result.decision is MatchDecision.REVIEW
    assert result.winning_margin == pytest.approx(0.03)


def test_empty_candidate_list_is_a_no_match() -> None:
    result = classify_best_candidate(
        [],
        auto_match_threshold=0.88,
        review_threshold=0.65,
        minimum_winning_margin=0.08,
    )

    assert result.decision is MatchDecision.NO_MATCH
    assert result.winning_margin is None
