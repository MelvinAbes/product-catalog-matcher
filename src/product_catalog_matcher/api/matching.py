from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from product_catalog_matcher.config import Settings, get_settings
from product_catalog_matcher.database import get_session
from product_catalog_matcher.matching.service import match_import_batch

router = APIRouter(prefix="/api/v1/imports", tags=["matching"])
SessionDependency = Annotated[Session, Depends(get_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


class MatchBatchResponse(BaseModel):
    batch_id: UUID
    processed: int
    auto_matches: int
    review_items: int
    no_matches: int
    policy_version: str
    semantic_used: bool


@router.post("/{batch_id}/match", status_code=status.HTTP_200_OK)
def match_batch(
    batch_id: UUID,
    session: SessionDependency,
    settings: SettingsDependency,
) -> MatchBatchResponse:
    result = match_import_batch(session, settings=settings, batch_id=batch_id)
    return MatchBatchResponse.model_validate(result, from_attributes=True)
