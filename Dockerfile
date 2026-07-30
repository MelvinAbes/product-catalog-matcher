FROM ghcr.io/astral-sh/uv@sha256:5164bf84e7b4e2e08ce0b4c66b4a8c996a286e6959f72ac5c6e0a3c80e8cb04a AS uv

FROM python@sha256:601d3d3797e90e2534782e69c85fafb7971b43f24c7b1b079b7e48dd435e458d AS builder

COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python@sha256:601d3d3797e90e2534782e69c85fafb7971b43f24c7b1b079b7e48dd435e458d AS runtime

RUN addgroup -S -g 10001 catalog \
    && adduser -S -D -H -u 10001 -G catalog catalog

WORKDIR /app
COPY --from=builder --chown=catalog:catalog /app/.venv /app/.venv
COPY --chown=catalog:catalog alembic.ini ./
COPY --chown=catalog:catalog migrations ./migrations
COPY --chown=catalog:catalog src ./src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER catalog
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2)"]

CMD ["python", "-m", "product_catalog_matcher.bootstrap"]
