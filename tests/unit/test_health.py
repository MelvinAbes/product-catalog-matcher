from fastapi.testclient import TestClient

from product_catalog_matcher.config import Settings
from product_catalog_matcher.main import create_app


def test_liveness_does_not_depend_on_database() -> None:
    client = TestClient(create_app(Settings(environment="test"), readiness_check=lambda: False))

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_database_failure() -> None:
    client = TestClient(create_app(Settings(environment="test"), readiness_check=lambda: False))

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


def test_readiness_reports_success() -> None:
    client = TestClient(create_app(Settings(environment="test"), readiness_check=lambda: True))

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
