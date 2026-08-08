from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from reconai_domain.money import Money
from reconai_domain.reconciliation import ReconciliationInput, reconcile_payment
from reconai_extraction import ExtractionResult, extract_invoice_summary, extract_promotion_summary, extract_remittance_summary

from ..repositories.review_cases import ReviewCaseRepository


TENANT_NAME = "Northstar Beverages"
RETAILER_NAME = "Fictional Market Co."


class DocumentProcessingService:
    def __init__(self, repository: ReviewCaseRepository, root: Path):
        self.repository = repository
        self.root = root

    def process_documents(self, invoice_path: Path, remittance_path: Path, promotion_path: Path | None = None) -> dict[str, Any]:
        invoice_result = extract_invoice_summary(invoice_path)
        remittance_result = extract_remittance_summary(remittance_path)
        promotion_result = extract_promotion_summary(promotion_path) if promotion_path else None
        case_id = f"processed-{uuid4()}"

        if (
            invoice_result.status == "INVALID_DOCUMENT"
            or remittance_result.status == "INVALID_DOCUMENT"
            or (promotion_result and promotion_result.status == "INVALID_DOCUMENT")
        ):
            raise HTTPException(status_code=422, detail=_error_detail(invoice_result, remittance_result, promotion_result))

        case = self._build_review_case(case_id, invoice_result, remittance_result, promotion_result)
        self.repository.create_review_case(case_id, case, case["audit_events"])
        state = self.repository.get_workflow_state(case_id)
        if state is None:
            raise HTTPException(status_code=500, detail="Processed review case was not persisted.")

        case["audit_events"] = state["audit_events"]
        return case

    def process_sample_documents(self) -> dict[str, Any]:
        sample_dir = self.root / "data" / "benchmark" / "linked_seed_20260807" / "evidence" / "promotion_overclaim_0001"
        return self.process_documents(sample_dir / "invoice.pdf", sample_dir / "remittance.pdf", promotion_path=sample_dir / "promotion.pdf")

    def _build_review_case(
        self,
        case_id: str,
        invoice_result: ExtractionResult,
        remittance_result: ExtractionResult,
        promotion_result: ExtractionResult | None = None,
    ) -> dict[str, Any]:
        extracted_fields = _api_fields("invoice", invoice_result) + _api_fields("remittance", remittance_result)
        if promotion_result:
            extracted_fields += _api_fields("promotion", promotion_result)
        now = datetime.now(UTC).replace(microsecond=0).isoformat()

        if invoice_result.status != "EXTRACTED" or remittance_result.status != "EXTRACTED" or (
            promotion_result and promotion_result.status != "EXTRACTED"
        ):
            case = _insufficient_evidence_case(case_id, extracted_fields, invoice_result, remittance_result, promotion_result)
            case["audit_events"] = [
                _audit_event(now, "reconai.extraction.v1", "documents_processed", _error_detail(invoice_result, remittance_result, promotion_result)),
                _audit_event(now, "system", "review_task_created", "Insufficient document evidence routed to human review."),
            ]
            return case

        invoice_fields = _field_map(invoice_result)
        remittance_fields = _field_map(remittance_result)
        promotion_fields = _field_map(promotion_result) if promotion_result else {}
        invoice_number = invoice_fields["invoice_number"]
        remittance_invoice_number = remittance_fields["invoice_number"]
        invoice_total = Money.parse(invoice_fields["invoice_total"])
        payment_received = Money.parse(remittance_fields["payment_received"])
        short_pay = invoice_total - payment_received
        has_stated_deduction = "claimed_deduction" in remittance_fields
        stated_deduction = Money.parse(
            remittance_fields["claimed_deduction"]
            if has_stated_deduction
            else (_format_decimal(short_pay.amount_cents) if "authorized_promotion" in remittance_fields else "0.00")
        )
        authorized_promotion = Money.parse(
            promotion_fields.get("authorized_promotion", remittance_fields.get("authorized_promotion", "0.00"))
        )
        promotion_code = promotion_fields.get(
            "promotion_id",
            "PROMO-FROM-REMITTANCE" if authorized_promotion.amount_cents else "NO-PROMOTION-EVIDENCE",
        )
        validation_error = None
        if invoice_number != remittance_invoice_number:
            validation_error = "invoice_reference_conflict"
        elif short_pay.amount_cents > 0 and stated_deduction.amount_cents not in {0, short_pay.amount_cents}:
            validation_error = "stated_deduction_mismatch"

        review_reason = None
        if short_pay.amount_cents > 0 and stated_deduction.amount_cents == 0 and validation_error is None:
            review_reason = "partial_payment_open_balance"
        elif short_pay.amount_cents > 0 and stated_deduction.amount_cents == short_pay.amount_cents and authorized_promotion.amount_cents == 0:
            review_reason = "unauthorized_deduction"

        reconciliation = reconcile_payment(
            ReconciliationInput(
                invoice_number=invoice_number,
                payment_reference=remittance_fields["payment_reference"],
                invoice_total=invoice_total,
                payment_received=payment_received,
                authorized_promotion=authorized_promotion,
                stated_deduction=stated_deduction,
                promotion_code=promotion_code,
                review_reason=review_reason,
                validation_error=validation_error,
            )
        )
        status = "REVIEW_REQUIRED"
        review_reason = reconciliation.review_reason or "document_processing_review"
        case = {
            "case_id": case_id,
            "tenant": TENANT_NAME,
            "retailer": RETAILER_NAME,
            "status": status,
            "priority": "high" if status == "REVIEW_REQUIRED" else "low",
            "assignee": "Demo Analyst",
            "invoice": {
                "invoice_number": invoice_number,
                "po_number": "extracted-from-upload",
                "issue_date": datetime.now(UTC).date().isoformat(),
                "total_cents": invoice_total.amount_cents,
            },
            "payment": {
                "payment_reference": reconciliation.payment_reference,
                "payment_date": datetime.now(UTC).date().isoformat(),
                "received_cents": reconciliation.matched_cents,
            },
            "deduction": {
                "claimed_cents": reconciliation.deduction.claimed_deduction.amount_cents,
                "validated_cents": reconciliation.deduction.validated_deduction.amount_cents,
                "unexplained_cents": reconciliation.deduction.unexplained_deduction.amount_cents,
                "open_balance_cents": short_pay.amount_cents,
                "reason_code": "PROMOTION_RECONCILIATION",
            },
            "promotion": {
                "promotion_code": promotion_code,
                "authorized_cents": authorized_promotion.amount_cents,
                "validity": (
                    "Derived from submitted promotion evidence"
                    if promotion_result and authorized_promotion.amount_cents
                    else "Derived from submitted remittance evidence"
                    if authorized_promotion.amount_cents
                    else "No authorized promotion evidence submitted"
                ),
            },
            "extracted_fields": extracted_fields,
            "rule_codes": list(reconciliation.rule_codes),
            "review_reason": review_reason,
            "audit_events": [
                _audit_event(now, "reconai.extraction.v1", "documents_processed", _processed_detail(promotion_result)),
                _audit_event(
                    now,
                    reconciliation.algorithm_version,
                    "reconciliation_completed",
                    (
                        f"{_format_money(reconciliation.deduction.claimed_deduction.amount_cents)} claimed deduction, "
                        f"{_format_money(reconciliation.deduction.validated_deduction.amount_cents)} validated promotion, "
                        f"{_format_money(reconciliation.deduction.unexplained_deduction.amount_cents)} unexplained."
                    ),
                ),
            ],
        }
        if status == "REVIEW_REQUIRED":
            case["audit_events"].append(
                _audit_event(now, "system", "review_task_created", "Reconciled exception routed to human review.")
            )
        return case


def _insufficient_evidence_case(
    case_id: str,
    extracted_fields: list[dict[str, Any]],
    invoice_result: ExtractionResult,
    remittance_result: ExtractionResult,
    promotion_result: ExtractionResult | None = None,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "tenant": TENANT_NAME,
        "retailer": RETAILER_NAME,
        "status": "REVIEW_REQUIRED",
        "priority": "high",
        "assignee": "Demo Analyst",
        "invoice": {"invoice_number": "INSUFFICIENT_EVIDENCE", "po_number": "unknown", "issue_date": "", "total_cents": 0},
        "payment": {"payment_reference": "INSUFFICIENT_EVIDENCE", "payment_date": "", "received_cents": 0},
        "deduction": {
            "claimed_cents": 0,
            "validated_cents": 0,
            "unexplained_cents": 0,
            "open_balance_cents": 0,
            "reason_code": "INSUFFICIENT_EVIDENCE",
        },
        "promotion": {"promotion_code": "unknown", "authorized_cents": 0, "validity": "Insufficient submitted evidence"},
        "extracted_fields": extracted_fields,
        "rule_codes": ["INSUFFICIENT_DOCUMENT_EVIDENCE"],
        "review_reason": _error_detail(invoice_result, remittance_result, promotion_result),
        "audit_events": [],
    }


def _api_fields(document_type: str, result: ExtractionResult) -> list[dict[str, Any]]:
    return [
        {
            "document_type": document_type,
            "field_name": field.field_name,
            "value": field.raw_value,
            "raw_value": field.raw_value,
            "normalized_value": field.normalized_value,
            "confidence": field.confidence,
            "page": field.page,
            "source": f"{field.source} page {field.page}",
        }
        for field in result.fields
    ]


def _field_map(result: ExtractionResult) -> dict[str, str]:
    return {field.field_name: field.normalized_value for field in result.fields}


def _audit_event(timestamp: str, actor: str, action: str, details: str) -> dict[str, str]:
    return {"timestamp": timestamp, "actor": actor, "action": action, "details": details}


def _error_detail(*results: ExtractionResult | None) -> str:
    errors: list[str] = []
    for result in results:
        if result is None:
            continue
        if result.status != "EXTRACTED":
            errors.extend(f"{result.document_type}: {error}" for error in result.errors)
    return "; ".join(errors) or "insufficient document evidence"


def _format_money(amount_cents: int) -> str:
    return f"${amount_cents / 100:,.2f}"


def _format_decimal(amount_cents: int) -> str:
    dollars, cents = divmod(amount_cents, 100)
    return f"{dollars}.{cents:02d}"


def _processed_detail(promotion_result: ExtractionResult | None) -> str:
    if promotion_result:
        return "Invoice, remittance, and promotion fields extracted from submitted PDFs."
    return "Invoice and remittance fields extracted from submitted PDFs."
