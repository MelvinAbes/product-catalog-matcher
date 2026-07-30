from sqlalchemy import CheckConstraint

from product_catalog_matcher.persistence.base import Base
from product_catalog_matcher.persistence.models import ImportRole, MatchDecision, ReviewAction


def test_schema_contains_expected_domain_tables() -> None:
    assert set(Base.metadata.tables) == {
        "canonical_products",
        "catalog_links",
        "import_batches",
        "import_issues",
        "match_proposals",
        "review_events",
        "score_factors",
        "supplier_products",
        "suppliers",
    }


def test_match_proposal_scores_are_constrained() -> None:
    table = Base.metadata.tables["match_proposals"]
    constraints = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_match_proposals_score_range" in constraints
    assert "ck_match_proposals_margin_range" in constraints


def test_workflow_enums_use_stable_external_values() -> None:
    assert ImportRole.REFERENCE.value == "reference"
    assert MatchDecision.AUTO_MATCH.value == "auto_match"
    assert ReviewAction.REASSIGNED.value == "reassigned"
