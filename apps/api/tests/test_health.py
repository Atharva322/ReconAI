from fastapi.testclient import TestClient

from reconai_api import app


def test_health_endpoint() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_tenant_endpoint() -> None:
    response = TestClient(app).get("/api/v1/demo-tenant")

    assert response.status_code == 200
    assert response.json()["name"] == "Northstar Beverages"
