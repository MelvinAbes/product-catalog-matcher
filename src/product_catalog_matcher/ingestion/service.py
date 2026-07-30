import hashlib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from product_catalog_matcher.config import Settings
from product_catalog_matcher.domain import (
    ImportRole,
    ImportStatus,
    IssueSeverity,
    RecordStatus,
)
from product_catalog_matcher.ingestion.parser import (
    FeedStructureError,
    ParsedRow,
    RowIssue,
    parse_feed,
)
from product_catalog_matcher.normalization.products import NormalizedProduct, normalize_product
from product_catalog_matcher.persistence.models import (
    CanonicalProduct,
    CatalogLink,
    ImportBatch,
    ImportIssue,
    Supplier,
    SupplierProduct,
)


class SupplierNotFoundError(LookupError):
    pass


class ImportNotFoundError(LookupError):
    pass


class DuplicateFeedError(ValueError):
    pass


class SupplierCodeConflictError(ValueError):
    pass


@dataclass(frozen=True)
class FeedImportCommand:
    settings: Settings
    supplier_id: UUID
    role: ImportRole
    file_name: str
    content: bytes


def create_supplier(session: Session, *, code: str, name: str) -> Supplier:
    supplier = Supplier(code=code, name=name)
    try:
        session.add(supplier)
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise SupplierCodeConflictError(f"Supplier code {code!r} already exists.") from error
    return supplier


def list_suppliers(session: Session) -> list[Supplier]:
    return list(session.scalars(select(Supplier).order_by(Supplier.code)))


def get_supplier(session: Session, supplier_id: UUID) -> Supplier:
    supplier = session.get(Supplier, supplier_id)
    if supplier is None:
        raise SupplierNotFoundError(f"Supplier {supplier_id} was not found.")
    return supplier


def import_feed(
    session: Session,
    command: FeedImportCommand,
) -> ImportBatch:
    parsed = parse_feed(
        file_name=command.file_name,
        content=command.content,
        max_bytes=command.settings.upload_max_bytes,
        max_rows=command.settings.import_max_rows,
    )
    content_sha256 = hashlib.sha256(command.content).hexdigest()

    try:
        supplier = session.get(Supplier, command.supplier_id)
        if supplier is None:
            raise SupplierNotFoundError(f"Supplier {command.supplier_id} was not found.")
        if _batch_with_hash_exists(session, command.supplier_id, content_sha256):
            raise DuplicateFeedError("This supplier feed has already been imported.")

        batch = ImportBatch(
            supplier_id=supplier.id,
            role=command.role,
            status=ImportStatus.PROCESSING,
            file_name=command.file_name,
            content_sha256=content_sha256,
            started_at=datetime.now(UTC),
        )
        session.add(batch)
        session.flush()
        _persist_parsed_rows(session, batch=batch, parsed_rows=parsed.rows)
        batch.completed_at = datetime.now(UTC)
        batch.status = (
            ImportStatus.COMPLETED_WITH_ERRORS if batch.rejected_rows else ImportStatus.COMPLETED
        )
        session.commit()
    except (DuplicateFeedError, SupplierNotFoundError):
        session.rollback()
        raise
    except IntegrityError as error:
        session.rollback()
        raise DuplicateFeedError("This supplier feed conflicts with an existing import.") from error

    return batch


def get_import_batch(session: Session, batch_id: UUID) -> ImportBatch:
    batch = session.get(ImportBatch, batch_id)
    if batch is None:
        raise ImportNotFoundError(f"Import batch {batch_id} was not found.")
    return batch


def list_import_issues(session: Session, batch_id: UUID) -> list[ImportIssue]:
    get_import_batch(session, batch_id)
    statement = (
        select(ImportIssue)
        .where(ImportIssue.import_batch_id == batch_id)
        .order_by(ImportIssue.row_number.nullsfirst(), ImportIssue.created_at, ImportIssue.id)
    )
    return list(session.scalars(statement))


def list_import_products(session: Session, batch_id: UUID) -> list[SupplierProduct]:
    get_import_batch(session, batch_id)
    statement = (
        select(SupplierProduct)
        .where(SupplierProduct.import_batch_id == batch_id)
        .order_by(SupplierProduct.source_row_number, SupplierProduct.id)
    )
    return list(session.scalars(statement))


def _batch_with_hash_exists(session: Session, supplier_id: UUID, content_sha256: str) -> bool:
    statement = select(ImportBatch.id).where(
        ImportBatch.supplier_id == supplier_id,
        ImportBatch.content_sha256 == content_sha256,
    )
    return session.scalar(statement) is not None


def _persist_parsed_rows(
    session: Session,
    *,
    batch: ImportBatch,
    parsed_rows: tuple[ParsedRow, ...],
) -> None:
    source_ids: set[str] = set()
    canonical_by_fingerprint: dict[str, CanonicalProduct] = {}
    batch.total_rows = len(parsed_rows)

    for row in parsed_rows:
        if row.product is None:
            batch.rejected_rows += 1
            _persist_issues(session, batch, row.issues)
            continue

        if row.product.source_record_id in source_ids:
            batch.duplicate_rows += 1
            issue = RowIssue(
                row_number=row.row_number,
                field="source_record_id",
                code="duplicate_source_record_id",
                severity=IssueSeverity.ERROR,
                message="Source record identifier is repeated within this feed.",
            )
            _persist_issues(session, batch, (issue,))
            continue
        source_ids.add(row.product.source_record_id)

        normalized = normalize_product(row.product, row_number=row.row_number)
        _persist_issues(session, batch, (*row.issues, *normalized.issues))
        existing_canonical = canonical_by_fingerprint.get(normalized.product.fingerprint)
        record_status = (
            RecordStatus.DUPLICATE if existing_canonical is not None else RecordStatus.VALID
        )
        if record_status is RecordStatus.DUPLICATE:
            batch.duplicate_rows += 1
            _persist_issues(
                session,
                batch,
                (
                    RowIssue(
                        row_number=row.row_number,
                        field=None,
                        code="duplicate_product",
                        severity=IssueSeverity.WARNING,
                        message="Normalized product duplicates an earlier row in this feed.",
                    ),
                ),
            )

        supplier_product = _supplier_product_from_normalized(
            batch=batch,
            row_number=row.row_number,
            raw_data=row.raw_data,
            product=normalized.product,
            record_status=record_status,
        )
        session.add(supplier_product)
        session.flush()
        batch.accepted_rows += 1

        if batch.role is ImportRole.REFERENCE:
            canonical = existing_canonical or _canonical_from_normalized(normalized.product)
            if existing_canonical is None:
                session.add(canonical)
                session.flush()
                canonical_by_fingerprint[normalized.product.fingerprint] = canonical
            session.add(
                CatalogLink(
                    supplier_product_id=supplier_product.id,
                    canonical_product_id=canonical.id,
                    method="reference_seed",
                    confidence=Decimal("1"),
                )
            )

    batch.issue_count = len(
        session.scalars(select(ImportIssue.id).where(ImportIssue.import_batch_id == batch.id)).all()
    )


def _persist_issues(
    session: Session,
    batch: ImportBatch,
    issues: tuple[RowIssue, ...],
) -> None:
    session.add_all(
        ImportIssue(
            import_batch_id=batch.id,
            row_number=issue.row_number,
            field=issue.field,
            code=issue.code,
            severity=issue.severity,
            message=issue.message,
        )
        for issue in issues
    )
    if issues:
        session.flush()


def _supplier_product_from_normalized(
    *,
    batch: ImportBatch,
    row_number: int,
    raw_data: dict[str, object],
    product: NormalizedProduct,
    record_status: RecordStatus,
) -> SupplierProduct:
    values = asdict(product)
    return SupplierProduct(
        supplier_id=batch.supplier_id,
        import_batch_id=batch.id,
        source_row_number=row_number,
        record_status=record_status,
        raw_data=raw_data,
        **values,
    )


def _canonical_from_normalized(product: NormalizedProduct) -> CanonicalProduct:
    return CanonicalProduct(
        name=product.name,
        normalized_name=product.normalized_name,
        brand=product.brand,
        normalized_brand=product.normalized_brand,
        category=product.category,
        normalized_category=product.normalized_category,
        gtin=product.normalized_gtin,
        manufacturer_part_number=product.manufacturer_part_number,
        normalized_mpn=product.normalized_mpn,
        pack_quantity=product.pack_quantity,
        unit_value=product.unit_value,
        unit_code=product.unit_code,
    )


__all__ = [
    "DuplicateFeedError",
    "FeedImportCommand",
    "FeedStructureError",
    "ImportNotFoundError",
    "SupplierCodeConflictError",
    "SupplierNotFoundError",
    "create_supplier",
    "get_import_batch",
    "get_supplier",
    "import_feed",
    "list_import_issues",
    "list_import_products",
    "list_suppliers",
]
