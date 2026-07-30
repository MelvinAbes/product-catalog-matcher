# Requirements

## Problem

Supplier feeds often describe the same product with different titles, identifiers, units, and
category structures. Naive joins either miss equivalent products or silently merge distinct
ones. The service must preserve source evidence, produce explainable proposals, and route
ambiguous cases to a reviewer.

## Functional scope

1. Register suppliers and import UTF-8 CSV or JSON feeds.
2. Validate required fields and report malformed or duplicate rows without discarding the
   import batch.
3. Normalize names, brands, categories, identifiers, model numbers, units, and pack sizes.
4. Seed canonical products from a reference feed.
5. Generate bounded match candidates for candidate feeds.
6. Score exact identifiers, normalized text, token similarity, and weighted attributes.
7. Optionally include local semantic similarity without changing the deterministic default.
8. Classify proposals as automatic matches, review items, or no-match results.
9. Store factor-level explanations and append-only reviewer decisions.
10. Expose REST endpoints, a review interface, data-quality reports, and evaluation metrics.

## Quality attributes

- Typed Python and validated configuration
- PostgreSQL migrations and transactional writes
- Bounded uploads and row counts
- Structured logs, request metrics, liveness, and database readiness
- No credentials in source control
- Reproducible dependency resolution and container setup
- Unit tests for algorithms and PostgreSQL integration tests for queries and API workflows

## Acceptance criteria

- The original demonstration feeds import without undocumented manual changes.
- Every match proposal exposes its policy version, total score, factor scores, and evidence.
- An uncertain proposal can be accepted or rejected from both the API and review page.
- Re-running the checked-in evaluation dataset produces precision, recall, and F1 from saved
  predictions and gold labels.
- Formatting, linting, typing, tests, secret scanning, dependency auditing, image scanning,
  container startup, and API smoke tests pass before publication.

## Out of scope

- Master-data authoring and supplier contract management
- Distributed job scheduling for very large feeds
- Automatically retraining a model from reviewer decisions
- Multi-tenant authorization
- Real supplier or customer data

