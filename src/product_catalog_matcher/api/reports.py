from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from product_catalog_matcher.database import get_session
from product_catalog_matcher.reporting.quality import build_quality_report

router = APIRouter(prefix="/api/v1/imports", tags=["reports"])
SessionDependency = Annotated[Session, Depends(get_session)]


class IssueCountResponse(BaseModel):
    code: str
    severity: str
    count: int


class FieldCompletenessResponse(BaseModel):
    field: str
    populated: int
    total: int
    ratio: float


class DataQualityReportResponse(BaseModel):
    batch_id: UUID
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    duplicate_rows: int
    issue_count: int
    acceptance_rate: float
    rejection_rate: float
    duplicate_rate: float
    completeness: list[FieldCompletenessResponse]
    issues: list[IssueCountResponse]


@router.get("/{batch_id}/quality")
def get_quality_report(
    batch_id: UUID,
    session: SessionDependency,
) -> DataQualityReportResponse:
    return DataQualityReportResponse.model_validate(
        build_quality_report(session, batch_id),
        from_attributes=True,
    )
