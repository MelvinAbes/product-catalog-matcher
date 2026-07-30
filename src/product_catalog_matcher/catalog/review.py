from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from product_catalog_matcher.domain import MatchDecision, ReviewAction
from product_catalog_matcher.persistence.models import (
    CanonicalProduct,
    CatalogLink,
    MatchProposal,
    ReviewEvent,
    ScoreFactor,
    SupplierProduct,
)


class ReviewProposalNotFoundError(LookupError):
    pass


class ReviewConflictError(ValueError):
    pass


class ReviewTargetNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class FactorDetail:
    name: str
    raw_score: float
    weight: float
    contribution: float
    evidence: dict[str, object]


@dataclass(frozen=True)
class ProductDetail:
    id: UUID
    name: str
    brand: str | None
    category: str | None
    gtin: str | None
    manufacturer_part_number: str | None
    pack_quantity: str | None
    unit_value: str | None
    unit_code: str | None


@dataclass(frozen=True)
class ReviewItem:
    proposal_id: UUID
    score: float
    winning_margin: float | None
    policy_version: str
    semantic_used: bool
    created_at: datetime
    source: ProductDetail
    target: ProductDetail
    factors: tuple[FactorDetail, ...]


@dataclass(frozen=True)
class ReviewDecisionResult:
    event_id: UUID
    proposal_id: UUID
    action: ReviewAction
    canonical_product_id: UUID | None
    reviewer: str
    rationale: str
    created_at: datetime


@dataclass(frozen=True)
class ReviewDecisionCommand:
    proposal_id: UUID
    action: ReviewAction
    reviewer: str
    rationale: str
    canonical_product_id: UUID | None = None


def list_open_reviews(
    session: Session,
    *,
    limit: int,
    offset: int,
) -> list[ReviewItem]:
    reviewed = exists(
        select(ReviewEvent.id).where(ReviewEvent.match_proposal_id == MatchProposal.id)
    )
    statement = (
        select(MatchProposal)
        .where(
            MatchProposal.rank == 1,
            MatchProposal.decision == MatchDecision.REVIEW,
            ~reviewed,
        )
        .order_by(MatchProposal.created_at, MatchProposal.id)
        .offset(offset)
        .limit(limit)
    )
    return [_build_review_item(session, proposal) for proposal in session.scalars(statement)]


def get_review_item(session: Session, proposal_id: UUID) -> ReviewItem:
    proposal = _get_review_proposal(session, proposal_id)
    return _build_review_item(session, proposal)


def decide_review(
    session: Session,
    command: ReviewDecisionCommand,
) -> ReviewDecisionResult:
    try:
        proposal = _get_review_proposal(session, command.proposal_id)
        existing_event = session.scalar(
            select(ReviewEvent.id).where(ReviewEvent.match_proposal_id == command.proposal_id)
        )
        if existing_event is not None:
            raise ReviewConflictError("This proposal already has a review decision.")

        selected_target = _resolve_review_target(
            session,
            proposal=proposal,
            action=command.action,
            canonical_product_id=command.canonical_product_id,
        )
        if command.action in {ReviewAction.ACCEPTED, ReviewAction.REASSIGNED}:
            if selected_target is None:
                raise ReviewConflictError("Accepted decisions require a target product.")
            existing_link = session.scalar(
                select(CatalogLink).where(
                    CatalogLink.supplier_product_id == proposal.supplier_product_id
                )
            )
            if existing_link is not None:
                raise ReviewConflictError("The supplier product is already linked.")
            session.add(
                CatalogLink(
                    supplier_product_id=proposal.supplier_product_id,
                    canonical_product_id=selected_target.id,
                    match_proposal_id=proposal.id,
                    method="manual",
                    confidence=1,
                )
            )

        event = ReviewEvent(
            match_proposal_id=proposal.id,
            canonical_product_id=selected_target.id if selected_target else None,
            action=command.action,
            reviewer=command.reviewer,
            rationale=command.rationale,
        )
        session.add(event)
        session.commit()
        session.refresh(event)
    except (
        ReviewConflictError,
        ReviewProposalNotFoundError,
        ReviewTargetNotFoundError,
    ):
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise

    return ReviewDecisionResult(
        event_id=event.id,
        proposal_id=proposal.id,
        action=event.action,
        canonical_product_id=event.canonical_product_id,
        reviewer=event.reviewer,
        rationale=event.rationale,
        created_at=event.created_at,
    )


def list_review_events(session: Session, proposal_id: UUID) -> list[ReviewDecisionResult]:
    _get_review_proposal(session, proposal_id)
    statement = (
        select(ReviewEvent)
        .where(ReviewEvent.match_proposal_id == proposal_id)
        .order_by(ReviewEvent.created_at, ReviewEvent.id)
    )
    return [
        ReviewDecisionResult(
            event_id=event.id,
            proposal_id=event.match_proposal_id,
            action=event.action,
            canonical_product_id=event.canonical_product_id,
            reviewer=event.reviewer,
            rationale=event.rationale,
            created_at=event.created_at,
        )
        for event in session.scalars(statement)
    ]


def _get_review_proposal(session: Session, proposal_id: UUID) -> MatchProposal:
    proposal = session.get(MatchProposal, proposal_id)
    if proposal is None or proposal.rank != 1 or proposal.decision is not MatchDecision.REVIEW:
        raise ReviewProposalNotFoundError(f"Review proposal {proposal_id} was not found.")
    return proposal


def _resolve_review_target(
    session: Session,
    *,
    proposal: MatchProposal,
    action: ReviewAction,
    canonical_product_id: UUID | None,
) -> CanonicalProduct | None:
    if action is ReviewAction.REJECTED:
        if canonical_product_id is not None:
            raise ReviewConflictError("Rejected decisions cannot specify a target product.")
        return None
    if action is ReviewAction.ACCEPTED:
        if canonical_product_id not in {None, proposal.canonical_product_id}:
            raise ReviewConflictError("Use reassigned when selecting a different target.")
        canonical_product_id = proposal.canonical_product_id
    if action is ReviewAction.REASSIGNED and canonical_product_id is None:
        raise ReviewConflictError("Reassigned decisions require a target product.")

    target = session.get(CanonicalProduct, canonical_product_id)
    if target is None:
        raise ReviewTargetNotFoundError(f"Canonical product {canonical_product_id} was not found.")
    return target


def _build_review_item(session: Session, proposal: MatchProposal) -> ReviewItem:
    source = session.get(SupplierProduct, proposal.supplier_product_id)
    target = session.get(CanonicalProduct, proposal.canonical_product_id)
    if source is None or target is None:
        raise ReviewProposalNotFoundError(f"Review proposal {proposal.id} is incomplete.")
    factors = tuple(
        FactorDetail(
            name=factor.name,
            raw_score=float(factor.raw_score),
            weight=float(factor.weight),
            contribution=float(factor.contribution),
            evidence=factor.evidence,
        )
        for factor in session.scalars(
            select(ScoreFactor)
            .where(ScoreFactor.match_proposal_id == proposal.id)
            .order_by(ScoreFactor.contribution.desc(), ScoreFactor.name)
        )
    )
    return ReviewItem(
        proposal_id=proposal.id,
        score=float(proposal.score),
        winning_margin=(
            float(proposal.runner_up_margin) if proposal.runner_up_margin is not None else None
        ),
        policy_version=proposal.policy_version,
        semantic_used=proposal.semantic_used,
        created_at=proposal.created_at,
        source=_source_detail(source),
        target=_target_detail(target),
        factors=factors,
    )


def _source_detail(product: SupplierProduct) -> ProductDetail:
    return ProductDetail(
        id=product.id,
        name=product.name,
        brand=product.brand,
        category=product.category,
        gtin=product.gtin,
        manufacturer_part_number=product.manufacturer_part_number,
        pack_quantity=str(product.pack_quantity) if product.pack_quantity else None,
        unit_value=str(product.unit_value) if product.unit_value else None,
        unit_code=product.unit_code,
    )


def _target_detail(product: CanonicalProduct) -> ProductDetail:
    return ProductDetail(
        id=product.id,
        name=product.name,
        brand=product.brand,
        category=product.category,
        gtin=product.gtin,
        manufacturer_part_number=product.manufacturer_part_number,
        pack_quantity=str(product.pack_quantity) if product.pack_quantity else None,
        unit_value=str(product.unit_value) if product.unit_value else None,
        unit_code=product.unit_code,
    )
