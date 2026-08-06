from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .money import Money

WorkflowStatus = Literal["MATCHED", "REVIEW_REQUIRED"]


@dataclass(frozen=True)
class ReconciliationInput:
    invoice_number: str
    payment_reference: str
    invoice_total: Money
    payment_received: Money
    authorized_promotion: Money
    promotion_code: str | None = None


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
    algorithm_version: str = "reconai.rules.v1"


def reconcile_payment(input_data: ReconciliationInput) -> ReconciliationResult:
    invoice_total = input_data.invoice_total
    payment_received = input_data.payment_received
    authorized_promotion = input_data.authorized_promotion
    invoice_total._check_currency(payment_received)
    invoice_total._check_currency(authorized_promotion)

    if payment_received.amount_cents > invoice_total.amount_cents:
        raise ValueError("payment cannot exceed invoice total in Phase 0")

    claimed_deduction = invoice_total - payment_received
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

    status: WorkflowStatus = "REVIEW_REQUIRED" if unexplained.amount_cents else "MATCHED"

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
    )
