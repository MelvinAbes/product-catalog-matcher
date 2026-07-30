from dataclasses import dataclass

from product_catalog_matcher.domain import MatchDecision
from product_catalog_matcher.matching.scoring import ProductScore


@dataclass(frozen=True)
class PolicyResult:
    decision: MatchDecision
    winning_margin: float | None


def classify_best_candidate(
    ranked_scores: list[ProductScore],
    *,
    auto_match_threshold: float,
    review_threshold: float,
    minimum_winning_margin: float,
) -> PolicyResult:
    if not ranked_scores:
        return PolicyResult(decision=MatchDecision.NO_MATCH, winning_margin=None)

    best = ranked_scores[0]
    runner_up_score = ranked_scores[1].score if len(ranked_scores) > 1 else 0.0
    margin = max(0.0, best.score - runner_up_score)
    if best.score >= auto_match_threshold and margin >= minimum_winning_margin:
        return PolicyResult(decision=MatchDecision.AUTO_MATCH, winning_margin=margin)
    if best.score >= review_threshold:
        return PolicyResult(decision=MatchDecision.REVIEW, winning_margin=margin)
    return PolicyResult(decision=MatchDecision.NO_MATCH, winning_margin=margin)
