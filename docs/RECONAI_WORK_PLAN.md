# ReconAI Work Plan

This plan is distilled from the downloaded project docs:

- `README (2).md`
- `ARCHITECTURE.md`
- `IMPLEMENTATION_PLAN.md`
- `PHASE_0_RISK_SPIKE.md`
- `DATASET_AND_EVALUATION.md`
- `DEMO_PLAN.md`
- `BLOCKERS_AND_RISKS.md`

## Project Goal

Build a recruiter-ready portfolio project for AI-assisted financial reconciliation. The useful demo is narrow and concrete: ingest fictional invoice/remittance/promotion evidence, extract normalized financial records with provenance, reconcile payment deductions deterministically, route ambiguous cases to human review, and report reproducible evaluation metrics.

## Non-Negotiables

- Money correctness is deterministic.
- Use integer cents or `Decimal`/database `NUMERIC`; never binary floats for money.
- Ground truth comes before extraction and matching claims.
- Generated data must be disclosed as generated/synthetic.
- AI may suggest evidence or reason codes, but domain rules decide financial outcomes.
- Ambiguous or low-confidence results become review work.
- Every workflow-changing write must be auditable.
- No private credentials, real PII, or proprietary financial data in the repo.

## Recommended Build Order

| Phase | Focus | Exit Gate |
|---:|---|---|
| 0 | Risk spike | Toolchains, PDF extraction, money model, schema, and golden arithmetic are proven locally |
| 1 | Foundation | FastAPI, React, PostgreSQL, migrations, seed data, health check, and CI boot reliably |
| 2 | Benchmark | Deterministic generated dataset, ground truth, manifest, and validator exist |
| 3 | Extraction | Documents produce typed normalized records with confidence and provenance |
| 4 | Reconciliation | Deterministic matching/deduction scenarios pass tests and evaluation |
| 5 | Review UI | Local five-minute demo works end to end |
| 6 | Reliability | Idempotency, async worker boundary, retries, replay, audit, and telemetry are visible |
| 7 | AI evidence | Optional grounded AI suggestions validate against deterministic controls |
| 8 | Cloud demo | Small hosted demo with smoke/load/security checks |
| 9 | Recruiter polish | README, screenshots/video, architecture diagram, benchmark report, and resume bullets use measured results |

## Immediate Phase 0 Plan

Phase 0 should be completed before scaffolding the whole app. Its job is to remove expensive uncertainty.

1. Create a one-page domain glossary for invoice, payment, remittance, deduction, promotion, allocation, review task, and audit event.
2. Choose the money representation for API, Python, and PostgreSQL.
3. Encode the golden Northstar transaction:
   - invoice total: `$18,450`
   - payment received: `$17,200`
   - claimed deduction: `$1,250`
   - authorized promotion: `$1,000`
   - unexplained amount: `$250`
   - expected workflow: `REVIEW_REQUIRED`
4. Prototype pure reconciliation arithmetic with tests for exact payment, deduction, promotion validation, and unexplained amount.
5. Generate simple fictional invoice and remittance PDFs from structured truth.
6. Prove local text extraction can recover invoice number and amount from at least one digital PDF.
7. Create one degraded/noisy or image-only variant and confirm it either extracts confidently or fails into an explicit low-confidence/error state.
8. Define a typed `ExtractionResult` contract independent of any OCR vendor.
9. Boot PostgreSQL and prove exact money round trips through the selected type.
10. Verify FastAPI and React/TypeScript toolchains start locally.
11. Write a dataset provenance policy: generated-only by default, fixed seed, no real PII, manifest required.
12. Record actual decisions, failures, and fallbacks in `docs/PHASE_0_DECISIONS.md`.

## First Repo Structure To Create

Create only what Phase 0 needs first:

```text
docs/
  RECONAI_WORK_PLAN.md
  PHASE_0_DECISIONS.md
  DOMAIN_GLOSSARY.md
packages/
  domain/
    tests/
  extraction/
    tests/
  benchmark/
    tests/
data/
  generated/
  ground_truth/
```

The full target structure can wait until Phase 1:

```text
apps/
  api/
  web/
  worker/
packages/
  domain/
  extraction/
  benchmark/
migrations/
infra/
tests/
```

## Phase 0 Acceptance Checklist

- [x] Domain glossary exists.
- [x] Money representation is selected and tested.
- [x] Golden financial truth exists as structured data.
- [x] Pure reconciliation calculates the golden expected outcome exactly.
- [x] At least one generated PDF can be read locally.
- [x] Degraded document behavior is explicit, not silently trusted.
- [x] Typed extraction contract is prototyped.
- [x] PostgreSQL round-trip for money is exact.
- [x] FastAPI toolchain boots.
- [x] React/TypeScript toolchain boots.
- [x] Dataset provenance policy is recorded.
- [x] Phase 0 decisions and fallbacks are written down.

## Cut Line If Time Gets Tight

Cut or defer in this order:

1. OpenSearch/vector retrieval.
2. LLM classification.
3. AWS-native OCR.
4. Full auth and multi-user admin screens.
5. Terraform breadth and multiple environments.
6. Advanced fuzzy matching.

Do not cut ground truth, deterministic reconciliation, confidence/review routing, audit history, regression tests, or reproducible evaluation.
