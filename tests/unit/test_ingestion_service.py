from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from product_catalog_matcher.config import Settings
from product_catalog_matcher.domain import ImportRole, ImportStatus, RecordStatus
from product_catalog_matcher.ingestion.service import (
    DuplicateFeedError,
    FeedImportCommand,
    import_feed,
)
from product_catalog_matcher.persistence import models


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.Base.metadata.create_all(engine)
    with Session(engine) as database_session:
        supplier = models.Supplier(code="reference", name="Reference Supplier")
        database_session.add(supplier)
        database_session.commit()
        yield database_session


def test_reference_import_seeds_catalog_and_preserves_duplicate_source_row(
    session: Session,
) -> None:
    supplier = session.scalar(select(models.Supplier))
    assert supplier is not None
    content = (
        b"id,name,brand,gtin,amount,unit\n"
        b"R-1,Arabica Coffee,Northwind,4006381333931,1,kg\n"
        b"R-2,arabica-coffee,Northwind,4006381333931,1000,g\n"
    )

    batch = import_feed(
        session,
        FeedImportCommand(
            settings=Settings(environment="test"),
            supplier_id=supplier.id,
            role=ImportRole.REFERENCE,
            file_name="reference.csv",
            content=content,
        ),
    )

    assert batch.status is ImportStatus.COMPLETED
    assert batch.accepted_rows == 2
    assert batch.duplicate_rows == 1
    assert batch.issue_count == 1
    assert session.scalar(select(func.count(models.CanonicalProduct.id))) == 1
    assert session.scalar(select(func.count(models.CatalogLink.id))) == 2
    products = list(
        session.scalars(
            select(models.SupplierProduct).order_by(models.SupplierProduct.source_row_number)
        )
    )
    assert products[0].record_status is RecordStatus.VALID
    assert products[1].record_status is RecordStatus.DUPLICATE
    assert products[0].raw_data["name"] == "Arabica Coffee"
    assert products[0].unit_value == Decimal("1000")


def test_invalid_rows_are_recorded_without_aborting_batch(session: Session) -> None:
    supplier = session.scalar(select(models.Supplier))
    assert supplier is not None

    batch = import_feed(
        session,
        FeedImportCommand(
            settings=Settings(environment="test"),
            supplier_id=supplier.id,
            role=ImportRole.CANDIDATE,
            file_name="candidate.csv",
            content=b"id,name\nC-1,Valid Product\nC-2,\n",
        ),
    )

    assert batch.status is ImportStatus.COMPLETED_WITH_ERRORS
    assert batch.total_rows == 2
    assert batch.accepted_rows == 1
    assert batch.rejected_rows == 1
    assert batch.issue_count == 1


def test_same_content_cannot_be_imported_twice_for_one_supplier(session: Session) -> None:
    supplier = session.scalar(select(models.Supplier))
    assert supplier is not None
    command = FeedImportCommand(
        settings=Settings(environment="test"),
        supplier_id=supplier.id,
        role=ImportRole.CANDIDATE,
        file_name="candidate.csv",
        content=b"id,name\nC-1,Valid Product\n",
    )

    import_feed(session, command)

    with pytest.raises(DuplicateFeedError):
        import_feed(session, command)
