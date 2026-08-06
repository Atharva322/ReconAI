from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from .contracts import ExtractionResult
from .pdf_text import extract_invoice_summary, extract_remittance_summary


@dataclass(frozen=True)
class FieldScore:
    scenario_id: str
    document_type: str
    field_name: str
    expected: str
    actual: str | None
    matched: bool


@dataclass(frozen=True)
class ExtractionEvaluation:
    scenario_count: int
    field_count: int
    matched_fields: int
    field_exact_match_rate: float
    review_required_count: int
    status_counts: dict[str, int]
    field_scores: tuple[FieldScore, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "scenario_count": self.scenario_count,
            "field_count": self.field_count,
            "matched_fields": self.matched_fields,
            "field_exact_match_rate": self.field_exact_match_rate,
            "review_required_count": self.review_required_count,
            "status_counts": self.status_counts,
            "field_scores": [asdict(score) for score in self.field_scores],
        }


def evaluate_benchmark_extraction(root: Path, seed: int = 20260806) -> ExtractionEvaluation:
    benchmark_dir = root / "data" / "benchmark" / f"seed_{seed}"
    scenarios = json.loads((benchmark_dir / "ground_truth" / "scenarios.json").read_text(encoding="utf-8"))
    evidence_dir = benchmark_dir / "evidence"

    field_scores: list[FieldScore] = []
    status_counts: Counter[str] = Counter()
    review_required = 0

    for scenario in scenarios:
        scenario_id = scenario["scenario_id"]
        invoice_result = extract_invoice_summary(evidence_dir / scenario_id / "invoice.pdf")
        remittance_result = extract_remittance_summary(evidence_dir / scenario_id / "remittance.pdf")

        for result in (invoice_result, remittance_result):
            status_counts[f"{result.document_type}:{result.status}"] += 1
            if result.requires_review:
                review_required += 1

        field_scores.extend(_score_invoice_fields(scenario, invoice_result))
        field_scores.extend(_score_remittance_fields(scenario, remittance_result))

    matched = sum(1 for score in field_scores if score.matched)
    field_count = len(field_scores)
    return ExtractionEvaluation(
        scenario_count=len(scenarios),
        field_count=field_count,
        matched_fields=matched,
        field_exact_match_rate=matched / field_count if field_count else 0,
        review_required_count=review_required,
        status_counts=dict(sorted(status_counts.items())),
        field_scores=tuple(field_scores),
    )


def write_evaluation_report(root: Path, seed: int = 20260806) -> ExtractionEvaluation:
    evaluation = evaluate_benchmark_extraction(root, seed)
    reports_dir = root / "data" / "benchmark" / f"seed_{seed}" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "extraction_metrics.json").write_text(
        json.dumps(evaluation.to_json(), indent=2) + "\n",
        encoding="utf-8",
    )
    (reports_dir / "extraction_metrics.md").write_text(_markdown_report(evaluation), encoding="utf-8")
    return evaluation


def _score_invoice_fields(scenario: dict[str, object], result: ExtractionResult) -> list[FieldScore]:
    actual = _field_map(result)
    expected = {
        "invoice_number": str(scenario["invoice_number"]),
        "invoice_total": _cents_to_decimal_string(int(scenario["invoice_total_cents"])),
    }
    return [_field_score(str(scenario["scenario_id"]), "invoice", field, value, actual) for field, value in expected.items()]


def _score_remittance_fields(scenario: dict[str, object], result: ExtractionResult) -> list[FieldScore]:
    actual = _field_map(result)
    expected = {
        "payment_reference": str(scenario["payment_reference"]),
        "invoice_number": str(scenario["invoice_number"]),
        "payment_received": _cents_to_decimal_string(int(scenario["payment_received_cents"])),
        "authorized_promotion": _cents_to_decimal_string(int(scenario["authorized_promotion_cents"])),
    }
    return [
        _field_score(str(scenario["scenario_id"]), "remittance", field, value, actual)
        for field, value in expected.items()
    ]


def _field_score(
    scenario_id: str,
    document_type: str,
    field_name: str,
    expected: str,
    actual: dict[str, str],
) -> FieldScore:
    actual_value = actual.get(field_name)
    return FieldScore(
        scenario_id=scenario_id,
        document_type=document_type,
        field_name=field_name,
        expected=expected,
        actual=actual_value,
        matched=actual_value == expected,
    )


def _field_map(result: ExtractionResult) -> dict[str, str]:
    return {field.field_name: field.normalized_value for field in result.fields}


def _cents_to_decimal_string(amount_cents: int) -> str:
    return f"{amount_cents / 100:.2f}"


def _markdown_report(evaluation: ExtractionEvaluation) -> str:
    misses_by_scenario: dict[str, list[FieldScore]] = defaultdict(list)
    for score in evaluation.field_scores:
        if not score.matched:
            misses_by_scenario[score.scenario_id].append(score)

    lines = [
        "# Extraction Evaluation",
        "",
        f"- Scenarios: {evaluation.scenario_count}",
        f"- Fields scored: {evaluation.field_count}",
        f"- Matched fields: {evaluation.matched_fields}",
        f"- Field exact match rate: {evaluation.field_exact_match_rate:.3f}",
        f"- Documents requiring review: {evaluation.review_required_count}",
        "",
        "## Status Counts",
        "",
    ]
    for status, count in evaluation.status_counts.items():
        lines.append(f"- `{status}`: {count}")

    lines.extend(["", "## Misses", ""])
    if not misses_by_scenario:
        lines.append("No field misses.")
    else:
        for scenario_id, misses in sorted(misses_by_scenario.items()):
            lines.append(f"### {scenario_id}")
            for miss in misses:
                lines.append(
                    f"- `{miss.document_type}.{miss.field_name}` expected `{miss.expected}`, got `{miss.actual}`"
                )

    return "\n".join(lines) + "\n"


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    evaluation = write_evaluation_report(root)
    print(json.dumps(evaluation.to_json(), indent=2))
    if evaluation.field_exact_match_rate < 0.90:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
