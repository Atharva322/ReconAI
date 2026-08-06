# Phase 2 Benchmark

Status: complete locally.

## Goal

Create a reproducible generated benchmark before implementing extraction or matching logic against it.

## Scope

- Deterministic scenario generation from a fixed seed.
- Canonical JSON ground truth.
- Rendered fictional PDF evidence derived from truth.
- Dataset manifest with generator version, seed, split counts, family coverage, and truth hash.
- Validator for arithmetic, coverage, and review-reason consistency.

## Scenario Families

- S01 exact invoice payment
- S02 explicit partial payment
- S03 payment plus authorized promotion
- S04 promotion over-claim
- S05 one payment, multiple invoices
- S06 duplicate remittance/document
- S07 unknown invoice reference
- S08 conflicting retailer/reference
- S09 missing or low-confidence invoice ID
- S10 inconsistent arithmetic
- S11 rotated/noisy scan
- S12 duplicate deduction claim

## Exit Criteria

- [x] Generator is deterministic.
- [x] All required scenario families are represented.
- [x] `dev`, `eval`, and `golden_demo` splits are present.
- [x] Ground truth validates from a clean generated dataset.
- [x] Manifest records seed, generator version, scenario count, split counts, and truth hash.
- [x] Generated data policy remains synthetic-only.
- [x] Existing Phase 0/1 tests still pass.

## Generated Artifacts

- `data/benchmark/seed_20260806/manifest.json`
- `data/benchmark/seed_20260806/ground_truth/scenarios.json`
- `data/benchmark/seed_20260806/evidence/*/invoice.pdf`
- `data/benchmark/seed_20260806/evidence/*/remittance.pdf`

## Verification

- `python packages\benchmark\reconai_benchmark\generate_phase2_dataset.py` -> generated 12 scenarios.
- `python packages\benchmark\reconai_benchmark\validate_dataset.py` -> `valid: true`.
- `python -m pytest -p no:cacheprovider packages\benchmark` -> 4 passed.

## Notes

- The dataset is intentionally generated/synthetic and contains no real financial documents or PII.
- S11 uses no-text PDFs as the Phase 2 degraded evidence placeholder. True OCR/noise generation remains a Phase 3 extraction concern.
- S05 records the multi-invoice family at scenario level; detailed allocation-line truth should be expanded before implementing Phase 4 reconciliation scoring.
