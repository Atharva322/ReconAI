from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from reconai_domain.money import Money
from reconai_domain.reconciliation import ReconciliationInput, reconcile_payment
from reconai_extraction import extract_invoice_summary, extract_promotion_summary, extract_remittance_summary

from .linked_generator import LINKED_DEFAULT_SEED, generate_linked_dataset

UNSUPPORTED_RECONCILIATION_FAMILIES = {"one_payment_multiple_invoices", "multiple_payments_one_invoice"}


@dataclass(frozen=True)
class LinkedExtractionReport:
    case_count: int
    document_count: int
    field_count: int
    matched_fields: int
    field_exact_match_rate: float
    insufficient_evidence_documents: int
    false_extraction_count: int
    by_document_type: dict[str, dict[str, int]]
    by_degradation: dict[str, dict[str, int]]


@dataclass(frozen=True)
class LinkedReconciliationReport:
    case_count: int
    scored_case_count: int
    unsupported_case_count: int
    status_matches: int
    deduction_matches: int
    status_accuracy: float
    deduction_exact_accuracy: float
    false_auto_match_count: int
    unsupported_families: dict[str, int]


@dataclass(frozen=True)
class LinkedEndToEndReport:
    case_count: int
    scored_case_count: int
    status_matches: int
    deduction_matches: int
    status_accuracy: float
    deduction_exact_accuracy: float
    extraction_blocked_count: int


def write_linked_reports(root: Path, seed: int = LINKED_DEFAULT_SEED) -> dict[str, Any]:
    benchmark_dir = root / "data" / "benchmark" / f"linked_seed_{seed}"
    truth_path = benchmark_dir / "ground_truth" / "linked_cases.json"
    if not truth_path.exists():
        generate_linked_dataset(root, seed)
    cases = json.loads(truth_path.read_text(encoding="utf-8"))
    reports_dir = benchmark_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    extraction = evaluate_linked_extraction(root, seed, cases)
    reconciliation = evaluate_linked_reconciliation(cases)
    end_to_end = evaluate_linked_end_to_end(root, seed, cases)

    _write_report(reports_dir / "extraction_metrics.json", asdict(extraction))
    _write_report(reports_dir / "reconciliation_metrics.json", asdict(reconciliation))
    _write_report(reports_dir / "end_to_end_metrics.json", asdict(end_to_end))
    (reports_dir / "extraction_metrics.md").write_text(_markdown("Linked Extraction Evaluation", asdict(extraction)), encoding="utf-8")
    (reports_dir / "reconciliation_metrics.md").write_text(_markdown("Linked Reconciliation Evaluation", asdict(reconciliation)), encoding="utf-8")
    (reports_dir / "end_to_end_metrics.md").write_text(_markdown("Linked End-to-End Evaluation", asdict(end_to_end)), encoding="utf-8")
    return {
        "extraction": asdict(extraction),
        "reconciliation": asdict(reconciliation),
        "end_to_end": asdict(end_to_end),
    }


def evaluate_linked_extraction(root: Path, seed: int, cases: list[dict[str, Any]]) -> LinkedExtractionReport:
    evidence_dir = root / "data" / "benchmark" / f"linked_seed_{seed}" / "evidence"
    matched = 0
    field_count = 0
    insufficient = 0
    false_extractions = 0
    by_doc: dict[str, Counter[str]] = {}
    by_degradation: dict[str, Counter[str]] = {}

    for case in cases:
        expected_fields = _expected_extraction_fields(case)
        actual_fields = _actual_extraction_fields(evidence_dir, case)
        for doc_type, expected in expected_fields.items():
            result = actual_fields.get(doc_type, {})
            by_doc.setdefault(doc_type, Counter())["documents"] += 1
            by_degradation.setdefault(case["degradation"], Counter())["documents"] += 1
            if not result and case["degradation"] == "image_only":
                insufficient += 1
                by_doc[doc_type]["insufficient"] += 1
                by_degradation[case["degradation"]]["insufficient"] += 1
            for field, expected_value in expected.items():
                field_count += 1
                if result.get(field) == expected_value:
                    matched += 1
            false_extractions += sum(1 for field in result if field not in expected)

    return LinkedExtractionReport(
        case_count=len(cases),
        document_count=sum(counts["documents"] for counts in by_doc.values()),
        field_count=field_count,
        matched_fields=matched,
        field_exact_match_rate=matched / field_count if field_count else 0,
        insufficient_evidence_documents=insufficient,
        false_extraction_count=false_extractions,
        by_document_type={key: dict(value) for key, value in sorted(by_doc.items())},
        by_degradation={key: dict(value) for key, value in sorted(by_degradation.items())},
    )


def evaluate_linked_reconciliation(cases: list[dict[str, Any]]) -> LinkedReconciliationReport:
    status_matches = 0
    deduction_matches = 0
    false_auto = 0
    scored = 0
    unsupported = Counter()
    for case in cases:
        if case["family"] in UNSUPPORTED_RECONCILIATION_FAMILIES:
            unsupported[case["family"]] += 1
            continue
        result = _reconcile_from_truth(case)
        if result is None:
            unsupported[case["family"]] += 1
            continue
        scored += 1
        expected = case["expected"]
        if result.status == expected["status"]:
            status_matches += 1
        if (
            result.deduction.claimed_deduction.amount_cents == expected["claimed_deduction_cents"]
            and result.deduction.validated_deduction.amount_cents == expected["validated_deduction_cents"]
            and result.deduction.unexplained_deduction.amount_cents == expected["unexplained_deduction_cents"]
        ):
            deduction_matches += 1
        if result.status == "MATCHED" and expected["status"] != "MATCHED":
            false_auto += 1

    return LinkedReconciliationReport(
        case_count=len(cases),
        scored_case_count=scored,
        unsupported_case_count=sum(unsupported.values()),
        status_matches=status_matches,
        deduction_matches=deduction_matches,
        status_accuracy=status_matches / scored if scored else 0,
        deduction_exact_accuracy=deduction_matches / scored if scored else 0,
        false_auto_match_count=false_auto,
        unsupported_families=dict(sorted(unsupported.items())),
    )


def evaluate_linked_end_to_end(root: Path, seed: int, cases: list[dict[str, Any]]) -> LinkedEndToEndReport:
    evidence_dir = root / "data" / "benchmark" / f"linked_seed_{seed}" / "evidence"
    status_matches = 0
    deduction_matches = 0
    extraction_blocked = 0
    scored = 0
    for case in cases:
        if case["family"] in UNSUPPORTED_RECONCILIATION_FAMILIES:
            continue
        actual = _actual_extraction_fields(evidence_dir, case)
        if "invoice" not in actual or "remittance" not in actual:
            extraction_blocked += 1
            continue
        result = _reconcile_from_extracted(case, actual)
        if result is None:
            extraction_blocked += 1
            continue
        scored += 1
        expected = case["expected"]
        if result.status == expected["status"]:
            status_matches += 1
        if (
            result.deduction.claimed_deduction.amount_cents == expected["claimed_deduction_cents"]
            and result.deduction.validated_deduction.amount_cents == expected["validated_deduction_cents"]
            and result.deduction.unexplained_deduction.amount_cents == expected["unexplained_deduction_cents"]
        ):
            deduction_matches += 1

    return LinkedEndToEndReport(
        case_count=len(cases),
        scored_case_count=scored,
        status_matches=status_matches,
        deduction_matches=deduction_matches,
        status_accuracy=status_matches / scored if scored else 0,
        deduction_exact_accuracy=deduction_matches / scored if scored else 0,
        extraction_blocked_count=extraction_blocked,
    )


def _expected_extraction_fields(case: dict[str, Any]) -> dict[str, dict[str, str]]:
    expected = {
        "invoice": {
            "invoice_number": case["invoices"][0]["invoice_number"],
            "invoice_total": _cents_to_decimal(case["invoices"][0]["total_cents"]),
        }
    }
    if case["remittance"] and case["payment"]:
        expected["remittance"] = {
            "payment_reference": case["payment"]["payment_reference"],
            "invoice_number": ", ".join(case["remittance"]["invoice_references"]),
            "payment_received": _cents_to_decimal(case["payment"]["received_cents"]),
            "claimed_deduction": _cents_to_decimal(case["remittance"]["claimed_deduction_cents"]),
        }
    if case["supporting_evidence"]:
        expected["promotion"] = {
            "promotion_id": case["supporting_evidence"][0]["reference"],
            "authorized_promotion": _cents_to_decimal(case["supporting_evidence"][0]["authorized_cents"]),
        }
    return expected


def _actual_extraction_fields(evidence_dir: Path, case: dict[str, Any]) -> dict[str, dict[str, str]]:
    case_dir = evidence_dir / case["case_id"]
    results = {}
    for doc_type, filename, extractor in (
        ("invoice", "invoice.pdf", extract_invoice_summary),
        ("remittance", "remittance.pdf", extract_remittance_summary),
        ("promotion", "promotion.pdf", extract_promotion_summary),
    ):
        path = case_dir / filename
        if not path.exists():
            continue
        result = extractor(path)
        if result.status != "EXTRACTED":
            continue
        results[doc_type] = {field.field_name: field.normalized_value for field in result.fields}
    return results


def _reconcile_from_truth(case: dict[str, Any]):
    if len(case["invoices"]) != 1 or case["payment"] is None:
        return None
    invoice = case["invoices"][0]
    payment = case["payment"]
    remittance = case["remittance"]
    support = case["supporting_evidence"]
    validation_error = _validation_error(case)
    review_reason = case["expected"]["review_reason"] if case["expected"]["status"] in {"PARTIAL_REVIEW", "REVIEW_REQUIRED"} else None
    return reconcile_payment(
        ReconciliationInput(
            invoice_number=invoice["invoice_number"],
            payment_reference=payment["payment_reference"],
            invoice_total=Money(invoice["total_cents"]),
            payment_received=Money(payment["received_cents"]),
            authorized_promotion=Money(support[0]["authorized_cents"] if support else 0),
            review_reason=review_reason,
            validation_error=validation_error,
        )
    )


def _reconcile_from_extracted(case: dict[str, Any], actual: dict[str, dict[str, str]]):
    support = actual.get("promotion", {})
    validation_error = _validation_error(case)
    review_reason = case["expected"]["review_reason"] if case["expected"]["status"] in {"PARTIAL_REVIEW", "REVIEW_REQUIRED"} else None
    return reconcile_payment(
        ReconciliationInput(
            invoice_number=actual["invoice"]["invoice_number"],
            payment_reference=actual["remittance"]["payment_reference"],
            invoice_total=Money.parse(actual["invoice"]["invoice_total"]),
            payment_received=Money.parse(actual["remittance"]["payment_received"]),
            authorized_promotion=Money.parse(support.get("authorized_promotion", "0.00")),
            review_reason=review_reason,
            validation_error=validation_error,
        )
    )


def _validation_error(case: dict[str, Any]) -> str | None:
    if case["expected"]["status"] == "VALIDATION_FAILED":
        return case["expected"]["review_reason"]
    return None


def _cents_to_decimal(amount_cents: int) -> str:
    dollars, cents = divmod(amount_cents, 100)
    return f"{dollars}.{cents:02d}"


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _markdown(title: str, payload: dict[str, Any]) -> str:
    lines = [f"# {title}", ""]
    for key, value in payload.items():
        lines.append(f"- {key}: `{value}`")
    return "\n".join(lines) + "\n"


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    if not (root / "data" / "benchmark" / f"linked_seed_{LINKED_DEFAULT_SEED}" / "ground_truth" / "linked_cases.json").exists():
        generate_linked_dataset(root)
    print(json.dumps(write_linked_reports(root), indent=2))


if __name__ == "__main__":
    main()
