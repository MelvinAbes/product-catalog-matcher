from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from product_catalog_matcher.config import Settings
from product_catalog_matcher.domain import ImportRole
from product_catalog_matcher.ingestion.service import FeedImportCommand, import_feed
from product_catalog_matcher.persistence import models
from product_catalog_matcher.reporting.quality import build_quality_report


def test_quality_report_uses_batch_denominator_and_field_completeness() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        supplier = models.Supplier(code="candidate", name="Candidate Supplier")
        session.add(supplier)
        session.commit()
        batch = import_feed(
            session,
            FeedImportCommand(
                settings=Settings(environment="test"),
                supplier_id=supplier.id,
                role=ImportRole.CANDIDATE,
                file_name="candidate.csv",
                content=b"id,name,brand\nC-1,Product One,Kite\nC-2,\n",
            ),
        )

        report = build_quality_report(session, batch.id)

    assert report.total_rows == 2
    assert report.acceptance_rate == 0.5
    assert report.rejection_rate == 0.5
    brand = next(item for item in report.completeness if item.field == "brand")
    assert brand.ratio == 1.0
