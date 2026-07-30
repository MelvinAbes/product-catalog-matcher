from collections.abc import Sequence

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from product_catalog_matcher.persistence.models import CanonicalProduct, SupplierProduct


def find_postgres_candidates(
    session: Session,
    source: SupplierProduct,
    *,
    similarity_floor: float,
    limit: int,
) -> Sequence[CanonicalProduct]:
    similarity = func.similarity(CanonicalProduct.normalized_name, source.normalized_name)
    criteria = [similarity >= similarity_floor]
    if source.normalized_gtin:
        criteria.append(CanonicalProduct.gtin == source.normalized_gtin)
    if source.normalized_mpn:
        criteria.append(CanonicalProduct.normalized_mpn == source.normalized_mpn)
    if source.normalized_brand:
        criteria.append(
            (CanonicalProduct.normalized_brand == source.normalized_brand)
            & (similarity >= similarity_floor / 2)
        )
    if source.normalized_category:
        criteria.append(
            (CanonicalProduct.normalized_category == source.normalized_category)
            & (similarity >= similarity_floor / 2)
        )

    statement = select(CanonicalProduct).where(or_(*criteria))
    if source.normalized_gtin:
        exact_gtin = case((CanonicalProduct.gtin == source.normalized_gtin, 1), else_=0)
        statement = statement.order_by(exact_gtin.desc(), similarity.desc())
    else:
        statement = statement.order_by(similarity.desc())
    statement = statement.limit(limit)
    return list(session.scalars(statement))
