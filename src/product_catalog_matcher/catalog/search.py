from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from product_catalog_matcher.normalization.products import normalize_text
from product_catalog_matcher.persistence.models import CanonicalProduct


class CanonicalProductNotFoundError(LookupError):
    pass


def search_catalog(
    session: Session,
    *,
    query: str | None,
    limit: int,
    offset: int,
) -> list[CanonicalProduct]:
    statement = select(CanonicalProduct)
    if query:
        normalized_query = normalize_text(query)
        statement = statement.where(CanonicalProduct.normalized_name.ilike(f"%{normalized_query}%"))
    statement = statement.order_by(CanonicalProduct.normalized_name, CanonicalProduct.id)
    return list(session.scalars(statement.offset(offset).limit(limit)))


def get_canonical_product(session: Session, product_id: UUID) -> CanonicalProduct:
    product = session.get(CanonicalProduct, product_id)
    if product is None:
        raise CanonicalProductNotFoundError(f"Canonical product {product_id} was not found.")
    return product
