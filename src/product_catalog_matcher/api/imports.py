from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from product_catalog_matcher.config import Settings, get_settings
from product_catalog_matcher.database import get_session
from product_catalog_matcher.domain import (
    ImportRole,
    ImportStatus,
    IssueSeverity,
    RecordStatus,
)
from product_catalog_matcher.ingestion.service import (
    FeedImportCommand,
    get_import_batch,
    import_feed,
    list_import_issues,
    list_import_products,
)

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])
SessionDependency = Annotated[Session, Depends(get_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


class ImportBatchResponse(BaseModel):
    id: UUID
    supplier_id: UUID
    role: ImportRole
    status: ImportStatus
    file_name: str
    content_sha256: str
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    duplicate_rows: int
    issue_count: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class ImportIssueResponse(BaseModel):
    id: UUID
    row_number: int | None
    field: str | None
    code: str
    severity: IssueSeverity
    message: str


class ImportedProductResponse(BaseModel):
    id: UUID
    source_record_id: str
    source_row_number: int
    record_status: RecordStatus
    name: str
    normalized_name: str
    brand: str | None
    normalized_brand: str | None
    category: str | None
    normalized_category: str | None
    gtin: str | None
    normalized_gtin: str | None
    manufacturer_part_number: str | None
    normalized_mpn: str | None
    pack_quantity: str | None
    unit_value: str | None
    unit_code: str | None
    fingerprint: str


@router.post("", status_code=status.HTTP_201_CREATED)
def add_import(
    session: SessionDependency,
    settings: SettingsDependency,
    supplier_id: Annotated[UUID, Form()],
    role: Annotated[Literal["reference", "candidate"], Form()],
    file: Annotated[UploadFile, File()],
) -> ImportBatchResponse:
    safe_name = (file.filename or "feed").replace("\\", "/").rsplit("/", maxsplit=1)[-1]
    content = file.file.read(settings.upload_max_bytes + 1)
    batch = import_feed(
        session,
        FeedImportCommand(
            settings=settings,
            supplier_id=supplier_id,
            role=ImportRole(role),
            file_name=safe_name,
            content=content,
        ),
    )
    return ImportBatchResponse.model_validate(batch, from_attributes=True)


@router.get("/{batch_id}")
def get_import(batch_id: UUID, session: SessionDependency) -> ImportBatchResponse:
    return ImportBatchResponse.model_validate(
        get_import_batch(session, batch_id),
        from_attributes=True,
    )


@router.get("/{batch_id}/issues")
def get_issues(batch_id: UUID, session: SessionDependency) -> list[ImportIssueResponse]:
    return [
        ImportIssueResponse.model_validate(issue, from_attributes=True)
        for issue in list_import_issues(session, batch_id)
    ]


@router.get("/{batch_id}/products")
def get_products(batch_id: UUID, session: SessionDependency) -> list[ImportedProductResponse]:
    products = list_import_products(session, batch_id)
    return [
        ImportedProductResponse(
            id=product.id,
            source_record_id=product.source_record_id,
            source_row_number=product.source_row_number,
            record_status=product.record_status,
            name=product.name,
            normalized_name=product.normalized_name,
            brand=product.brand,
            normalized_brand=product.normalized_brand,
            category=product.category,
            normalized_category=product.normalized_category,
            gtin=product.gtin,
            normalized_gtin=product.normalized_gtin,
            manufacturer_part_number=product.manufacturer_part_number,
            normalized_mpn=product.normalized_mpn,
            pack_quantity=str(product.pack_quantity) if product.pack_quantity else None,
            unit_value=str(product.unit_value) if product.unit_value else None,
            unit_code=product.unit_code,
            fingerprint=product.fingerprint,
        )
        for product in products
    ]
