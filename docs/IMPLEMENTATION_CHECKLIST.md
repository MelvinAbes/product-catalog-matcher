# Implementation checklist

## Foundation

- [x] Record requirements, architecture, and trade-offs
- [x] Configure Python, dependency locking, formatting, linting, typing, and tests
- [x] Add typed settings, structured logging, and health endpoints
- [x] Add Docker Compose and database migrations

## Data pipeline

- [x] Model suppliers, batches, source products, canonical products, issues, and proposals
- [x] Parse bounded CSV and JSON feeds
- [x] Normalize product attributes and validate identifiers
- [x] Detect duplicate and malformed records
- [x] Produce batch-level data-quality reports

## Matching and review

- [x] Generate bounded candidates with exact, blocked, and trigram retrieval
- [x] Implement weighted deterministic factors and policy decisions
- [x] Add the optional semantic scorer
- [x] Persist proposal explanations and catalog links
- [x] Implement review endpoints and append-only audit events
- [x] Build the review interface

## Evaluation and delivery

- [x] Add original feeds and gold labels
- [x] Calculate precision, recall, and F1
- [x] Add unit, repository, and API integration tests
- [x] Add CI, security scans, and container smoke tests
- [x] Verify setup from a clean environment
- [x] Complete API examples, screenshots, limitations, roadmap, and private interview notes
