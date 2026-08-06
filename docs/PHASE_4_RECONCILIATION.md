# Phase 4 Reconciliation

Status: complete locally.

## Goal

Implement deterministic payment/invoice reconciliation against the Phase 2 benchmark with explicit deduction arithmetic, promotion validation, and review routing.

## Scope

- Exact invoice-reference reconciliation.
- Integer-cent deduction arithmetic.
- Promotion validation up to the authorized amount.
- Review routing for partial payments, unexplained deductions, duplicates, unknown references, conflicts, low-confidence evidence, no-text evidence, and duplicate deduction claims.
- Validation failure for inconsistent arithmetic.
- Benchmark reconciliation evaluator with JSON and Markdown reports.

## Exit Criteria

- [x] Golden `$1,250` deduction / `$250` unexplained case passes.
- [x] Exact payments confirm as `MATCHED`.
- [x] Partial payments route to `PARTIAL_REVIEW`.
- [x] Deterministic blockers never auto-match.
- [x] Reconciliation evaluator reports status accuracy and deduction exact accuracy.
- [x] False auto-match count is zero.
- [x] Existing Phase 0-3 tests still pass.

## Generated Reports

- `data/benchmark/seed_20260806/reports/reconciliation_metrics.json`
- `data/benchmark/seed_20260806/reports/reconciliation_metrics.md`

## Measured Results

- Scenarios: 12
- Status accuracy: 1.000
- Deduction exact accuracy: 1.000
- Confirmed-match precision: 1.000
- Review-routing recall: 1.000
- False auto-match count: 0

## Status Counts

- `MATCHED`: 3
- `PARTIAL_REVIEW`: 1
- `REVIEW_REQUIRED`: 7
- `VALIDATION_FAILED`: 1

## Notes

- Phase 4 uses deterministic scenario blockers for known unsafe cases: duplicate documents, unknown references, retailer conflicts, low-confidence/no-text evidence, inconsistent arithmetic, and duplicate deduction claims.
- No fuzzy threshold is allowed to silently confirm a match in this phase.
- Multi-invoice allocation is represented as a covered family but still simplified to scenario-level totals. Detailed allocation-line scoring should be deepened before a production-style reconciliation UI.
