from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

DatasetSplit = Literal["dev", "eval", "golden_demo"]
ExpectedStatus = Literal["MATCHED", "PARTIAL_REVIEW", "REVIEW_REQUIRED", "VALIDATION_FAILED"]


@dataclass(frozen=True)
class BenchmarkScenario:
    scenario_id: str
    family_id: str
    split: DatasetSplit
    seed: int
    tenant: str
    retailer: str
    invoice_number: str
    payment_reference: str
    invoice_total_cents: int
    payment_received_cents: int
    authorized_promotion_cents: int
    expected_status: ExpectedStatus
    expected_claimed_deduction_cents: int
    expected_validated_deduction_cents: int
    expected_unexplained_deduction_cents: int
    expected_review_reason: str | None
    document_templates: tuple[str, ...]
    degradation: str
    notes: str

    def to_json(self) -> dict[str, object]:
        data = asdict(self)
        data["document_templates"] = list(self.document_templates)
        return data


SCENARIO_FAMILIES = {
    "S01": "exact invoice payment",
    "S02": "explicit partial payment",
    "S03": "payment plus authorized promotion",
    "S04": "promotion over-claim",
    "S05": "one payment, multiple invoices",
    "S06": "duplicate remittance/document",
    "S07": "unknown invoice reference",
    "S08": "conflicting retailer/reference",
    "S09": "missing or low-confidence invoice ID",
    "S10": "inconsistent arithmetic",
    "S11": "rotated/noisy scan",
    "S12": "duplicate deduction claim",
}
