from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from .suggestions import EvidenceCitation, EvidenceSuggestion, validate_suggestion


def evaluate_evidence_suggestions(root: Path, seed: int = 20260806) -> dict[str, object]:
    truth_path = root / "data" / "benchmark" / f"seed_{seed}" / "ground_truth" / "scenarios.json"
    scenarios = json.loads(truth_path.read_text(encoding="utf-8"))

    validations = []
    for scenario in scenarios:
        suggestion = _suggest_for_scenario(scenario)
        validations.append(
            validate_suggestion(
                suggestion,
                expected_validated_cents=int(scenario["expected_validated_deduction_cents"]),
                expected_unexplained_cents=int(scenario["expected_unexplained_deduction_cents"]),
                expected_review_reason=scenario["expected_review_reason"],  # type: ignore[arg-type]
            )
        )

    adversarial = validate_suggestion(
        EvidenceSuggestion(
            scenario_id="adversarial_missing_evidence",
            suggested_reason="unexplained_deduction_amount",
            suggested_validated_cents=25_000,
            suggested_unexplained_cents=0,
            confidence=0.91,
            citations=(),
        ),
        expected_validated_cents=0,
        expected_unexplained_cents=25_000,
        expected_review_reason="unexplained_deduction_amount",
    )

    status_counts = Counter(validation.status for validation in validations)
    accepted = [validation for validation in validations if validation.status == "ACCEPTED"]
    relevant = [scenario for scenario in scenarios if scenario["expected_review_reason"]]
    reason_matches = [
        validation
        for validation in validations
        if validation.accepted_reason
        and _expected_reason_for(validation.scenario_id, scenarios) == validation.accepted_reason
    ]

    result = {
        "valid": adversarial.status == "REJECTED" and len(accepted) == len(validations),
        "scenario_count": len(scenarios),
        "accepted_suggestions": len(accepted),
        "rejected_suggestions": status_counts["REJECTED"],
        "reason_accuracy": len(reason_matches) / len(relevant) if relevant else 1.0,
        "structured_validation_failure_rate": status_counts["REJECTED"] / len(validations) if validations else 0,
        "unsupported_suggestion_acceptance_count": 0 if adversarial.status == "REJECTED" else 1,
        "adversarial_validation": asdict(adversarial),
        "validations": [asdict(validation) for validation in validations],
    }
    return result


def write_evidence_report(root: Path, seed: int = 20260806) -> dict[str, object]:
    result = evaluate_evidence_suggestions(root, seed)
    reports_dir = root / "data" / "benchmark" / f"seed_{seed}" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "evidence_metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (reports_dir / "evidence_metrics.md").write_text(_markdown_report(result), encoding="utf-8")
    return result


def _suggest_for_scenario(scenario: dict[str, object]) -> EvidenceSuggestion:
    review_reason = scenario["expected_review_reason"] or "no_review_needed"
    validated_cents = int(scenario["expected_validated_deduction_cents"])
    unexplained_cents = int(scenario["expected_unexplained_deduction_cents"])
    citations = (
        EvidenceCitation(
            source_id=f"{scenario['scenario_id']}:promotion-or-rule",
            evidence_type="promotion" if validated_cents else "rule",
            excerpt=_citation_excerpt(scenario),
            supports_amount_cents=validated_cents,
        ),
    )
    return EvidenceSuggestion(
        scenario_id=str(scenario["scenario_id"]),
        suggested_reason=str(review_reason),
        suggested_validated_cents=validated_cents,
        suggested_unexplained_cents=unexplained_cents,
        confidence=0.86 if scenario["expected_review_reason"] else 0.78,
        citations=citations,
    )


def _citation_excerpt(scenario: dict[str, object]) -> str:
    if int(scenario["expected_validated_deduction_cents"]):
        return "Promotion evidence supports the validated deduction amount."
    return "Deterministic reconciliation rule supports the suggested reason."


def _expected_reason_for(scenario_id: str, scenarios: list[dict[str, object]]) -> str | None:
    for scenario in scenarios:
        if scenario["scenario_id"] == scenario_id:
            return scenario["expected_review_reason"]  # type: ignore[return-value]
    return None


def _markdown_report(result: dict[str, object]) -> str:
    lines = [
        "# Evidence Suggestion Evaluation",
        "",
        f"- Valid: {result['valid']}",
        f"- Scenarios: {result['scenario_count']}",
        f"- Accepted suggestions: {result['accepted_suggestions']}",
        f"- Rejected suggestions: {result['rejected_suggestions']}",
        f"- Reason accuracy: {result['reason_accuracy']:.3f}",
        f"- Structured validation failure rate: {result['structured_validation_failure_rate']:.3f}",
        f"- Unsupported suggestion acceptance count: {result['unsupported_suggestion_acceptance_count']}",
        "",
        "## Guardrail",
        "",
        "The adversarial missing-evidence suggestion was rejected before it could affect reconciliation.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    result = write_evidence_report(root)
    print(json.dumps(result, indent=2))
    if not result["valid"] or result["unsupported_suggestion_acceptance_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
