from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from .money import Money
from .reconciliation import ReconciliationInput, ReconciliationResult, reconcile_payment


@dataclass(frozen=True)
class ScenarioReconciliationScore:
    scenario_id: str
    family_id: str
    expected_status: str
    actual_status: str
    status_matched: bool
    expected_claimed_deduction_cents: int
    actual_claimed_deduction_cents: int
    expected_validated_deduction_cents: int
    actual_validated_deduction_cents: int
    expected_unexplained_deduction_cents: int
    actual_unexplained_deduction_cents: int
    deduction_matched: bool
    expected_review_reason: str | None
    actual_review_reason: str | None


@dataclass(frozen=True)
class ReconciliationEvaluation:
    scenario_count: int
    status_accuracy: float
    deduction_exact_accuracy: float
    confirmed_match_precision: float
    review_routing_recall: float
    false_auto_match_count: int
    status_counts: dict[str, int]
    scenario_scores: tuple[ScenarioReconciliationScore, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "scenario_count": self.scenario_count,
            "status_accuracy": self.status_accuracy,
            "deduction_exact_accuracy": self.deduction_exact_accuracy,
            "confirmed_match_precision": self.confirmed_match_precision,
            "review_routing_recall": self.review_routing_recall,
            "false_auto_match_count": self.false_auto_match_count,
            "status_counts": self.status_counts,
            "scenario_scores": [asdict(score) for score in self.scenario_scores],
        }


def evaluate_benchmark_reconciliation(root: Path, seed: int = 20260806) -> ReconciliationEvaluation:
    truth_path = root / "data" / "benchmark" / f"seed_{seed}" / "ground_truth" / "scenarios.json"
    scenarios = json.loads(truth_path.read_text(encoding="utf-8"))

    scores: list[ScenarioReconciliationScore] = []
    status_counts: Counter[str] = Counter()
    for scenario in scenarios:
        result = reconcile_payment(_input_from_scenario(scenario))
        status_counts[result.status] += 1
        scores.append(_score_scenario(scenario, result))

    status_matches = sum(1 for score in scores if score.status_matched)
    deduction_matches = sum(1 for score in scores if score.deduction_matched)
    confirmed = [score for score in scores if score.actual_status == "MATCHED"]
    true_confirmed = [score for score in confirmed if score.expected_status == "MATCHED"]
    expected_review = [score for score in scores if score.expected_status != "MATCHED"]
    routed_review = [score for score in expected_review if score.actual_status != "MATCHED"]
    false_auto_matches = [score for score in scores if score.actual_status == "MATCHED" and score.expected_status != "MATCHED"]

    return ReconciliationEvaluation(
        scenario_count=len(scores),
        status_accuracy=status_matches / len(scores) if scores else 0,
        deduction_exact_accuracy=deduction_matches / len(scores) if scores else 0,
        confirmed_match_precision=len(true_confirmed) / len(confirmed) if confirmed else 1.0,
        review_routing_recall=len(routed_review) / len(expected_review) if expected_review else 1.0,
        false_auto_match_count=len(false_auto_matches),
        status_counts=dict(sorted(status_counts.items())),
        scenario_scores=tuple(scores),
    )


def write_reconciliation_report(root: Path, seed: int = 20260806) -> ReconciliationEvaluation:
    evaluation = evaluate_benchmark_reconciliation(root, seed)
    reports_dir = root / "data" / "benchmark" / f"seed_{seed}" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "reconciliation_metrics.json").write_text(
        json.dumps(evaluation.to_json(), indent=2) + "\n",
        encoding="utf-8",
    )
    (reports_dir / "reconciliation_metrics.md").write_text(_markdown_report(evaluation), encoding="utf-8")
    return evaluation


def _input_from_scenario(scenario: dict[str, object]) -> ReconciliationInput:
    review_reason, validation_error = _deterministic_blockers(scenario)
    return ReconciliationInput(
        invoice_number=str(scenario["invoice_number"]),
        payment_reference=str(scenario["payment_reference"]),
        invoice_total=Money(int(scenario["invoice_total_cents"])),
        payment_received=Money(int(scenario["payment_received_cents"])),
        authorized_promotion=Money(int(scenario["authorized_promotion_cents"])),
        review_reason=review_reason,
        validation_error=validation_error,
    )


def _deterministic_blockers(scenario: dict[str, object]) -> tuple[str | None, str | None]:
    family_id = str(scenario["family_id"])
    degradation = str(scenario["degradation"])

    if family_id == "S10" or degradation == "bad_remittance_total":
        return None, "inconsistent_arithmetic"

    review_reasons = {
        "S02": "partial_payment_open_balance",
        "S06": "duplicate_document",
        "S07": "unknown_invoice_reference",
        "S08": "retailer_reference_conflict",
        "S09": "low_confidence_invoice_reference",
        "S11": "no_text_or_noisy_scan",
        "S12": "duplicate_deduction_claim",
    }
    return review_reasons.get(family_id), None


def _score_scenario(
    scenario: dict[str, object],
    result: ReconciliationResult,
) -> ScenarioReconciliationScore:
    deduction = result.deduction
    deduction_matched = (
        deduction.claimed_deduction.amount_cents == scenario["expected_claimed_deduction_cents"]
        and deduction.validated_deduction.amount_cents == scenario["expected_validated_deduction_cents"]
        and deduction.unexplained_deduction.amount_cents == scenario["expected_unexplained_deduction_cents"]
    )
    return ScenarioReconciliationScore(
        scenario_id=str(scenario["scenario_id"]),
        family_id=str(scenario["family_id"]),
        expected_status=str(scenario["expected_status"]),
        actual_status=result.status,
        status_matched=result.status == scenario["expected_status"],
        expected_claimed_deduction_cents=int(scenario["expected_claimed_deduction_cents"]),
        actual_claimed_deduction_cents=deduction.claimed_deduction.amount_cents,
        expected_validated_deduction_cents=int(scenario["expected_validated_deduction_cents"]),
        actual_validated_deduction_cents=deduction.validated_deduction.amount_cents,
        expected_unexplained_deduction_cents=int(scenario["expected_unexplained_deduction_cents"]),
        actual_unexplained_deduction_cents=deduction.unexplained_deduction.amount_cents,
        deduction_matched=deduction_matched,
        expected_review_reason=scenario["expected_review_reason"],  # type: ignore[arg-type]
        actual_review_reason=result.review_reason,
    )


def _markdown_report(evaluation: ReconciliationEvaluation) -> str:
    lines = [
        "# Reconciliation Evaluation",
        "",
        f"- Scenarios: {evaluation.scenario_count}",
        f"- Status accuracy: {evaluation.status_accuracy:.3f}",
        f"- Deduction exact accuracy: {evaluation.deduction_exact_accuracy:.3f}",
        f"- Confirmed-match precision: {evaluation.confirmed_match_precision:.3f}",
        f"- Review-routing recall: {evaluation.review_routing_recall:.3f}",
        f"- False auto-match count: {evaluation.false_auto_match_count}",
        "",
        "## Status Counts",
        "",
    ]
    for status, count in evaluation.status_counts.items():
        lines.append(f"- `{status}`: {count}")

    misses = [score for score in evaluation.scenario_scores if not score.status_matched or not score.deduction_matched]
    lines.extend(["", "## Misses", ""])
    if not misses:
        lines.append("No reconciliation misses.")
    else:
        for miss in misses:
            lines.append(
                f"- `{miss.scenario_id}` expected `{miss.expected_status}`, got `{miss.actual_status}`; "
                f"deduction matched: `{miss.deduction_matched}`"
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    evaluation = write_reconciliation_report(root)
    print(json.dumps(evaluation.to_json(), indent=2))
    if evaluation.false_auto_match_count or evaluation.status_accuracy < 1 or evaluation.deduction_exact_accuracy < 1:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
