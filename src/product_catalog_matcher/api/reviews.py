from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from product_catalog_matcher.catalog.review import (
    ReviewDecisionCommand,
    ReviewItem,
    decide_review,
    get_review_item,
    list_open_reviews,
    list_review_events,
)
from product_catalog_matcher.database import get_session
from product_catalog_matcher.domain import ReviewAction

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])
SessionDependency = Annotated[Session, Depends(get_session)]


class ProductDetailResponse(BaseModel):
    id: UUID
    name: str
    brand: str | None
    category: str | None
    gtin: str | None
    manufacturer_part_number: str | None
    pack_quantity: str | None
    unit_value: str | None
    unit_code: str | None


class FactorDetailResponse(BaseModel):
    name: str
    raw_score: float
    weight: float
    contribution: float
    evidence: dict[str, object]


class ReviewItemResponse(BaseModel):
    proposal_id: UUID
    score: float
    winning_margin: float | None
    policy_version: str
    semantic_used: bool
    created_at: datetime
    source: ProductDetailResponse
    target: ProductDetailResponse
    factors: list[FactorDetailResponse]


class ReviewDecisionRequest(BaseModel):
    action: ReviewAction
    reviewer: str = Field(min_length=2, max_length=120)
    rationale: str = Field(min_length=5, max_length=500)
    canonical_product_id: UUID | None = None

    @model_validator(mode="after")
    def validate_target(self) -> "ReviewDecisionRequest":
        if self.action is ReviewAction.REASSIGNED and self.canonical_product_id is None:
            raise ValueError("reassigned decisions require canonical_product_id")
        if self.action is ReviewAction.REJECTED and self.canonical_product_id is not None:
            raise ValueError("rejected decisions cannot specify canonical_product_id")
        return self


class ReviewDecisionResponse(BaseModel):
    event_id: UUID
    proposal_id: UUID
    action: ReviewAction
    canonical_product_id: UUID | None
    reviewer: str
    rationale: str
    created_at: datetime


@router.get("")
def get_open_reviews(
    session: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ReviewItemResponse]:
    return [
        _review_response(item) for item in list_open_reviews(session, limit=limit, offset=offset)
    ]


@router.get("/{proposal_id}")
def get_review(proposal_id: UUID, session: SessionDependency) -> ReviewItemResponse:
    return _review_response(get_review_item(session, proposal_id))


@router.post(
    "/{proposal_id}/decisions",
    status_code=status.HTTP_201_CREATED,
)
def add_review_decision(
    proposal_id: UUID,
    payload: ReviewDecisionRequest,
    session: SessionDependency,
) -> ReviewDecisionResponse:
    result = decide_review(
        session,
        ReviewDecisionCommand(
            proposal_id=proposal_id,
            action=payload.action,
            reviewer=" ".join(payload.reviewer.split()),
            rationale=" ".join(payload.rationale.split()),
            canonical_product_id=payload.canonical_product_id,
        ),
    )
    return ReviewDecisionResponse.model_validate(result, from_attributes=True)


@router.get("/{proposal_id}/events")
def get_review_events(
    proposal_id: UUID,
    session: SessionDependency,
) -> list[ReviewDecisionResponse]:
    return [
        ReviewDecisionResponse.model_validate(event, from_attributes=True)
        for event in list_review_events(session, proposal_id)
    ]


def _review_response(item: ReviewItem) -> ReviewItemResponse:
    return ReviewItemResponse(
        proposal_id=item.proposal_id,
        score=item.score,
        winning_margin=item.winning_margin,
        policy_version=item.policy_version,
        semantic_used=item.semantic_used,
        created_at=item.created_at,
        source=ProductDetailResponse.model_validate(item.source, from_attributes=True),
        target=ProductDetailResponse.model_validate(item.target, from_attributes=True),
        factors=[
            FactorDetailResponse.model_validate(factor, from_attributes=True)
            for factor in item.factors
        ],
    )
