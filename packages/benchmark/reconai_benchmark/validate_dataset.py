from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reconai_benchmark.generator import DEFAULT_SEED, generate_dataset
from reconai_benchmark.scenarios import SCENARIO_FAMILIES


def validate_dataset(root: Path, seed: int = DEFAULT_SEED) -> dict[str, object]:
    benchmark_dir = root / "data" / "benchmark" / f"seed_{seed}"
    truth_path = benchmark_dir / "ground_truth" / "scenarios.json"
    manifest_path = benchmark_dir / "manifest.json"

    if not truth_path.exists() or not manifest_path.exists():
        generate_dataset(root, seed)

    scenarios = json.loads(truth_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    errors: list[str] = []
    family_counts = Counter(scenario["family_id"] for scenario in scenarios)
    split_counts = Counter(scenario["split"] for scenario in scenarios)

    missing_families = sorted(set(SCENARIO_FAMILIES) - set(family_counts))
    if missing_families:
        errors.append(f"missing scenario families: {', '.join(missing_families)}")

    for scenario in scenarios:
        scenario_id = scenario["scenario_id"]
        claimed = scenario["invoice_total_cents"] - scenario["payment_received_cents"]
        validated = min(max(claimed, 0), scenario["authorized_promotion_cents"])
        unexplained = max(claimed - validated, 0)
        if scenario["expected_claimed_deduction_cents"] != claimed:
            errors.append(f"{scenario_id}: claimed deduction arithmetic mismatch")
        if scenario["expected_validated_deduction_cents"] != validated:
            errors.append(f"{scenario_id}: validated deduction arithmetic mismatch")
        if scenario["expected_unexplained_deduction_cents"] != unexplained:
            errors.append(f"{scenario_id}: unexplained deduction arithmetic mismatch")
        if scenario["expected_status"] != "MATCHED" and not scenario["expected_review_reason"]:
            errors.append(f"{scenario_id}: non-matched scenario missing review reason")

    if manifest["scenario_count"] != len(scenarios):
        errors.append("manifest scenario_count does not match truth file")

    return {
        "valid": not errors,
        "errors": errors,
        "scenario_count": len(scenarios),
        "family_counts": dict(sorted(family_counts.items())),
        "split_counts": dict(sorted(split_counts.items())),
        "manifest": manifest,
    }


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    result = validate_dataset(root)
    print(json.dumps(result, indent=2))
    if not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
