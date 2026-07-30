from fastapi.testclient import TestClient

from product_catalog_matcher.config import Settings
from product_catalog_matcher.main import create_app


def test_request_id_is_preserved_when_valid() -> None:
    client = TestClient(create_app(Settings(environment="test"), readiness_check=lambda: True))

    response = client.get("/health/live", headers={"X-Request-ID": "catalog-test-42"})

    assert response.headers["X-Request-ID"] == "catalog-test-42"


def test_invalid_request_id_is_replaced() -> None:
    client = TestClient(create_app(Settings(environment="test"), readiness_check=lambda: True))

    response = client.get("/health/live", headers={"X-Request-ID": "contains spaces"})

    assert response.headers["X-Request-ID"] != "contains spaces"
    assert len(response.headers["X-Request-ID"]) == 36


def test_metrics_use_route_templates_instead_of_raw_paths() -> None:
    client = TestClient(create_app(Settings(environment="test"), readiness_check=lambda: True))
    client.get("/health/live")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "catalog_matcher_http_requests_total" in response.text
    assert 'route="/health/live"' in response.text
