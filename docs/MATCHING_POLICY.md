# Matching policy

The default policy is deterministic and versioned as `deterministic-v1`. Candidate retrieval,
factor scoring, and decision classification are separate steps.

## Candidate retrieval

PostgreSQL produces at most 20 candidates per supplier record using available exact GTIN and
manufacturer-part-number evidence, normalized brand or category blocking, and `pg_trgm` name
similarity. The default trigram floor is `0.25`. Candidate generation narrows work; it does not
make the final decision.

## Factor scoring

| Factor | Base weight | Comparison |
| --- | ---: | --- |
| GTIN | 0.30 | Exact normalized value |
| Name | 0.20 | Character similarity |
| Tokens | 0.15 | Order-insensitive token-set similarity |
| Brand | 0.10 | Normalized text similarity |
| Category | 0.05 | Normalized text similarity |
| Manufacturer part number | 0.10 | Exact normalized value |
| Quantity | 0.05 | Relative total-quantity difference |
| Semantic | 0.05 | Optional local embedding similarity |

Only factors with evidence on both records are active. Their weights are normalized to sum to
one, and each contribution is `raw_score × normalized_weight`. This avoids treating missing
attributes as mismatches while keeping the evidence visible.

The optional semantic factor is disabled by default. It cannot replace identifier or attribute
evidence and adds at most its normalized share of the score.

## Decision classification

The highest-ranked candidate is classified using both confidence and separation:

```text
if score >= 0.80 and winning_margin >= 0.08:
    automatic match
elif score >= 0.65:
    manual review
else:
    no match
```

The winning margin is the difference between the best and second-best scores. When there is only
one candidate, the runner-up score is zero. A high-confidence near-tie remains in review because
confidence alone does not show that the target is unique.

## Audit evidence

The service stores up to three ranked proposals per source record. Each proposal records the
policy version, decision, score, rank, margin, and semantic-use flag. Each factor stores its raw
score, effective weight, contribution, and source/target evidence. Review actions append a
timestamped event with reviewer, rationale, action, and selected target.

Changing weights, evidence handling, or thresholds in a way that can change saved decisions
requires a new policy version and a reproduced evaluation report.
