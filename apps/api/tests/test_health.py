from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from reconai_api import app, create_app
from reconai_api.config import get_settings
from reconai_api.database import connect
from reconai_api.repositories.review_cases import ReviewCaseRepository


ROOT = Path(__file__).resolve().parents[3]
GOLDEN_INVOICE = ROOT / "data" / "benchmark" / "seed_20260806" / "evidence" / "s04_6811" / "invoice.pdf"
GOLDEN_REMITTANCE = ROOT / "data" / "benchmark" / "seed_20260806" / "evidence" / "s04_6811" / "remittance.pdf"
LINKED_EXACT_INVOICE = ROOT / "data" / "benchmark" / "linked_seed_20260807" / "evidence" / "exact_full_payment_0001" / "invoice.pdf"
LINKED_EXACT_REMITTANCE = ROOT / "data" / "benchmark" / "linked_seed_20260807" / "evidence" / "exact_full_payment_0001" / "remittance.pdf"
NO_TEXT_PDF = ROOT / "data" / "generated" / "northstar_no_text_scan.pdf"


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


def test_process_sample_documents_creates_review_case_from_extracted_pdfs() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/reconciliation/process", data={"use_sample": "true"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["case_id"].startswith("processed-")
    assert payload["status"] == "REVIEW_REQUIRED"
    assert payload["invoice"]["invoice_number"] == "NSB-INV-1001"
    assert payload["invoice"]["total_cents"] == 1_845_000
    assert payload["payment"]["payment_reference"] == "PAY-NORTHSTAR-0001"
    assert payload["payment"]["received_cents"] == 1_720_000
    assert payload["deduction"]["claimed_cents"] == 125_000
    assert payload["deduction"]["validated_cents"] == 100_000
    assert payload["deduction"]["unexplained_cents"] == 25_000
    assert payload["review_reason"] == "unexplained_deduction_amount"
    assert any(field["field_name"] == "invoice_total" and field["normalized_value"] == "18450.00" for field in payload["extracted_fields"])
    assert [event["action"] for event in payload["audit_events"]] == [
        "documents_processed",
        "reconciliation_completed",
        "review_task_created",
    ]

    fetched = client.get(f"/api/v1/review-cases/{payload['case_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["deduction"]["unexplained_cents"] == 25_000


def test_process_uploaded_documents_then_decision_survives_new_api_instance() -> None:
    client = TestClient(app)
    with GOLDEN_INVOICE.open("rb") as invoice, GOLDEN_REMITTANCE.open("rb") as remittance:
        response = client.post(
            "/api/v1/reconciliation/process",
            files={
                "invoice": ("invoice.pdf", invoice, "application/pdf"),
                "remittance": ("remittance.pdf", remittance, "application/pdf"),
            },
        )
    payload = response.json()
    case_id = payload["case_id"]

    decision = client.post(
        f"/api/v1/review-cases/{case_id}/decision",
        json={"decision": "dispute", "comment": "Dispute the dynamically extracted over-claim."},
    )
    recreated_client = TestClient(create_app())
    persisted = recreated_client.get(f"/api/v1/review-cases/{case_id}")

    assert response.status_code == 200
    assert decision.status_code == 200
    assert decision.json()["status"] == "DISPUTED"
    assert persisted.status_code == 200
    assert persisted.json()["status"] == "DISPUTED"
    assert persisted.json()["review_decision"]["comment"] == "Dispute the dynamically extracted over-claim."


def test_process_linked_benchmark_pair_without_promotion_field() -> None:
    client = TestClient(app)
    with LINKED_EXACT_INVOICE.open("rb") as invoice, LINKED_EXACT_REMITTANCE.open("rb") as remittance:
        response = client.post(
            "/api/v1/reconciliation/process",
            files={
                "invoice": ("invoice.pdf", invoice, "application/pdf"),
                "remittance": ("remittance.pdf", remittance, "application/pdf"),
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "REVIEW_REQUIRED"
    assert payload["promotion"]["authorized_cents"] == 0
    assert payload["promotion"]["promotion_code"] == "NO-PROMOTION-EVIDENCE"
    assert payload["deduction"]["claimed_cents"] == 0
    assert payload["deduction"]["unexplained_cents"] == 0


def test_process_no_text_pdf_routes_to_review_without_fabricated_fields() -> None:
    client = TestClient(app)
    with NO_TEXT_PDF.open("rb") as invoice, NO_TEXT_PDF.open("rb") as remittance:
        response = client.post(
            "/api/v1/reconciliation/process",
            files={
                "invoice": ("invoice.pdf", invoice, "application/pdf"),
                "remittance": ("remittance.pdf", remittance, "application/pdf"),
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "REVIEW_REQUIRED"
    assert payload["invoice"]["invoice_number"] == "INSUFFICIENT_EVIDENCE"
    assert payload["extracted_fields"] == []
    assert payload["rule_codes"] == ["INSUFFICIENT_DOCUMENT_EVIDENCE"]
    assert "no text layer found" in payload["review_reason"]


def test_process_corrupt_pdf_returns_controlled_422(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.pdf"
    corrupt.write_bytes(b"not a pdf")

    client = TestClient(app)
    with corrupt.open("rb") as invoice, GOLDEN_REMITTANCE.open("rb") as remittance:
        response = client.post(
            "/api/v1/reconciliation/process",
            files={
                "invoice": ("corrupt.pdf", invoice, "application/pdf"),
                "remittance": ("remittance.pdf", remittance, "application/pdf"),
            },
        )

    assert response.status_code == 422
    assert "invalid or unreadable PDF" in response.text


def test_process_non_pdf_upload_returns_415() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/reconciliation/process",
        files={
            "invoice": ("invoice.txt", b"not a pdf", "text/plain"),
            "remittance": ("remittance.pdf", GOLDEN_REMITTANCE.read_bytes(), "application/pdf"),
        },
    )

    assert response.status_code == 415


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
