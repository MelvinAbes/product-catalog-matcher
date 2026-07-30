# Product Catalog Matcher

Product Catalog Matcher imports inconsistent supplier feeds and produces explainable match
proposals against a canonical catalog. It is designed to make data quality, confidence
thresholds, and reviewer decisions visible instead of hiding them behind a single score.

The repository is under active construction. The initial foundation includes typed
configuration, structured logging, database health checks, design records, and automated
quality checks. The matching and review slices are implemented in subsequent milestones.

## Local foundation

Prerequisites are Docker, `uv`, and Make.

```bash
cp .env.example .env
uv sync --frozen
make check
uv run uvicorn product_catalog_matcher.main:app --reload
```

The liveness endpoint is available at `http://localhost:8000/health/live`. Readiness also
checks PostgreSQL and remains unavailable until the database is running.

The design is documented in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), with scope and
acceptance criteria in [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md).

## Licence

Licensed under the Apache License 2.0. Demonstration data created for this project will be
included under the same licence.

