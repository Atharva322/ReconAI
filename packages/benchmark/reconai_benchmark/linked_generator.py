from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .linked_schema import (
    ExpectedAllocation,
    LinkedBenchmarkCase,
    LinkedExpected,
    LinkedInvoice,
    LinkedPayment,
    LinkedRemittance,
    SupportingEvidence,
)
from .pdf_renderer import render_blank_pdf, render_text_pdf
from .profiles import (
    DEDUCTION_REASONS,
    FAMILY_COUNTS,
    INVOICE_AMOUNT_BUCKETS_CENTS,
    INVOICE_TEMPLATES,
    PAYMENT_DELAY_DAYS,
    PAYMENT_MODES,
    PROMOTION_TEMPLATES,
    REMITTANCE_TEMPLATES,
)

LINKED_GENERATOR_VERSION = "benchmark.v2.linked-financial"
LINKED_DEFAULT_SEED = 20260807
LINKED_DIR_NAME = f"linked_seed_{LINKED_DEFAULT_SEED}"


@dataclass(frozen=True)
class LinkedDatasetBuild:
    cases: tuple[LinkedBenchmarkCase, ...]
    manifest: dict[str, object]


def build_linked_cases(seed: int = LINKED_DEFAULT_SEED) -> tuple[LinkedBenchmarkCase, ...]:
    cases: list[LinkedBenchmarkCase] = []
    ordinal = 0
    for family, count in FAMILY_COUNTS.items():
        for index in range(count):
            split = _split_for_ordinal(ordinal)
            cases.append(_build_case(seed, family, index, split))
            ordinal += 1
    return tuple(cases)


def generate_linked_dataset(root: Path, seed: int = LINKED_DEFAULT_SEED) -> LinkedDatasetBuild:
    cases = build_linked_cases(seed)
    benchmark_dir = root / "data" / "benchmark" / f"linked_seed_{seed}"
    truth_dir = benchmark_dir / "ground_truth"
    evidence_dir = benchmark_dir / "evidence"
    truth_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    truth_payload = [case.to_json() for case in cases]
    truth_path = truth_dir / "linked_cases.json"
    truth_path.write_text(json.dumps(truth_payload, indent=2) + "\n", encoding="utf-8")

    for case in cases:
        _render_case(evidence_dir, case)

    manifest = _manifest(root, seed, cases, truth_path, evidence_dir)
    (benchmark_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return LinkedDatasetBuild(cases=cases, manifest=manifest)


def _build_case(seed: int, family: str, index: int, split: str) -> LinkedBenchmarkCase:
    rng = random.Random(_stable_seed(seed, family, index))
    case_id = f"{family}_{index + 1:04d}"
    invoice_count = 2 if family == "one_payment_multiple_invoices" else 1
    invoices = tuple(_invoice(rng, case_id, i) for i in range(invoice_count))
    invoice_total = sum(invoice.total_cents for invoice in invoices)

    deduction_reason = rng.choice(DEDUCTION_REASONS)
    claimed = 0
    authorized = 0
    payment_received = invoice_total
    status = "MATCHED"
    review_reason = None
    remittance_present = True
    payment_present = True
    invoice_refs = tuple(invoice.invoice_number for invoice in invoices)
    degradation = "clean_digital"
    notes = "Clean linked financial case."

    if family == "valid_deduction":
        claimed = _round_cents(rng.randint(300, 1200) * 100)
        authorized = claimed
        payment_received = invoice_total - claimed
    elif family == "promotion_overclaim":
        claimed = _round_cents(rng.randint(800, 1600) * 100)
        authorized = max(claimed - _round_cents(rng.randint(100, 500) * 100), 0)
        payment_received = invoice_total - claimed
        status = "REVIEW_REQUIRED"
        review_reason = "unexplained_deduction_amount"
    elif family == "partial_payment":
        claimed = _round_cents(rng.randint(500, 1800) * 100)
        payment_received = invoice_total - claimed
        status = "PARTIAL_REVIEW"
        review_reason = "partial_payment_open_balance"
    elif family == "one_payment_multiple_invoices":
        payment_received = invoice_total
        notes = "One payment is allocated across multiple invoices; current domain scorer marks cardinality as unsupported."
    elif family == "multiple_payments_one_invoice":
        status = "REVIEW_REQUIRED"
        review_reason = "multiple_payment_allocation_not_supported"
        notes = "Multiple payments against one invoice are represented in truth but not scored by the current domain engine."
    elif family == "missing_remittance":
        remittance_present = False
        status = "REVIEW_REQUIRED"
        review_reason = "missing_remittance"
    elif family == "incorrect_invoice_reference":
        invoice_refs = (f"UNKNOWN-{rng.randint(1000, 9999)}",)
        status = "REVIEW_REQUIRED"
        review_reason = "unknown_invoice_reference"
    elif family == "duplicate_invoice_remittance":
        status = "REVIEW_REQUIRED"
        review_reason = "duplicate_document"
    elif family == "unauthorized_deduction":
        claimed = _round_cents(rng.randint(400, 1300) * 100)
        authorized = 0
        payment_received = invoice_total - claimed
        status = "REVIEW_REQUIRED"
        review_reason = "unauthorized_deduction"
        deduction_reason = "UNAUTHORIZED_ALLOWANCE"
    elif family == "amount_extraction_degradation":
        claimed = _round_cents(rng.randint(300, 1000) * 100)
        authorized = min(claimed, _round_cents(rng.randint(100, 600) * 100))
        payment_received = invoice_total - claimed
        degradation = "cropped_field_metadata"
        status = "REVIEW_REQUIRED" if claimed > authorized else "MATCHED"
        review_reason = "unexplained_deduction_amount" if status != "MATCHED" else None
    elif family == "reference_extraction_degradation":
        degradation = "rotation_metadata"
        status = "REVIEW_REQUIRED"
        review_reason = "low_confidence_invoice_reference"
    elif family == "image_only_no_text":
        degradation = "image_only"
        status = "REVIEW_REQUIRED"
        review_reason = "no_text_or_noisy_scan"
    elif family == "contradictory_evidence":
        claimed = _round_cents(rng.randint(700, 1500) * 100)
        authorized = min(claimed, _round_cents(rng.randint(100, 600) * 100))
        payment_received = invoice_total - claimed
        status = "VALIDATION_FAILED"
        review_reason = "stated_deduction_mismatch"
        notes = "Remittance stated deduction intentionally conflicts with calculated short-pay."

    payment = (
        LinkedPayment(
            payment_reference=f"PAY-{case_id.upper()}",
            payment_date=(date(2026, 8, 1) + timedelta(days=rng.choice(PAYMENT_DELAY_DAYS))).isoformat(),
            received_cents=payment_received,
            payment_mode=rng.choice(PAYMENT_MODES),
        )
        if payment_present
        else None
    )
    stated_claimed = claimed + (100_00 if family == "contradictory_evidence" else 0)
    remittance = (
        LinkedRemittance(
            invoice_references=invoice_refs,
            claimed_deduction_cents=stated_claimed,
            claimed_reason=deduction_reason,
        )
        if remittance_present
        else None
    )
    supporting = (
        (
            SupportingEvidence(
                evidence_type="promotion",
                reference=f"PROMO-{case_id.upper()}",
                authorized_cents=authorized,
                valid_from="2026-07-01",
                valid_to="2026-08-31",
            ),
        )
        if authorized or family in {"valid_deduction", "promotion_overclaim", "amount_extraction_degradation"}
        else ()
    )
    allocations = tuple(
        ExpectedAllocation(invoice.invoice_number, _allocated_payment(invoice, invoice_total, payment_received))
        for invoice in invoices
    )
    expected = LinkedExpected(
        invoice_allocations=allocations,
        claimed_deduction_cents=max(invoice_total - sum(a.applied_payment_cents for a in allocations), 0),
        validated_deduction_cents=min(max(invoice_total - payment_received, 0), authorized),
        unexplained_deduction_cents=max(max(invoice_total - payment_received, 0) - min(max(invoice_total - payment_received, 0), authorized), 0),
        status=status,  # type: ignore[arg-type]
        review_reason=review_reason,
    )
    case = LinkedBenchmarkCase(
        case_id=case_id,
        family=family,
        split=split,  # type: ignore[arg-type]
        seed=seed,
        tenant="Northstar Beverages",
        retailer="Fictional Market Co.",
        invoices=invoices,
        payment=payment,
        remittance=remittance,
        supporting_evidence=supporting,
        expected=expected,
        document_templates=(
            INVOICE_TEMPLATES[index % len(INVOICE_TEMPLATES)],
            REMITTANCE_TEMPLATES[index % len(REMITTANCE_TEMPLATES)],
            PROMOTION_TEMPLATES[index % len(PROMOTION_TEMPLATES)] if supporting else "no_promotion_evidence",
        ),
        degradation=degradation,
        notes=notes,
    )
    case.validate()
    return case


def _render_case(evidence_dir: Path, case: LinkedBenchmarkCase) -> None:
    case_dir = evidence_dir / case.case_id
    if case.degradation == "image_only":
        render_blank_pdf(case_dir / "invoice.pdf")
        render_blank_pdf(case_dir / "remittance.pdf")
        if case.supporting_evidence:
            render_blank_pdf(case_dir / "promotion.pdf")
        return

    invoice = case.invoices[0]
    render_text_pdf(
        case_dir / "invoice.pdf",
        "Northstar Beverages Invoice",
        _invoice_lines(case, invoice),
    )
    if case.remittance and case.payment:
        render_text_pdf(
            case_dir / "remittance.pdf",
            "Payment Remittance Advice",
            _remittance_lines(case),
        )
    if case.supporting_evidence:
        render_text_pdf(case_dir / "promotion.pdf", "Promotion Allowance Agreement", _promotion_lines(case))
    if case.family == "duplicate_invoice_remittance":
        (case_dir / "invoice_duplicate.pdf").write_bytes((case_dir / "invoice.pdf").read_bytes())
        if (case_dir / "remittance.pdf").exists():
            (case_dir / "remittance_duplicate.pdf").write_bytes((case_dir / "remittance.pdf").read_bytes())


def _invoice_lines(case: LinkedBenchmarkCase, invoice: LinkedInvoice) -> list[str]:
    template = case.document_templates[0]
    if template == "invoice_table_v1":
        return [
            f"Customer: {case.retailer}",
            f"PO Number: {invoice.po_number}",
            "Line | Description | Amount",
            f"1 | Grocery shipment | {_format_cents(invoice.total_cents)}",
            f"Invoice #: {invoice.invoice_number}",
            f"Amount Due: {_format_cents(invoice.total_cents)}",
        ]
    if template == "invoice_compact_v1":
        return [
            f"Bill To {case.retailer}",
            f"Inv No {invoice.invoice_number}",
            f"PO {invoice.po_number}",
            f"Total Due {_format_cents(invoice.total_cents)}",
        ]
    if template == "invoice_retailer_v1":
        return [
            f"Retailer: {case.retailer}",
            f"Invoice Number: {invoice.invoice_number}",
            f"Invoice Date: {invoice.invoice_date}",
            f"Invoice Total: {_format_cents(invoice.total_cents)}",
        ]
    return [
        f"Retailer: {case.retailer}",
        f"PO Number: {invoice.po_number}",
        f"Invoice Number: {invoice.invoice_number}",
        f"Invoice Total: {_format_cents(invoice.total_cents)}",
    ]


def _remittance_lines(case: LinkedBenchmarkCase) -> list[str]:
    assert case.payment and case.remittance
    refs = ", ".join(case.remittance.invoice_references)
    template = case.document_templates[1]
    lines = [
        f"Payment Reference: {case.payment.payment_reference}",
        f"Payment Date: {case.payment.payment_date}",
        f"Payment Mode: {case.payment.payment_mode}",
        f"Invoice Reference: {refs}",
        f"Payment Received: {_format_cents(case.payment.received_cents)}",
        f"Claimed Deduction: {_format_cents(case.remittance.claimed_deduction_cents)}",
        f"Deduction Reason: {case.remittance.claimed_reason}",
    ]
    if template == "payment_advice_table_v1":
        return ["Payment Advice", "Reference | Net Paid | Deduction"] + lines
    if template == "remittance_compact_v1":
        return [line.replace("Payment Reference", "Advice Number").replace("Payment Received", "Net Paid") for line in lines]
    return lines


def _promotion_lines(case: LinkedBenchmarkCase) -> list[str]:
    evidence = case.supporting_evidence[0]
    return [
        f"Promotion ID: {evidence.reference}",
        f"Retailer: {case.retailer}",
        f"Valid From: {evidence.valid_from}",
        f"Valid To: {evidence.valid_to}",
        f"Authorized Amount: {_format_cents(evidence.authorized_cents)}",
    ]


def _invoice(rng: random.Random, case_id: str, index: int) -> LinkedInvoice:
    bucket = rng.choice(INVOICE_AMOUNT_BUCKETS_CENTS)
    amount = _round_cents(rng.randint(bucket[0] // 100, bucket[1] // 100) * 100)
    return LinkedInvoice(
        invoice_number=f"INV-{case_id.upper()}-{index + 1}",
        invoice_date=(date(2026, 7, 1) + timedelta(days=rng.randint(0, 28))).isoformat(),
        po_number=f"PO-{rng.randint(1000, 9999)}",
        total_cents=amount,
    )


def _split_for_ordinal(ordinal: int) -> str:
    if ordinal < 100:
        return "dev"
    if ordinal < 125:
        return "validation"
    return "held_out"


def _allocated_payment(invoice: LinkedInvoice, invoice_total: int, payment_received: int) -> int:
    if invoice_total == 0:
        return 0
    return min(invoice.total_cents, round(payment_received * invoice.total_cents / invoice_total))


def _round_cents(amount_cents: int) -> int:
    return int(amount_cents)


def _format_cents(amount_cents: int) -> str:
    dollars, cents = divmod(amount_cents, 100)
    return f"${dollars:,}.{cents:02d}"


def _stable_seed(seed: int, family: str, index: int) -> int:
    digest = hashlib.sha256(f"{LINKED_GENERATOR_VERSION}:{seed}:{family}:{index}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _manifest(root: Path, seed: int, cases: tuple[LinkedBenchmarkCase, ...], truth_path: Path, evidence_dir: Path) -> dict[str, object]:
    return {
        "generator_version": LINKED_GENERATOR_VERSION,
        "seed": seed,
        "dataset_kind": "generated_linked_financial",
        "case_count": len(cases),
        "truth_sha256": hashlib.sha256(truth_path.read_bytes()).hexdigest(),
        "truth_path": str(truth_path.relative_to(root).as_posix()),
        "evidence_path": str(evidence_dir.relative_to(root).as_posix()),
        "family_counts": {family: sum(1 for case in cases if case.family == family) for family in sorted({case.family for case in cases})},
        "split_counts": {split: sum(1 for case in cases if case.split == split) for split in ("dev", "validation", "held_out")},
        "external_raw_rows_stored": False,
        "external_raw_documents_redistributed": False,
    }


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    build = generate_linked_dataset(root)
    print(json.dumps(build.manifest, indent=2))


if __name__ == "__main__":
    main()
