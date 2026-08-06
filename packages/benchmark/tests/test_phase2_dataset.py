from pathlib import Path

from reconai_benchmark.generator import DEFAULT_SEED, build_scenarios, generate_dataset
from reconai_benchmark.scenarios import SCENARIO_FAMILIES
from reconai_benchmark.validate_dataset import validate_dataset


def test_phase2_generator_is_deterministic() -> None:
    first = [scenario.to_json() for scenario in build_scenarios(DEFAULT_SEED)]
    second = [scenario.to_json() for scenario in build_scenarios(DEFAULT_SEED)]

    assert first == second


def test_phase2_dataset_covers_required_families() -> None:
    family_ids = {scenario.family_id for scenario in build_scenarios(DEFAULT_SEED)}

    assert family_ids == set(SCENARIO_FAMILIES)


def test_phase2_dataset_validates_generated_truth(tmp_path: Path) -> None:
    generate_dataset(tmp_path, DEFAULT_SEED)
    result = validate_dataset(tmp_path, DEFAULT_SEED)

    assert result["valid"] is True
    assert result["scenario_count"] == 12
    assert result["split_counts"] == {"dev": 3, "eval": 8, "golden_demo": 1}
