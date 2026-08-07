from __future__ import annotations

from copy import deepcopy
from typing import Any

from fastapi import HTTPException


GOLDEN_REVIEW_CASE: dict[str, Any] = {
    "case_id": "review-golden-001",
    "tenant": "Northstar Beverages",
    "retailer": "Fictional Market Co.",
    "status": "REVIEW_REQUIRED",
    "priority": "high",
    "assignee": "Demo Analyst",
    "invoice": {
        "invoice_number": "NSB-INV-1001",
        "po_number": "PO-FMC-2026-001",
        "issue_date": "2026-08-06",
        "total_cents": 1_845_000,
    },
    "payment": {
        "payment_reference": "PAY-NORTHSTAR-0001",
        "payment_date": "2026-08-06",
        "received_cents": 1_720_000,
    },
    "deduction": {
        "claimed_cents": 125_000,
        "validated_cents": 100_000,
        "unexplained_cents": 25_000,
        "reason_code": "PROMO_OVER_CLAIM",
    },
    "promotion": {
        "promotion_code": "PROMO-SUMMER-1000",
        "authorized_cents": 100_000,
        "validity": "2026-07-01 to 2026-08-31",
    },
    "extracted_fields": [
        {
            "document_type": "invoice",
            "field_name": "invoice_number",
            "value": "NSB-INV-1001",
            "confidence": 0.98,
            "source": "northstar_invoice.pdf page 1",
        },
        {
            "document_type": "invoice",
            "field_name": "invoice_total",
            "value": "$18,450.00",
            "confidence": 0.98,
            "source": "northstar_invoice.pdf page 1",
        },
        {
            "document_type": "remittance",
            "field_name": "payment_reference",
            "value": "PAY-NORTHSTAR-0001",
            "confidence": 0.98,
            "source": "northstar_remittance.pdf page 1",
        },
        {
            "document_type": "remittance",
            "field_name": "payment_received",
            "value": "$17,200.00",
            "confidence": 0.98,
            "source": "northstar_remittance.pdf page 1",
        },
    ],
    "rule_codes": [
        "EXACT_INVOICE_REFERENCE",
        "AMOUNT_ARITHMETIC_EXACT",
        "DEDUCTION_DETECTED",
        "PROMOTION_VALIDATED",
        "UNEXPLAINED_DEDUCTION_REVIEW",
    ],
    "review_reason": "unexplained_deduction_amount",
    "audit_events": [
        {
            "timestamp": "2026-08-06T09:00:00Z",
            "actor": "system",
            "action": "documents_processed",
            "details": "Invoice and remittance fields extracted with provenance.",
        },
        {
            "timestamp": "2026-08-06T09:01:00Z",
            "actor": "reconai.rules.v1",
            "action": "reconciliation_completed",
            "details": "$1,250 claimed deduction, $1,000 validated promotion, $250 unexplained.",
        },
        {
            "timestamp": "2026-08-06T09:02:00Z",
            "actor": "system",
            "action": "review_task_created",
            "details": "Unexplained deduction routed to human review.",
        },
    ],
}

_review_case_state: dict[str, Any] = deepcopy(GOLDEN_REVIEW_CASE)


def get_review_case() -> dict[str, Any]:
    return deepcopy(_review_case_state)


def apply_review_decision(decision: str, comment: str) -> dict[str, Any]:
    global _review_case_state
    if _review_case_state["status"] != "REVIEW_REQUIRED":
        raise HTTPException(
            status_code=409,
            detail=f"Review case already decided with status {_review_case_state['status']}.",
        )

    case = deepcopy(_review_case_state)
    decision_action = "review_decision_recorded"
    case["status"] = "DISPUTED" if decision == "dispute" else "APPROVED"
    case["review_decision"] = {
        "decision": decision,
        "comment": comment,
        "actor": "Demo Analyst",
    }
    case["audit_events"].append(
        {
            "timestamp": "2026-08-06T09:05:00Z",
            "actor": "Demo Analyst",
            "action": decision_action,
            "details": f"{decision}: {comment}",
        }
    )
    _review_case_state = case
    return case


def reset_review_case() -> dict[str, Any]:
    global _review_case_state
    _review_case_state = deepcopy(GOLDEN_REVIEW_CASE)
    return get_review_case()
