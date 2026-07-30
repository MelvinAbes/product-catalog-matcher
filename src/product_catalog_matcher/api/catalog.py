from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from product_catalog_matcher.catalog.search import (
    get_canonical_product,
    search_catalog,
)
from product_catalog_matcher.database import get_session
from product_catalog_matcher.persistence.models import CanonicalProduct

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])
SessionDependency = Annotated[Session, Depends(get_session)]


class CanonicalProductResponse(BaseModel):
    id: UUID
    name: str
    normalized_name: str
    brand: str | None
    category: str | None
    gtin: str | None
    manufacturer_part_number: str | None
    pack_quantity: str | None
    unit_value: str | None
    unit_code: str | None


@router.get("")
def get_catalog(
    session: SessionDependency,
    query: Annotated[str | None, Query(min_length=2, max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CanonicalProductResponse]:
    return [
        _catalog_response(product)
        for product in search_catalog(session, query=query, limit=limit, offset=offset)
    ]


@router.get("/{product_id}")
def get_catalog_product(
    product_id: UUID,
    session: SessionDependency,
) -> CanonicalProductResponse:
    return _catalog_response(get_canonical_product(session, product_id))


def _catalog_response(product: CanonicalProduct) -> CanonicalProductResponse:
    return CanonicalProductResponse(
        id=product.id,
        name=product.name,
        normalized_name=product.normalized_name,
        brand=product.brand,
        category=product.category,
        gtin=product.gtin,
        manufacturer_part_number=product.manufacturer_part_number,
        pack_quantity=str(product.pack_quantity) if product.pack_quantity else None,
        unit_value=str(product.unit_value) if product.unit_value else None,
        unit_code=product.unit_code,
    )
