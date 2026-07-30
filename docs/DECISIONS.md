# Design decisions

## PostgreSQL as the only stateful dependency

PostgreSQL stores source records, canonical products, proposals, audit events, and reporting
data. Its trigram extension supports a bounded text shortlist. A separate vector database would
add operational cost without improving the deterministic core of this project.

## Canonical catalog rather than pairwise clustering

Supplier products match against stable canonical targets. This produces clearer audit history
and reviewer actions than continually re-clustering every feed. It does require an explicit
reference-feed seeding step.

## Transparent weighted scoring

Exact identifiers and independent attributes contribute named factors. The policy considers
both the top score and its margin over the runner-up. This makes ambiguous near-ties visible and
prevents a high but non-unique score from being accepted automatically.

## Bounded synchronous imports

Imports run within a request with configured byte and row limits. This is easier to operate and
demonstrate locally. A durable worker queue is the appropriate extension once import duration
exceeds an HTTP request budget.

## Optional local semantic scoring

The deterministic matcher works without network access or model files. When explicitly enabled,
a local embedding model supplies one additional bounded factor. Model-specific code remains
behind a semantic scorer protocol so tests use a deterministic substitute.

## Server-rendered review interface

Jinja templates and small browser-native scripts keep the review interface easy to inspect and
avoid a separate frontend build. The REST API remains the authoritative workflow boundary.

