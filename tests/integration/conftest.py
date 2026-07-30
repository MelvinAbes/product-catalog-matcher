from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.community.postgres import PostgresContainer

from product_catalog_matcher.config import Settings, get_settings
from product_catalog_matcher.database import get_session
from product_catalog_matcher.main import create_app

PROJECT_ROOT = Path(__file__).parents[2]
POSTGRES_IMAGE = "postgres@sha256:742f40ea20b9ff2ff31db5458d127452988a2164df9e17441e191f3b72252193"


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer(POSTGRES_IMAGE, driver="psycopg") as postgres:
        yield postgres.get_connection_url(driver="psycopg")


@pytest.fixture(scope="session")
def migrated_engine(postgres_url: str) -> Iterator[Engine]:
    alembic_config = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_config.attributes["database_url"] = postgres_url
    command.upgrade(alembic_config, "head")
    engine = create_engine(postgres_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def integration_settings(postgres_url: str) -> Settings:
    return Settings(environment="test", database_url=postgres_url, log_format="console")


@pytest.fixture
def api_application(
    migrated_engine: Engine,
    integration_settings: Settings,
) -> FastAPI:
    session_factory = sessionmaker(bind=migrated_engine, expire_on_commit=False)

    def session_override() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    application = create_app(integration_settings, readiness_check=lambda: True)
    application.dependency_overrides[get_session] = session_override
    application.dependency_overrides[get_settings] = lambda: integration_settings
    return application


@pytest.fixture
def api_client(api_application: FastAPI) -> Iterator[TestClient]:
    with TestClient(api_application) as client:
        yield client
