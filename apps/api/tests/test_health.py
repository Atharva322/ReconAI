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


def test_golden_review_case_endpoint() -> None:
    response = TestClient(app).get("/api/v1/review-cases/golden")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "REVIEW_REQUIRED"
    assert payload["deduction"]["claimed_cents"] == 125_000
    assert payload["deduction"]["unexplained_cents"] == 25_000
    assert payload["review_reason"] == "unexplained_deduction_amount"


def test_golden_review_decision_endpoint() -> None:
    response = TestClient(app).post(
        "/api/v1/review-cases/golden/decision",
        json={"decision": "dispute", "comment": "Dispute the unexplained $250 over-claim."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "DISPUTED"
    assert payload["review_decision"]["decision"] == "dispute"
    assert payload["audit_events"][-1]["action"] == "review_decision_recorded"
