FROM ghcr.io/astral-sh/uv@sha256:5164bf84e7b4e2e08ce0b4c66b4a8c996a286e6959f72ac5c6e0a3c80e8cb04a AS uv

FROM python@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7 AS builder

COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7 AS runtime

RUN groupadd --gid 10001 catalog \
    && useradd --uid 10001 --gid catalog --no-create-home --home-dir /app \
        --shell /usr/sbin/nologin catalog

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
