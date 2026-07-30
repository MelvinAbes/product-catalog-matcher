from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from product_catalog_matcher.database import get_session
from product_catalog_matcher.ingestion.service import create_supplier, list_suppliers

router = APIRouter(prefix="/api/v1/suppliers", tags=["suppliers"])
SessionDependency = Annotated[Session, Depends(get_session)]


class SupplierCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=2, max_length=200)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().casefold()

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())


class SupplierResponse(BaseModel):
    id: UUID
    code: str
    name: str
    created_at: datetime


@router.post("", status_code=status.HTTP_201_CREATED)
def add_supplier(payload: SupplierCreate, session: SessionDependency) -> SupplierResponse:
    return SupplierResponse.model_validate(
        create_supplier(session, code=payload.code, name=payload.name),
        from_attributes=True,
    )


@router.get("")
def get_suppliers(session: SessionDependency) -> list[SupplierResponse]:
    return [
        SupplierResponse.model_validate(supplier, from_attributes=True)
        for supplier in list_suppliers(session)
    ]
