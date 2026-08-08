from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .linked_generator import LINKED_DEFAULT_SEED, generate_linked_dataset
from .profiles import FAMILY_COUNTS

LEAKAGE_TOKENS = (
    "Expected Status",
    "expected_review_reason",
    "expected_unexplained",
    "REVIEW_REQUIRED",
    "MATCHED",
    "PARTIAL_REVIEW",
    "VALIDATION_FAILED",
)


def validate_linked_dataset(root: Path, seed: int = LINKED_DEFAULT_SEED) -> dict[str, object]:
    benchmark_dir = root / "data" / "benchmark" / f"linked_seed_{seed}"
    truth_path = benchmark_dir / "ground_truth" / "linked_cases.json"
    manifest_path = benchmark_dir / "manifest.json"
    if not truth_path.exists() or not manifest_path.exists():
        generate_linked_dataset(root, seed)

    cases = json.loads(truth_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    family_counts = Counter(case["family"] for case in cases)
    split_counts = Counter(case["split"] for case in cases)

    if dict(sorted(family_counts.items())) != dict(sorted(FAMILY_COUNTS.items())):
        errors.append("family counts do not match linked benchmark profile")
    if split_counts != {"dev": 100, "held_out": 25, "validation": 25}:
        errors.append(f"unexpected split counts: {dict(split_counts)}")

    ids = [case["case_id"] for case in cases]
    if len(ids) != len(set(ids)):
        errors.append("case IDs are not unique")

    for case in cases:
        expected = case["expected"]
        invoice_total = sum(invoice["total_cents"] for invoice in case["invoices"])
        applied_cash = sum(allocation["applied_payment_cents"] for allocation in expected["invoice_allocations"])
        open_balance = max(invoice_total - applied_cash, 0)
        if expected["open_balance_cents"] != open_balance:
            errors.append(f"{case['case_id']}: open balance mismatch")
        if case["remittance"] and expected["claimed_deduction_cents"] != case["remittance"]["claimed_deduction_cents"]:
            errors.append(f"{case['case_id']}: stated deduction mismatch")
        if expected["validated_deduction_cents"] > expected["claimed_deduction_cents"]:
            errors.append(f"{case['case_id']}: validated deduction exceeds claim")
        if expected["unexplained_deduction_cents"] != expected["claimed_deduction_cents"] - expected["validated_deduction_cents"]:
            errors.append(f"{case['case_id']}: unexplained deduction mismatch")

    leakage = _find_leakage(benchmark_dir / "evidence")
    errors.extend(leakage)
    if manifest["case_count"] != len(cases):
        errors.append("manifest case_count does not match truth")

    return {
        "valid": not errors,
        "errors": errors,
        "case_count": len(cases),
        "family_counts": dict(sorted(family_counts.items())),
        "split_counts": dict(sorted(split_counts.items())),
        "manifest": manifest,
    }


def _find_leakage(evidence_dir: Path) -> list[str]:
    errors: list[str] = []
    for path in evidence_dir.rglob("*.pdf"):
        data = path.read_bytes().decode("latin-1", errors="ignore")
        for token in LEAKAGE_TOKENS:
            if token in data:
                errors.append(f"{path}: leaked benchmark token {token!r}")
    return errors


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    result = validate_linked_dataset(root)
    print(json.dumps(result, indent=2))
    if not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
