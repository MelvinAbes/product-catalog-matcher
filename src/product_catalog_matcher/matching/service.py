from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from product_catalog_matcher.config import Settings
from product_catalog_matcher.domain import ImportRole, MatchDecision, RecordStatus
from product_catalog_matcher.matching.candidates import find_postgres_candidates
from product_catalog_matcher.matching.policy import classify_best_candidate
from product_catalog_matcher.matching.scoring import (
    POLICY_VERSION,
    ProductScore,
    SemanticScorer,
    score_product_pair,
)
from product_catalog_matcher.matching.semantic import SentenceTransformerScorer
from product_catalog_matcher.persistence.models import (
    CanonicalProduct,
    CatalogLink,
    ImportBatch,
    MatchProposal,
    ScoreFactor,
    SupplierProduct,
)

CandidateFinder = Callable[[Session, SupplierProduct, float, int], Sequence[CanonicalProduct]]


class MatchBatchNotFoundError(LookupError):
    pass


class ReferenceBatchMatchError(ValueError):
    pass


class BatchAlreadyMatchedError(ValueError):
    pass


@dataclass(frozen=True)
class MatchBatchResult:
    batch_id: UUID
    processed: int
    auto_matches: int
    review_items: int
    no_matches: int
    policy_version: str
    semantic_used: bool


def match_import_batch(
    session: Session,
    *,
    settings: Settings,
    batch_id: UUID,
    candidate_finder: CandidateFinder | None = None,
    semantic_scorer: SemanticScorer | None = None,
) -> MatchBatchResult:
    try:
        batch = session.get(ImportBatch, batch_id)
        if batch is None:
            raise MatchBatchNotFoundError(f"Import batch {batch_id} was not found.")
        if batch.role is ImportRole.REFERENCE:
            raise ReferenceBatchMatchError(
                "Reference imports seed the catalog and are not matched."
            )

        products = list(
            session.scalars(
                select(SupplierProduct)
                .where(
                    SupplierProduct.import_batch_id == batch_id,
                    SupplierProduct.record_status.in_([RecordStatus.VALID, RecordStatus.DUPLICATE]),
                )
                .order_by(SupplierProduct.source_row_number)
            )
        )
        if any(product.match_policy_version is not None for product in products):
            raise BatchAlreadyMatchedError("This import batch has already been matched.")

        selected_semantic_scorer = semantic_scorer
        if settings.semantic_matching_enabled and selected_semantic_scorer is None:
            selected_semantic_scorer = SentenceTransformerScorer(settings.semantic_model)
        finder = candidate_finder or _default_candidate_finder
        decisions: list[MatchDecision] = []

        for product in products:
            candidates = finder(
                session,
                product,
                settings.candidate_similarity_floor,
                settings.candidate_limit,
            )
            ranked = sorted(
                (
                    score_product_pair(
                        product,
                        candidate,
                        semantic_scorer=selected_semantic_scorer,
                    )
                    for candidate in candidates
                ),
                key=lambda item: item.score,
                reverse=True,
            )
            policy = classify_best_candidate(
                ranked,
                auto_match_threshold=settings.auto_match_threshold,
                review_threshold=settings.review_threshold,
                minimum_winning_margin=settings.minimum_winning_margin,
            )
            _persist_ranked_scores(
                session,
                product=product,
                ranked=ranked[: settings.proposal_limit],
                decision=policy.decision,
                winning_margin=policy.winning_margin,
            )
            product.match_decision = policy.decision
            product.match_policy_version = POLICY_VERSION
            product.matched_at = datetime.now(UTC)
            decisions.append(policy.decision)
        session.commit()
    except (
        BatchAlreadyMatchedError,
        MatchBatchNotFoundError,
        ReferenceBatchMatchError,
    ):
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise

    return MatchBatchResult(
        batch_id=batch_id,
        processed=len(decisions),
        auto_matches=decisions.count(MatchDecision.AUTO_MATCH),
        review_items=decisions.count(MatchDecision.REVIEW),
        no_matches=decisions.count(MatchDecision.NO_MATCH),
        policy_version=POLICY_VERSION,
        semantic_used=selected_semantic_scorer is not None,
    )


def _default_candidate_finder(
    session: Session,
    product: SupplierProduct,
    similarity_floor: float,
    limit: int,
) -> Sequence[CanonicalProduct]:
    return find_postgres_candidates(
        session,
        product,
        similarity_floor=similarity_floor,
        limit=limit,
    )


def _persist_ranked_scores(
    session: Session,
    *,
    product: SupplierProduct,
    ranked: list[ProductScore],
    decision: MatchDecision,
    winning_margin: float | None,
) -> None:
    for index, product_score in enumerate(ranked, start=1):
        proposal_decision = decision if index == 1 else MatchDecision.NO_MATCH
        proposal = MatchProposal(
            supplier_product_id=product.id,
            canonical_product_id=product_score.canonical_product.id,
            rank=index,
            score=_decimal(product_score.score),
            runner_up_margin=(
                _decimal(winning_margin) if index == 1 and winning_margin is not None else None
            ),
            decision=proposal_decision,
            policy_version=POLICY_VERSION,
            semantic_used=product_score.semantic_used,
        )
        session.add(proposal)
        session.flush()
        session.add_all(
            ScoreFactor(
                match_proposal_id=proposal.id,
                name=factor.name,
                raw_score=_decimal(factor.raw_score),
                weight=_decimal(factor.weight),
                contribution=_decimal(factor.contribution),
                evidence=factor.evidence,
            )
            for factor in product_score.factors
        )
        if index == 1 and decision is MatchDecision.AUTO_MATCH:
            session.add(
                CatalogLink(
                    supplier_product_id=product.id,
                    canonical_product_id=product_score.canonical_product.id,
                    match_proposal_id=proposal.id,
                    method="automatic",
                    confidence=_decimal(product_score.score),
                )
            )


def count_match_proposals(session: Session, batch_id: UUID) -> int:
    statement = (
        select(func.count(MatchProposal.id))
        .join(
            SupplierProduct,
            SupplierProduct.id == MatchProposal.supplier_product_id,
        )
        .where(SupplierProduct.import_batch_id == batch_id)
    )
    return session.scalar(statement) or 0


def _decimal(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.000001"))
