from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from product_catalog_matcher.config import Settings
from product_catalog_matcher.domain import (
    ImportRole,
    ImportStatus,
    MatchDecision,
    RecordStatus,
)
from product_catalog_matcher.matching.service import (
    BatchAlreadyMatchedError,
    match_import_batch,
)
from product_catalog_matcher.persistence import models


@pytest.fixture
def matching_session() -> tuple[Session, models.ImportBatch]:
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
        role=ImportRole.CANDIDATE,
        status=ImportStatus.COMPLETED,
        file_name="candidate.csv",
        content_sha256="b" * 64,
    )
    session.add(batch)
    session.flush()
    session.add(
        models.SupplierProduct(
            supplier_id=supplier.id,
            import_batch_id=batch.id,
            source_record_id="C-1",
            source_row_number=2,
            record_status=RecordStatus.VALID,
            raw_data={"id": "C-1"},
            name="Kite Steel Travel Mug 500 ml",
            normalized_name="kite steel travel mug 500 ml",
            brand="Kite Works",
            normalized_brand="kite works",
            category="Home > Drinkware",
            normalized_category="home > drinkware",
            gtin="4006381333931",
            normalized_gtin="04006381333931",
            sku="C-1",
            manufacturer_part_number="KW-TM-500",
            normalized_mpn="kwtm500",
            description=None,
            normalized_description=None,
            pack_quantity=Decimal("1"),
            unit_value=Decimal("500"),
            unit_code="ml",
            fingerprint="c" * 64,
        )
    )
    session.commit()
    yield session, batch
    session.close()


def test_batch_matching_persists_explanations_and_automatic_link(
    matching_session: tuple[Session, models.ImportBatch],
) -> None:
    session, batch = matching_session
    target = models.CanonicalProduct(
        name="Kite Works Steel Travel Mug 500ml",
        normalized_name="kite works steel travel mug 500ml",
        brand="Kite Works",
        normalized_brand="kite works",
        category="Home > Drinkware",
        normalized_category="home > drinkware",
        gtin="04006381333931",
        manufacturer_part_number="KW-TM-500",
        normalized_mpn="kwtm500",
        pack_quantity=Decimal("1"),
        unit_value=Decimal("500"),
        unit_code="ml",
    )
    session.add(target)
    session.commit()

    result = match_import_batch(
        session,
        settings=Settings(environment="test"),
        batch_id=batch.id,
        candidate_finder=lambda _session, _product, _floor, _limit: [target],
    )

    assert result.auto_matches == 1
    assert result.review_items == 0
    assert session.scalar(select(func.count(models.MatchProposal.id))) == 1
    assert session.scalar(select(func.count(models.ScoreFactor.id))) == 7
    assert session.scalar(select(func.count(models.CatalogLink.id))) == 1
    product = session.scalar(select(models.SupplierProduct))
    assert product is not None
    assert product.match_decision is MatchDecision.AUTO_MATCH


def test_batch_matching_is_idempotent_at_the_workflow_boundary(
    matching_session: tuple[Session, models.ImportBatch],
) -> None:
    session, batch = matching_session

    first = match_import_batch(
        session,
        settings=Settings(environment="test"),
        batch_id=batch.id,
        candidate_finder=lambda _session, _product, _floor, _limit: [],
    )

    assert first.no_matches == 1
    with pytest.raises(BatchAlreadyMatchedError):
        match_import_batch(
            session,
            settings=Settings(environment="test"),
            batch_id=batch.id,
            candidate_finder=lambda _session, _product, _floor, _limit: [],
        )
