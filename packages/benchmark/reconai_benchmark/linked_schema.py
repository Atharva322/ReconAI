from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

LinkedSplit = Literal["dev", "validation", "held_out"]
LinkedStatus = Literal["MATCHED", "PARTIAL_REVIEW", "REVIEW_REQUIRED", "VALIDATION_FAILED"]


@dataclass(frozen=True)
class LinkedInvoice:
    invoice_number: str
    invoice_date: str
    po_number: str
    total_cents: int


@dataclass(frozen=True)
class LinkedPayment:
    payment_reference: str
    payment_date: str
    received_cents: int
    payment_mode: str


@dataclass(frozen=True)
class LinkedRemittance:
    invoice_references: tuple[str, ...]
    claimed_deduction_cents: int
    claimed_reason: str


@dataclass(frozen=True)
class SupportingEvidence:
    evidence_type: str
    reference: str
    authorized_cents: int
    valid_from: str
    valid_to: str


@dataclass(frozen=True)
class ExpectedAllocation:
    invoice_number: str
    applied_payment_cents: int


@dataclass(frozen=True)
class LinkedExpected:
    invoice_allocations: tuple[ExpectedAllocation, ...]
    open_balance_cents: int
    claimed_deduction_cents: int
    validated_deduction_cents: int
    unexplained_deduction_cents: int
    status: LinkedStatus
    review_reason: str | None


@dataclass(frozen=True)
class LinkedBenchmarkCase:
    case_id: str
    family: str
    split: LinkedSplit
    seed: int
    tenant: str
    retailer: str
    invoices: tuple[LinkedInvoice, ...]
    payment: LinkedPayment | None
    remittance: LinkedRemittance | None
    supporting_evidence: tuple[SupportingEvidence, ...]
    expected: LinkedExpected
    document_templates: tuple[str, ...]
    degradation: str
    notes: str

    def validate(self) -> None:
        invoice_total = sum(invoice.total_cents for invoice in self.invoices)
        applied_cash = sum(allocation.applied_payment_cents for allocation in self.expected.invoice_allocations)
        if self.expected.open_balance_cents != max(invoice_total - applied_cash, 0):
            raise ValueError(f"{self.case_id}: open balance arithmetic mismatch")
        if self.remittance and self.expected.claimed_deduction_cents != self.remittance.claimed_deduction_cents:
            raise ValueError(f"{self.case_id}: stated deduction mismatch")
        if self.expected.validated_deduction_cents > self.expected.claimed_deduction_cents:
            raise ValueError(f"{self.case_id}: validated deduction exceeds claim")
        if (
            self.expected.unexplained_deduction_cents
            != self.expected.claimed_deduction_cents - self.expected.validated_deduction_cents
        ):
            raise ValueError(f"{self.case_id}: unexplained deduction arithmetic mismatch")
        if self.expected.status != "MATCHED" and not self.expected.review_reason:
            raise ValueError(f"{self.case_id}: non-matched case missing review reason")
        for invoice in self.invoices:
            if invoice.total_cents < 0:
                raise ValueError(f"{self.case_id}: invoice total cannot be negative")
        if self.payment and self.payment.received_cents < 0:
            raise ValueError(f"{self.case_id}: payment cannot be negative")

    def to_json(self) -> dict[str, object]:
        self.validate()
        return asdict(self)
