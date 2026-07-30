from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from product_catalog_matcher.catalog.review import (
    ReviewConflictError,
    ReviewDecisionCommand,
    decide_review,
)
from product_catalog_matcher.domain import MatchDecision, RecordStatus, ReviewAction
from product_catalog_matcher.persistence import models


@pytest.fixture
def review_session() -> tuple[Session, models.MatchProposal, models.CanonicalProduct]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.Base.metadata.create_all(engine)
    session = Session(engine, expire_on_commit=False)
    supplier = models.Supplier(code="candidate", name="Candidate Supplier")
    session.add(supplier)
    session.flush()
    batch = models.ImportBatch(
        supplier_id=supplier.id,
        role="candidate",
        status="completed",
        file_name="candidate.csv",
        content_sha256="d" * 64,
    )
    session.add(batch)
    session.flush()
    source = models.SupplierProduct(
        supplier_id=supplier.id,
        import_batch_id=batch.id,
        source_record_id="C-1",
        source_row_number=2,
        record_status=RecordStatus.VALID,
        raw_data={},
        name="Travel Mug",
        normalized_name="travel mug",
        brand="Kite",
        normalized_brand="kite",
        category=None,
        normalized_category=None,
        gtin=None,
        normalized_gtin=None,
        sku="C-1",
        manufacturer_part_number=None,
        normalized_mpn=None,
        description=None,
        normalized_description=None,
        pack_quantity=None,
        unit_value=None,
        unit_code=None,
        fingerprint="e" * 64,
        match_decision=MatchDecision.REVIEW,
        match_policy_version="deterministic-v1",
    )
    target = models.CanonicalProduct(
        name="Travel Mug",
        normalized_name="travel mug",
        brand="Kite",
        normalized_brand="kite",
        category=None,
        normalized_category=None,
        gtin=None,
        manufacturer_part_number=None,
        normalized_mpn=None,
        pack_quantity=None,
        unit_value=None,
        unit_code=None,
    )
    session.add_all([source, target])
    session.flush()
    proposal = models.MatchProposal(
        supplier_product_id=source.id,
        canonical_product_id=target.id,
        rank=1,
        score=Decimal("0.810000"),
        runner_up_margin=Decimal("0.040000"),
        decision=MatchDecision.REVIEW,
        policy_version="deterministic-v1",
        semantic_used=False,
    )
    session.add(proposal)
    session.commit()
    yield session, proposal, target
    session.close()


def test_accepting_review_creates_append_only_event_and_manual_link(
    review_session: tuple[Session, models.MatchProposal, models.CanonicalProduct],
) -> None:
    session, proposal, target = review_session

    result = decide_review(
        session,
        ReviewDecisionCommand(
            proposal_id=proposal.id,
            action=ReviewAction.ACCEPTED,
            reviewer="catalog-reviewer",
            rationale="Brand, model and pack size agree.",
        ),
    )

    assert result.action is ReviewAction.ACCEPTED
    assert result.canonical_product_id == target.id
    assert session.scalar(select(func.count(models.ReviewEvent.id))) == 1
    link = session.scalar(select(models.CatalogLink))
    assert link is not None
    assert link.method == "manual"
    assert link.confidence == Decimal("1.000000")


def test_review_cannot_be_decided_twice(
    review_session: tuple[Session, models.MatchProposal, models.CanonicalProduct],
) -> None:
    session, proposal, _target = review_session
    decide_review(
        session,
        ReviewDecisionCommand(
            proposal_id=proposal.id,
            action=ReviewAction.REJECTED,
            reviewer="catalog-reviewer",
            rationale="Different product dimensions.",
        ),
    )

    with pytest.raises(ReviewConflictError, match="already has"):
        decide_review(
            session,
            ReviewDecisionCommand(
                proposal_id=proposal.id,
                action=ReviewAction.REJECTED,
                reviewer="catalog-reviewer",
                rationale="Repeated decision should fail.",
            ),
        )


def test_reassignment_requires_an_existing_target(
    review_session: tuple[Session, models.MatchProposal, models.CanonicalProduct],
) -> None:
    session, proposal, _target = review_session

    with pytest.raises(LookupError, match="was not found"):
        decide_review(
            session,
            ReviewDecisionCommand(
                proposal_id=proposal.id,
                action=ReviewAction.REASSIGNED,
                reviewer="catalog-reviewer",
                rationale="A different canonical item is correct.",
                canonical_product_id=uuid4(),
            ),
        )
