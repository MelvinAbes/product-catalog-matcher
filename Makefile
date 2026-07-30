.PHONY: audit build check demo down format lint lock logs migrate run test test-integration type up

lock:
	uv lock

run:
	uv run uvicorn product_catalog_matcher.main:app --reload

migrate:
	uv run alembic upgrade head

build:
	docker compose build

up:
	docker compose up --build --wait

down:
	docker compose down

logs:
	docker compose logs --tail=100

demo:
	./scripts/load-demo.sh

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
