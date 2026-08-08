from __future__ import annotations

import json
from pathlib import Path

from reconai_benchmark.linked_evaluate import write_linked_reports
from reconai_benchmark.linked_generator import LINKED_DEFAULT_SEED, build_linked_cases, generate_linked_dataset
from reconai_benchmark.linked_validate import validate_linked_dataset
from reconai_benchmark.profiles import FAMILY_COUNTS


def test_linked_generator_is_deterministic() -> None:
    first = [case.to_json() for case in build_linked_cases(LINKED_DEFAULT_SEED)]
    second = [case.to_json() for case in build_linked_cases(LINKED_DEFAULT_SEED)]

    assert first == second


def test_linked_generator_family_counts_and_splits() -> None:
    cases = build_linked_cases(LINKED_DEFAULT_SEED)
    family_counts = {family: sum(1 for case in cases if case.family == family) for family in FAMILY_COUNTS}
    split_counts = {split: sum(1 for case in cases if case.split == split) for split in ("dev", "validation", "held_out")}

    assert len(cases) == 150
    assert family_counts == FAMILY_COUNTS
    assert split_counts == {"dev": 100, "validation": 25, "held_out": 25}


def test_linked_dataset_validates_and_has_no_answer_leakage(tmp_path: Path) -> None:
    generate_linked_dataset(tmp_path, LINKED_DEFAULT_SEED)
    result = validate_linked_dataset(tmp_path, LINKED_DEFAULT_SEED)

    assert result["valid"] is True
    assert result["errors"] == []
    assert result["case_count"] == 150


def test_linked_promotion_overclaim_uses_independent_promotion_evidence(tmp_path: Path) -> None:
    generate_linked_dataset(tmp_path, LINKED_DEFAULT_SEED)
    truth_path = tmp_path / "data" / "benchmark" / f"linked_seed_{LINKED_DEFAULT_SEED}" / "ground_truth" / "linked_cases.json"
    cases = json.loads(truth_path.read_text(encoding="utf-8"))
    overclaim = next(case for case in cases if case["family"] == "promotion_overclaim")
    case_dir = tmp_path / "data" / "benchmark" / f"linked_seed_{LINKED_DEFAULT_SEED}" / "evidence" / overclaim["case_id"]

    remittance_text = (case_dir / "remittance.pdf").read_bytes().decode("latin-1", errors="ignore")
    promotion_text = (case_dir / "promotion.pdf").read_bytes().decode("latin-1", errors="ignore")

    assert "Claimed Deduction" in remittance_text
    assert "Authorized Amount" not in remittance_text
    assert "Authorized Amount" in promotion_text
    assert "Expected Status" not in remittance_text


def test_linked_partial_payment_states_no_customer_deduction(tmp_path: Path) -> None:
    build = generate_linked_dataset(tmp_path, LINKED_DEFAULT_SEED)
    partial = next(case for case in build.cases if case.family == "partial_payment")

    assert partial.payment is not None
    assert partial.remittance is not None
    assert partial.invoices[0].total_cents > partial.payment.received_cents
    assert partial.remittance.claimed_deduction_cents == 0
    assert partial.expected.open_balance_cents == partial.invoices[0].total_cents - partial.payment.received_cents
    assert partial.expected.review_reason == "partial_payment_open_balance"
    assert partial.supporting_evidence == ()

    remittance_text = (
        tmp_path
        / "data"
        / "benchmark"
        / f"linked_seed_{LINKED_DEFAULT_SEED}"
        / "evidence"
        / partial.case_id
        / "remittance.pdf"
    ).read_bytes().decode("latin-1", errors="ignore")
    assert "Claimed Deduction: $0.00" in remittance_text


def test_linked_reports_are_written_and_mark_unsupported_cardinality(tmp_path: Path) -> None:
    generate_linked_dataset(tmp_path, LINKED_DEFAULT_SEED)
    reports = write_linked_reports(tmp_path, LINKED_DEFAULT_SEED)

    report_dir = tmp_path / "data" / "benchmark" / f"linked_seed_{LINKED_DEFAULT_SEED}" / "reports"
    assert (report_dir / "extraction_metrics.json").exists()
    assert (report_dir / "reconciliation_metrics.json").exists()
    assert (report_dir / "end_to_end_metrics.json").exists()
    assert reports["reconciliation"]["case_count"] == 150
    assert reports["reconciliation"]["unsupported_families"] == {
        "missing_remittance": 10,
        "multiple_payments_one_invoice": 10,
        "one_payment_multiple_invoices": 10,
    }
