# Phase 7 Grounded AI Evidence

Status: complete locally.

## Goal

Add a typed evidence-suggestion layer that behaves like an AI assistant but cannot bypass deterministic reconciliation controls.

## Scope

- Evidence citations for promotion/rule support.
- Typed suggestion output with reason, validated amount, unexplained amount, confidence, and citations.
- Deterministic validation against benchmark ground truth and reconciliation expectations.
- Adversarial missing-evidence check.
- JSON and Markdown evidence metrics.

## Exit Criteria

- [x] Suggestions are structured and citation-backed.
- [x] Amount suggestions must match deterministic validated/unexplained amounts.
- [x] Review reason suggestions must match expected review reason when one exists.
- [x] Unsupported suggestions are rejected.
- [x] Evidence evaluator writes JSON and Markdown reports.
- [x] Existing Phase 0-6 tests still pass.

## Generated Reports

- `data/benchmark/seed_20260806/reports/evidence_metrics.json`
- `data/benchmark/seed_20260806/reports/evidence_metrics.md`

## Measured Results

- Scenarios: 12
- Accepted suggestions: 12
- Rejected benchmark suggestions: 0
- Reason accuracy: 1.000
- Structured validation failure rate: 0.000
- Unsupported suggestion acceptance count: 0

## Verification

- `python -m pytest -p no:cacheprovider` -> 33 passed.
- `python packages\evidence\reconai_evidence\run_phase7_evaluation.py` -> `valid: true`.
- `python scripts\check_foundation.py` -> passed.
- `npm run build` from `apps/web` -> passed.
- `npm audit` from `apps/web` -> 0 vulnerabilities.
- `powershell -ExecutionPolicy Bypass -File scripts\check_migrations.ps1` -> passed.
- `docker compose build api` -> API image built.
- `GET /api/v1/evidence/demo` -> returned `valid: true`.

## Notes

- This phase does not call a live LLM. It implements the typed contract and guardrails an LLM adapter must obey.
- Suggestions are only accepted after deterministic validation of citations, validated amount, unexplained amount, and review reason.
- The adversarial missing-evidence suggestion is rejected before it can affect reconciliation.
