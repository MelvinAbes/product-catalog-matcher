.PHONY: audit check format lint lock run test test-integration type

lock:
	uv lock

run:
	uv run uvicorn product_catalog_matcher.main:app --reload

format:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff format --check .
	uv run ruff check .

type:
	uv run mypy

test:
	uv run pytest -m "not integration"

test-integration:
	uv run pytest -m integration

audit:
	uv export --frozen --no-dev --no-emit-project -o /tmp/product-catalog-matcher-requirements.txt
	uv run pip-audit -r /tmp/product-catalog-matcher-requirements.txt

check: lint type test

