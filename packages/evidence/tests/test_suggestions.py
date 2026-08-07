from pathlib import Path

from reconai_evidence.evaluate import evaluate_evidence_suggestions, write_evidence_report
from reconai_evidence.suggestions import EvidenceSuggestion, validate_suggestion


def test_missing_citation_suggestion_is_rejected() -> None:
    validation = validate_suggestion(
        EvidenceSuggestion(
            scenario_id="case-1",
            suggested_reason="unexplained_deduction_amount",
            suggested_validated_cents=0,
            suggested_unexplained_cents=25_000,
            confidence=0.9,
            citations=(),
        ),
        expected_validated_cents=0,
        expected_unexplained_cents=25_000,
        expected_review_reason="unexplained_deduction_amount",
    )

    assert validation.status == "REJECTED"
    assert validation.rejection_reason == "missing_citation"


def test_phase7_evidence_evaluation_is_valid() -> None:
    result = evaluate_evidence_suggestions(Path.cwd())

    assert result["valid"] is True
    assert result["accepted_suggestions"] == 12
    assert result["unsupported_suggestion_acceptance_count"] == 0


def test_phase7_evidence_report_is_written(tmp_path: Path) -> None:
    source_root = Path.cwd()
    target_truth = tmp_path / "data" / "benchmark" / "seed_20260806" / "ground_truth"
    target_truth.mkdir(parents=True)
    (target_truth / "scenarios.json").write_text(
        (source_root / "data" / "benchmark" / "seed_20260806" / "ground_truth" / "scenarios.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )

    write_evidence_report(tmp_path)

    assert (tmp_path / "data" / "benchmark" / "seed_20260806" / "reports" / "evidence_metrics.json").exists()
    assert (tmp_path / "data" / "benchmark" / "seed_20260806" / "reports" / "evidence_metrics.md").exists()
