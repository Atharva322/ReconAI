from pathlib import Path

from reconai_benchmark.generator import DEFAULT_SEED, generate_dataset
from reconai_extraction.evaluate import evaluate_benchmark_extraction, write_evaluation_report


def test_benchmark_extraction_evaluation_scores_expected_fields(tmp_path: Path) -> None:
    generate_dataset(tmp_path, DEFAULT_SEED)

    evaluation = evaluate_benchmark_extraction(tmp_path, DEFAULT_SEED)

    assert evaluation.scenario_count == 12
    assert evaluation.field_count == 72
    assert evaluation.matched_fields == 66
    assert evaluation.field_exact_match_rate == 66 / 72
    assert evaluation.review_required_count == 2
    assert evaluation.status_counts["invoice:INSUFFICIENT_EVIDENCE"] == 1
    assert evaluation.status_counts["remittance:INSUFFICIENT_EVIDENCE"] == 1


def test_benchmark_extraction_report_is_written(tmp_path: Path) -> None:
    generate_dataset(tmp_path, DEFAULT_SEED)

    write_evaluation_report(tmp_path, DEFAULT_SEED)

    assert (tmp_path / "data" / "benchmark" / "seed_20260806" / "reports" / "extraction_metrics.json").exists()
    assert (tmp_path / "data" / "benchmark" / "seed_20260806" / "reports" / "extraction_metrics.md").exists()
