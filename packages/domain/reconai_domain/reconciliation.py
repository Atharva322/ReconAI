from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .money import Money

WorkflowStatus = Literal["MATCHED", "PARTIAL_REVIEW", "REVIEW_REQUIRED", "VALIDATION_FAILED"]


@dataclass(frozen=True)
class ReconciliationInput:
    invoice_number: str
    payment_reference: str
    invoice_total: Money
    payment_received: Money
    authorized_promotion: Money
    stated_deduction: Money | None = None
    promotion_code: str | None = None
    review_reason: str | None = None
    validation_error: str | None = None


@dataclass(frozen=True)
class DeductionOutcome:
    claimed_deduction: Money
    validated_deduction: Money
    unexplained_deduction: Money


@dataclass(frozen=True)
class ReconciliationResult:
    invoice_number: str
    payment_reference: str
    status: WorkflowStatus
    matched_cents: int
    deduction: DeductionOutcome
    rule_codes: tuple[str, ...]
    review_reason: str | None = None
    algorithm_version: str = "reconai.rules.v1"


def reconcile_payment(input_data: ReconciliationInput) -> ReconciliationResult:
    invoice_total = input_data.invoice_total
    payment_received = input_data.payment_received
    authorized_promotion = input_data.authorized_promotion
    invoice_total._check_currency(payment_received)
    invoice_total._check_currency(authorized_promotion)

    if payment_received.amount_cents > invoice_total.amount_cents:
        raise ValueError("payment cannot exceed invoice total")

    short_pay = invoice_total - payment_received
    claimed_deduction = input_data.stated_deduction if input_data.stated_deduction is not None else short_pay
    invoice_total._check_currency(claimed_deduction)
    validated_cents = min(claimed_deduction.amount_cents, authorized_promotion.amount_cents)
    validated = Money(validated_cents)
    unexplained = Money(claimed_deduction.amount_cents - validated_cents)

    rule_codes: list[str] = ["EXACT_INVOICE_REFERENCE", "AMOUNT_ARITHMETIC_EXACT"]
    if claimed_deduction.amount_cents:
        rule_codes.append("DEDUCTION_DETECTED")
    if validated.amount_cents:
        rule_codes.append("PROMOTION_VALIDATED")
    if unexplained.amount_cents:
        rule_codes.append("UNEXPLAINED_DEDUCTION_REVIEW")
    if input_data.review_reason:
        rule_codes.append(f"REVIEW_SIGNAL:{input_data.review_reason}")
    if input_data.validation_error:
        rule_codes.append(f"VALIDATION_ERROR:{input_data.validation_error}")

    status: WorkflowStatus
    review_reason = input_data.review_reason
    if input_data.validation_error:
        status = "VALIDATION_FAILED"
        review_reason = input_data.validation_error
    elif input_data.review_reason == "partial_payment_open_balance":
        status = "PARTIAL_REVIEW"
    elif input_data.review_reason or unexplained.amount_cents:
        status = "REVIEW_REQUIRED"
        if not review_reason and unexplained.amount_cents:
            review_reason = "unexplained_deduction_amount"
    else:
        status = "MATCHED"

    return ReconciliationResult(
        invoice_number=input_data.invoice_number,
        payment_reference=input_data.payment_reference,
        status=status,
        matched_cents=payment_received.amount_cents,
        deduction=DeductionOutcome(
            claimed_deduction=claimed_deduction,
            validated_deduction=validated,
            unexplained_deduction=unexplained,
        ),
        rule_codes=tuple(rule_codes),
        review_reason=review_reason,
    )
