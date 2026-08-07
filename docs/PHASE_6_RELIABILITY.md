# Phase 6 Reliability

Status: complete locally.

## Goal

Prove local reliability behavior before adding cloud queues or object storage.

## Scope

- Idempotent document ingestion by tenant, source, and SHA-256.
- Duplicate upload detection.
- Processing retry budget.
- Replay for failed documents.
- Correlation IDs on audit events.
- Reliability metrics and reports.

## Exit Criteria

- [x] Duplicate upload creates no duplicate document record.
- [x] Transient processing failure recovers within retry budget.
- [x] Permanent processing failure remains failed after replay.
- [x] Audit events are emitted for uploads, duplicates, attempts, failures, recovery, replay, and final state.
- [x] Reliability report writes JSON and Markdown artifacts.
- [x] Existing Phase 0-5 tests still pass.

## Generated Reports

- `data/benchmark/seed_20260806/reports/reliability_metrics.json`
- `data/benchmark/seed_20260806/reports/reliability_metrics.md`

## Measured Results

- Ingested documents: 3
- Duplicate uploads: 1
- Processing attempts: 7
- Recovered after retry: 1
- Failed documents: 1
- Audit events: 22

## Verification

- `python -m pytest -p no:cacheprovider` -> 29 passed.
- `python packages\reliability\reconai_reliability\run_phase6_evaluation.py` -> `valid: true`.
- `python scripts\check_foundation.py` -> passed.
- `npm run build` from `apps/web` -> passed.
- `npm audit` from `apps/web` -> 0 vulnerabilities.
- `powershell -ExecutionPolicy Bypass -File scripts\check_migrations.ps1` -> passed.
- `docker compose build api` -> API image built.
- `docker compose up -d` plus `GET /api/v1/reliability/demo` -> returned `valid: true`.

## Notes

- Phase 6 uses an in-memory local pipeline so retry/replay/idempotency behavior can be tested without SQS, S3, or a worker service.
- Persistence and real async workers are still future work. The local contract is now explicit enough to move behind a queue or database-backed implementation later.
- The permanent failure case intentionally remains failed after replay, proving replay does not hide deterministic failures.
