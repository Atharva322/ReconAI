import pytest
from fastapi.testclient import TestClient

from reconai_api import app, create_app
from reconai_api.config import get_settings
from reconai_api.database import connect
from reconai_api.repositories.review_cases import ReviewCaseRepository


def test_health_endpoint() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_tenant_endpoint() -> None:
    response = TestClient(app).get("/api/v1/demo-tenant")

    assert response.status_code == 200
    assert response.json()["name"] == "Northstar Beverages"


def test_golden_review_case_endpoint() -> None:
    TestClient(app).post("/api/v1/review-cases/golden/reset")
    response = TestClient(app).get("/api/v1/review-cases/golden")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "REVIEW_REQUIRED"
    assert payload["deduction"]["claimed_cents"] == 125_000
    assert payload["deduction"]["unexplained_cents"] == 25_000
    assert payload["review_reason"] == "unexplained_deduction_amount"


def test_golden_review_decision_endpoint() -> None:
    client = TestClient(app)
    client.post("/api/v1/review-cases/golden/reset")
    response = client.post(
        "/api/v1/review-cases/golden/decision",
        json={"decision": "dispute", "comment": "Dispute the unexplained $250 over-claim."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "DISPUTED"
    assert payload["review_decision"]["decision"] == "dispute"
    assert payload["review_decision"]["comment"] == "Dispute the unexplained $250 over-claim."
    assert payload["review_decision"]["actor"] == "demo_reviewer"
    assert payload["audit_events"][-1]["action"] == "review_decision_recorded"
    assert sum(1 for event in payload["audit_events"] if event["action"] == "review_decision_recorded") == 1

    persisted = client.get("/api/v1/review-cases/golden")
    assert persisted.json()["status"] == "DISPUTED"


def test_golden_review_decision_rejects_invalid_transition() -> None:
    client = TestClient(app)
    client.post("/api/v1/review-cases/golden/reset")
    first = client.post(
        "/api/v1/review-cases/golden/decision",
        json={"decision": "approve", "comment": "Approve the validated review outcome."},
    )
    second = client.post(
        "/api/v1/review-cases/golden/decision",
        json={"decision": "dispute", "comment": "Try to dispute after approval."},
    )

    assert first.status_code == 200
    assert first.json()["status"] == "APPROVED"
    assert second.status_code == 409


def test_golden_review_decision_survives_new_api_instance() -> None:
    client = TestClient(app)
    client.post("/api/v1/review-cases/golden/reset")
    client.post(
        "/api/v1/review-cases/golden/decision",
        json={"decision": "dispute", "comment": "Persist this decision across app instances."},
    )

    recreated_client = TestClient(create_app())
    response = recreated_client.get("/api/v1/review-cases/golden")

    assert response.status_code == 200
    assert response.json()["status"] == "DISPUTED"
    assert response.json()["review_decision"]["comment"] == "Persist this decision across app instances."


def test_failed_decision_audit_insert_rolls_back_state(monkeypatch: pytest.MonkeyPatch) -> None:
    with connect(get_settings()) as conn:
        repository = ReviewCaseRepository(conn)
        repository.reset_golden_case(
            [
                {
                    "timestamp": "2026-08-06T09:00:00Z",
                    "actor": "system",
                    "action": "documents_processed",
                    "details": "Seeded for rollback test.",
                }
            ]
        )

        def fail_audit_insert(*args: object, **kwargs: object) -> None:
            raise RuntimeError("simulated audit insert failure")

        monkeypatch.setattr(repository, "_insert_decision_audit_event", fail_audit_insert)

        with pytest.raises(RuntimeError, match="simulated audit insert failure"):
            repository.record_decision(
                decision="dispute",
                comment="This update should roll back.",
                actor="demo_reviewer",
                audit_details="dispute: This update should roll back.",
            )

        state = repository.get_workflow_state()

    assert state is not None
    assert state["status"] == "REVIEW_REQUIRED"
    assert state["decision"] is None
    assert not any(event["action"] == "review_decision_recorded" for event in state["audit_events"])


def test_golden_review_reset_endpoint() -> None:
    client = TestClient(app)
    client.post("/api/v1/review-cases/golden/reset")
    client.post("/api/v1/review-cases/golden/decision", json={"decision": "approve", "comment": "Approve case."})

    response = client.post("/api/v1/review-cases/golden/reset")

    assert response.status_code == 200
    assert response.json()["status"] == "REVIEW_REQUIRED"


def test_reliability_demo_endpoint() -> None:
    response = TestClient(app).get("/api/v1/reliability/demo")

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is True
    assert payload["metrics"]["duplicate_uploads"] == 1
    assert payload["metrics"]["recovered_after_retry"] == 1
    assert payload["metrics"]["failed_documents"] == 1


def test_evidence_demo_endpoint() -> None:
    response = TestClient(app).get("/api/v1/evidence/demo")

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is True
    assert payload["unsupported_suggestion_acceptance_count"] == 0
    assert payload["adversarial_validation"]["status"] == "REJECTED"
