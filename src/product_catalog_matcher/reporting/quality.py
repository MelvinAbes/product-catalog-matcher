from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from product_catalog_matcher.ingestion.service import ImportNotFoundError
from product_catalog_matcher.persistence.models import ImportBatch, ImportIssue, SupplierProduct

COMPLETENESS_FIELDS = (
    "brand",
    "category",
    "normalized_gtin",
    "normalized_mpn",
    "unit_value",
)


@dataclass(frozen=True)
class IssueCount:
    code: str
    severity: str
    count: int


@dataclass(frozen=True)
class FieldCompleteness:
    field: str
    populated: int
    total: int
    ratio: float


@dataclass(frozen=True)
class DataQualityReport:
    batch_id: UUID
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    duplicate_rows: int
    issue_count: int
    acceptance_rate: float
    rejection_rate: float
    duplicate_rate: float
    completeness: tuple[FieldCompleteness, ...]
    issues: tuple[IssueCount, ...]


def build_quality_report(session: Session, batch_id: UUID) -> DataQualityReport:
    batch = session.get(ImportBatch, batch_id)
    if batch is None:
        raise ImportNotFoundError(f"Import batch {batch_id} was not found.")
    products = list(
        session.scalars(select(SupplierProduct).where(SupplierProduct.import_batch_id == batch_id))
    )
    product_total = len(products)
    completeness = tuple(
        FieldCompleteness(
            field=field,
            populated=sum(getattr(product, field) is not None for product in products),
            total=product_total,
            ratio=(
                sum(getattr(product, field) is not None for product in products) / product_total
                if product_total
                else 0.0
            ),
        )
        for field in COMPLETENESS_FIELDS
    )
    issue_statement = (
        select(
            ImportIssue.code,
            ImportIssue.severity,
            func.count(ImportIssue.id),
        )
        .where(ImportIssue.import_batch_id == batch_id)
        .group_by(ImportIssue.code, ImportIssue.severity)
        .order_by(func.count(ImportIssue.id).desc(), ImportIssue.code)
    )
    issues = tuple(
        IssueCount(code=code, severity=severity.value, count=count)
        for code, severity, count in session.execute(issue_statement)
    )
    denominator = batch.total_rows or 1
    return DataQualityReport(
        batch_id=batch.id,
        total_rows=batch.total_rows,
        accepted_rows=batch.accepted_rows,
        rejected_rows=batch.rejected_rows,
        duplicate_rows=batch.duplicate_rows,
        issue_count=batch.issue_count,
        acceptance_rate=batch.accepted_rows / denominator,
        rejection_rate=batch.rejected_rows / denominator,
        duplicate_rate=batch.duplicate_rows / denominator,
        completeness=completeness,
        issues=issues,
    )
