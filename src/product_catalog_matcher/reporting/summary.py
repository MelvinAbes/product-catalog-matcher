from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from product_catalog_matcher.domain import MatchDecision
from product_catalog_matcher.persistence.models import (
    CanonicalProduct,
    ImportBatch,
    MatchProposal,
    ReviewEvent,
    Supplier,
    SupplierProduct,
)


@dataclass(frozen=True)
class RecentImport:
    id: UUID
    file_name: str
    supplier_code: str
    role: str
    status: str
    total_rows: int
    issue_count: int
    created_at: datetime


@dataclass(frozen=True)
class CatalogSummary:
    suppliers: int
    canonical_products: int
    supplier_products: int
    open_reviews: int
    automatic_matches: int
    no_matches: int
    recent_imports: tuple[RecentImport, ...]


def build_catalog_summary(session: Session) -> CatalogSummary:
    reviewed = exists(
        select(ReviewEvent.id).where(ReviewEvent.match_proposal_id == MatchProposal.id)
    )
    open_reviews = session.scalar(
        select(func.count(MatchProposal.id)).where(
            MatchProposal.rank == 1,
            MatchProposal.decision == MatchDecision.REVIEW,
            ~reviewed,
        )
    )
    recent_statement = (
        select(ImportBatch, Supplier.code)
        .join(Supplier, Supplier.id == ImportBatch.supplier_id)
        .order_by(ImportBatch.created_at.desc(), ImportBatch.id.desc())
        .limit(8)
    )
    return CatalogSummary(
        suppliers=_count(session, Supplier.id),
        canonical_products=_count(session, CanonicalProduct.id),
        supplier_products=_count(session, SupplierProduct.id),
        open_reviews=open_reviews or 0,
        automatic_matches=_count_decisions(session, MatchDecision.AUTO_MATCH),
        no_matches=_count_decisions(session, MatchDecision.NO_MATCH),
        recent_imports=tuple(
            RecentImport(
                id=batch.id,
                file_name=batch.file_name,
                supplier_code=supplier_code,
                role=batch.role.value,
                status=batch.status.value,
                total_rows=batch.total_rows,
                issue_count=batch.issue_count,
                created_at=batch.created_at,
            )
            for batch, supplier_code in session.execute(recent_statement)
        ),
    )


def _count(session: Session, column: InstrumentedAttribute[Any]) -> int:
    return session.scalar(select(func.count(column))) or 0


def _count_decisions(session: Session, decision: MatchDecision) -> int:
    return (
        session.scalar(
            select(func.count(SupplierProduct.id)).where(SupplierProduct.match_decision == decision)
        )
        or 0
    )
