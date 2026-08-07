from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .pdf_renderer import render_blank_pdf, render_text_pdf
from .scenarios import BenchmarkScenario, DatasetSplit, SCENARIO_FAMILIES

GENERATOR_VERSION = "phase2.benchmark.v1"
DEFAULT_SEED = 20260806


@dataclass(frozen=True)
class DatasetBuild:
    scenarios: tuple[BenchmarkScenario, ...]
    manifest: dict[str, object]


def build_scenarios(seed: int = DEFAULT_SEED) -> tuple[BenchmarkScenario, ...]:
    rng = random.Random(seed)
    scenarios = [
        _scenario(
            rng,
            seed,
            "S01",
            "dev",
            invoice_total=12_500_00,
            payment_received=12_500_00,
            authorized_promotion=0,
            expected_status="MATCHED",
            review_reason=None,
            degradation="digital_text",
            notes="Exact reference and exact amount.",
        ),
        _scenario(
            rng,
            seed,
            "S02",
            "dev",
            invoice_total=8_000_00,
            payment_received=6_000_00,
            authorized_promotion=0,
            expected_status="PARTIAL_REVIEW",
            review_reason="partial_payment_open_balance",
            degradation="digital_text",
            notes="Explicit partial payment leaves open balance.",
        ),
        _scenario(
            rng,
            seed,
            "S03",
            "dev",
            invoice_total=5_500_00,
            payment_received=5_000_00,
            authorized_promotion=500_00,
            expected_status="MATCHED",
            review_reason=None,
            degradation="digital_text",
            notes="Promotion fully validates the deduction.",
        ),
        _scenario(
            rng,
            seed,
            "S04",
            "golden_demo",
            invoice_total=18_450_00,
            payment_received=17_200_00,
            authorized_promotion=1_000_00,
            expected_status="REVIEW_REQUIRED",
            review_reason="unexplained_deduction_amount",
            degradation="digital_text",
            notes="Golden demo: $1,250 claimed, $1,000 authorized, $250 unexplained.",
            invoice_number="NSB-INV-1001",
            payment_reference="PAY-NORTHSTAR-0001",
        ),
        _scenario(
            rng,
            seed,
            "S05",
            "eval",
            invoice_total=14_000_00,
            payment_received=14_000_00,
            authorized_promotion=0,
            expected_status="MATCHED",
            review_reason=None,
            degradation="multi_invoice_remittance",
            notes="Payment explicitly allocates across multiple invoices.",
        ),
        _scenario(
            rng,
            seed,
            "S06",
            "eval",
            invoice_total=4_250_00,
            payment_received=4_250_00,
            authorized_promotion=0,
            expected_status="REVIEW_REQUIRED",
            review_reason="duplicate_document",
            degradation="duplicate_remittance",
            notes="Duplicate remittance must not create duplicate financial records.",
        ),
        _scenario(
            rng,
            seed,
            "S07",
            "eval",
            invoice_total=3_900_00,
            payment_received=3_900_00,
            authorized_promotion=0,
            expected_status="REVIEW_REQUIRED",
            review_reason="unknown_invoice_reference",
            degradation="digital_text",
            notes="Remittance references an invoice that does not exist in truth.",
        ),
        _scenario(
            rng,
            seed,
            "S08",
            "eval",
            invoice_total=7_300_00,
            payment_received=7_300_00,
            authorized_promotion=0,
            expected_status="REVIEW_REQUIRED",
            review_reason="retailer_reference_conflict",
            degradation="digital_text",
            notes="Reference conflict must not cross retailer or tenant boundaries.",
        ),
        _scenario(
            rng,
            seed,
            "S09",
            "eval",
            invoice_total=6_600_00,
            payment_received=6_600_00,
            authorized_promotion=0,
            expected_status="REVIEW_REQUIRED",
            review_reason="low_confidence_invoice_reference",
            degradation="missing_invoice_reference",
            notes="Missing/low-confidence invoice ID routes to review.",
        ),
        _scenario(
            rng,
            seed,
            "S10",
            "eval",
            invoice_total=10_000_00,
            payment_received=8_750_00,
            authorized_promotion=500_00,
            expected_status="VALIDATION_FAILED",
            review_reason="inconsistent_arithmetic",
            degradation="bad_remittance_total",
            notes="Document arithmetic contradicts expected totals.",
        ),
        _scenario(
            rng,
            seed,
            "S11",
            "eval",
            invoice_total=2_500_00,
            payment_received=2_500_00,
            authorized_promotion=0,
            expected_status="REVIEW_REQUIRED",
            review_reason="no_text_or_noisy_scan",
            degradation="no_text_scan",
            notes="Image-only/no-text evidence is not silently trusted.",
        ),
        _scenario(
            rng,
            seed,
            "S12",
            "eval",
            invoice_total=9_100_00,
            payment_received=8_100_00,
            authorized_promotion=1_000_00,
            expected_status="REVIEW_REQUIRED",
            review_reason="duplicate_deduction_claim",
            degradation="duplicate_deduction",
            notes="Duplicate deduction claim must be detected and reviewed.",
        ),
    ]
    return tuple(scenarios)


def generate_dataset(root: Path, seed: int = DEFAULT_SEED) -> DatasetBuild:
    scenarios = build_scenarios(seed)
    benchmark_dir = root / "data" / "benchmark" / f"seed_{seed}"
    truth_dir = benchmark_dir / "ground_truth"
    evidence_dir = benchmark_dir / "evidence"
    truth_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    truth_payload = [scenario.to_json() for scenario in scenarios]
    truth_path = truth_dir / "scenarios.json"
    truth_path.write_text(json.dumps(truth_payload, indent=2) + "\n", encoding="utf-8")

    for scenario in scenarios:
        _render_evidence(evidence_dir, scenario)

    manifest = _manifest(root, seed, scenarios, truth_path, evidence_dir)
    manifest_path = benchmark_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    return DatasetBuild(scenarios=scenarios, manifest=manifest)


def _scenario(
    rng: random.Random,
    seed: int,
    family_id: str,
    split: DatasetSplit,
    *,
    invoice_total: int,
    payment_received: int,
    authorized_promotion: int,
    expected_status: str,
    review_reason: str | None,
    degradation: str,
    notes: str,
    invoice_number: str | None = None,
    payment_reference: str | None = None,
) -> BenchmarkScenario:
    claimed = invoice_total - payment_received
    validated = min(max(claimed, 0), authorized_promotion)
    unexplained = max(claimed - validated, 0)
    suffix = rng.randint(1000, 9999)
    return BenchmarkScenario(
        scenario_id=f"{family_id.lower()}_{suffix}",
        family_id=family_id,
        split=split,
        seed=seed,
        tenant="Northstar Beverages",
        retailer="Fictional Market Co.",
        invoice_number=invoice_number or f"NSB-INV-{suffix}",
        payment_reference=payment_reference or f"PAY-NSB-{suffix}",
        invoice_total_cents=invoice_total,
        payment_received_cents=payment_received,
        authorized_promotion_cents=authorized_promotion,
        expected_status=expected_status,  # type: ignore[arg-type]
        expected_claimed_deduction_cents=claimed,
        expected_validated_deduction_cents=validated,
        expected_unexplained_deduction_cents=unexplained,
        expected_review_reason=review_reason,
        document_templates=("invoice_basic_v1", "remittance_basic_v1"),
        degradation=degradation,
        notes=notes,
    )


def _render_evidence(evidence_dir: Path, scenario: BenchmarkScenario) -> None:
    scenario_dir = evidence_dir / scenario.scenario_id
    if scenario.degradation == "no_text_scan":
        render_blank_pdf(scenario_dir / "invoice.pdf")
        render_blank_pdf(scenario_dir / "remittance.pdf")
        return

    render_text_pdf(
        scenario_dir / "invoice.pdf",
        "Northstar Beverages Invoice",
        [
            f"Scenario: {scenario.scenario_id}",
            f"Retailer: {scenario.retailer}",
            f"Invoice Number: {scenario.invoice_number}",
            f"Invoice Total: {_format_cents(scenario.invoice_total_cents)}",
        ],
    )
    render_text_pdf(
        scenario_dir / "remittance.pdf",
        "Northstar Beverages Remittance",
        [
            f"Scenario: {scenario.scenario_id}",
            f"Payment Reference: {scenario.payment_reference}",
            f"Invoice Reference: {scenario.invoice_number}",
            f"Payment Received: {_format_cents(scenario.payment_received_cents)}",
            f"Authorized Promotion: {_format_cents(scenario.authorized_promotion_cents)}",
        ],
    )


def _manifest(
    root: Path,
    seed: int,
    scenarios: tuple[BenchmarkScenario, ...],
    truth_path: Path,
    evidence_dir: Path,
) -> dict[str, object]:
    truth_hash = hashlib.sha256(truth_path.read_bytes()).hexdigest()
    splits = {split: sum(1 for scenario in scenarios if scenario.split == split) for split in ("dev", "eval", "golden_demo")}
    families = {family_id: SCENARIO_FAMILIES[family_id] for family_id in sorted({scenario.family_id for scenario in scenarios})}
    return {
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
        "created_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "dataset_kind": "generated_synthetic",
        "scenario_count": len(scenarios),
        "splits": splits,
        "families": families,
        "truth_sha256": truth_hash,
        "truth_path": str(truth_path.relative_to(root).as_posix()),
        "evidence_path": str(evidence_dir.relative_to(root).as_posix()),
    }


def _format_cents(amount_cents: int) -> str:
    dollars, cents = divmod(amount_cents, 100)
    return f"${dollars:,}.{cents:02d}"
