# Implementation checklist

## Foundation

- [x] Record requirements, architecture, and trade-offs
- [x] Configure Python, dependency locking, formatting, linting, typing, and tests
- [x] Add typed settings, structured logging, and health endpoints
- [ ] Add Docker Compose and database migrations

## Data pipeline

- [ ] Model suppliers, batches, source products, canonical products, issues, and proposals
- [ ] Parse bounded CSV and JSON feeds
- [ ] Normalize product attributes and validate identifiers
- [ ] Detect duplicate and malformed records
- [ ] Produce batch-level data-quality reports

## Matching and review

- [ ] Generate bounded candidates with exact, blocked, and trigram retrieval
- [ ] Implement weighted deterministic factors and policy decisions
- [ ] Add the optional semantic scorer
- [ ] Persist proposal explanations and catalog links
- [ ] Implement review endpoints and append-only audit events
- [ ] Build the review interface

## Evaluation and delivery

- [ ] Add original feeds and gold labels
- [ ] Calculate precision, recall, and F1
- [ ] Add unit, repository, and API integration tests
- [ ] Add CI, security scans, and container smoke tests
- [ ] Verify setup from a clean environment
- [ ] Complete API examples, screenshots, limitations, roadmap, and private interview notes

