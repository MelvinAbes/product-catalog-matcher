from pathlib import Path

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration
PROJECT_ROOT = Path(__file__).parents[2]


def test_complete_supplier_matching_and_review_workflow(api_client: TestClient) -> None:
    reference_supplier = _create_supplier(
        api_client,
        code="reference-integration",
        name="Reference Integration",
    )
    north_supplier = _create_supplier(
        api_client,
        code="north-integration",
        name="North Integration",
    )
    central_supplier = _create_supplier(
        api_client,
        code="central-integration",
        name="Central Integration",
    )

    reference_batch = _import_feed(
        api_client,
        supplier_id=reference_supplier["id"],
        role="reference",
        path=PROJECT_ROOT / "demo/feeds/reference-products.csv",
    )
    north_batch = _import_feed(
        api_client,
        supplier_id=north_supplier["id"],
        role="candidate",
        path=PROJECT_ROOT / "demo/feeds/supplier-north.json",
    )
    central_batch = _import_feed(
        api_client,
        supplier_id=central_supplier["id"],
        role="candidate",
        path=PROJECT_ROOT / "demo/feeds/supplier-central.csv",
    )

    assert reference_batch["accepted_rows"] == 17
    assert north_batch["accepted_rows"] == 10
    assert central_batch["accepted_rows"] == 9

    north_matches = api_client.post(f"/api/v1/imports/{north_batch['id']}/match")
    central_matches = api_client.post(f"/api/v1/imports/{central_batch['id']}/match")
    assert north_matches.status_code == 200
    assert central_matches.status_code == 200
    assert north_matches.json()["processed"] == 10
    assert central_matches.json()["processed"] == 9
    assert north_matches.json()["auto_matches"] >= 6
    assert central_matches.json()["auto_matches"] >= 6

    quality = api_client.get(f"/api/v1/imports/{central_batch['id']}/quality")
    assert quality.status_code == 200
    assert quality.json()["total_rows"] == 9
    assert quality.json()["acceptance_rate"] == 1.0

    reviews = api_client.get("/api/v1/reviews")
    assert reviews.status_code == 200
    assert len(reviews.json()) >= 1
    review = reviews.json()[0]
    detail = api_client.get(f"/api/v1/reviews/{review['proposal_id']}")
    assert detail.status_code == 200
    assert detail.json()["factors"]

    decision = api_client.post(
        f"/api/v1/reviews/{review['proposal_id']}/decisions",
        json={
            "action": "accepted",
            "reviewer": "integration-reviewer",
            "rationale": "Checked identifiers and normalized attributes.",
            "canonical_product_id": None,
        },
    )
    assert decision.status_code == 201
    assert decision.json()["action"] == "accepted"

    dashboard = api_client.get("/")
    assert dashboard.status_code == 200
    assert "Catalog matching at a glance" in dashboard.text
    assert "Supplier imports" in dashboard.text

    metrics = api_client.get("/metrics")
    assert metrics.status_code == 200
    assert "catalog_matcher_http_requests_total" in metrics.text


def test_invalid_feed_returns_problem_detail(api_client: TestClient) -> None:
    supplier = _create_supplier(
        api_client,
        code="invalid-feed-integration",
        name="Invalid Feed Integration",
    )

    response = api_client.post(
        "/api/v1/imports",
        data={"supplier_id": supplier["id"], "role": "candidate"},
        files={"file": ("feed.xml", b"<products/>", "application/xml")},
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"].endswith(":unsupported_format")


def _create_supplier(client: TestClient, *, code: str, name: str) -> dict[str, object]:
    response = client.post("/api/v1/suppliers", json={"code": code, "name": name})
    assert response.status_code == 201, response.text
    return response.json()


def _import_feed(
    client: TestClient,
    *,
    supplier_id: object,
    role: str,
    path: Path,
) -> dict[str, object]:
    media_type = "application/json" if path.suffix == ".json" else "text/csv"
    response = client.post(
        "/api/v1/imports",
        data={"supplier_id": str(supplier_id), "role": role},
        files={"file": (path.name, path.read_bytes(), media_type)},
    )
    assert response.status_code == 201, response.text
    return response.json()
