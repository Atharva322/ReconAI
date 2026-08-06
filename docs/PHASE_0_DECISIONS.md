# Phase 0 Decisions

Status: complete locally.

Phase 0 proved the riskiest assumptions needed before Phase 1: exact money handling, golden demo arithmetic, local PDF text extraction, explicit low-confidence routing for no-text evidence, PostgreSQL cents round-trip behavior, and API/frontend toolchain viability.

## Decisions To Make

| Area | Decision | Result | Notes |
|---|---|---|---|
| Money representation | Integer cents in domain/API; PostgreSQL `BIGINT` cents | Passed | Python rejects float money construction; boundary tests cover zero, cents, golden amount, and large values |
| Golden transaction source | Generated Northstar fixture | Passed | `data/ground_truth/golden_northstar.json` matches the demo arithmetic exactly |
| PDF generation | Minimal digital PDFs rendered from structured truth | Passed | Canonical JSON is truth; PDFs are evidence artifacts |
| Local extraction route | Digital PDF text extraction with `pypdf` | Passed | Extracts invoice number and total from the generated invoice |
| Extraction contract | Typed dataclasses with status, fields, confidence, page, source, and optional bbox | Passed | No-text evidence returns `INSUFFICIENT_EVIDENCE` and requires review |
| PostgreSQL setup | Docker `postgres:16-alpine` one-shot check | Passed | `scripts/check_postgres_money_roundtrip.sql` round-trips `BIGINT` cents exactly |
| Dataset policy | Generated-only by default | Passed | See `docs/DATASET_PROVENANCE_POLICY.md` |
| Toolchains | Python 3.12, FastAPI, Node 22/npm baseline | Passed | FastAPI health smoke check and Node baseline check passed |

## Spike Log

- `python -m pytest` -> 12 passed.
- `python scripts\check_fastapi_toolchain.py` -> `FastAPI toolchain OK`.
- `node scripts\check_react_toolchain.mjs` -> Node baseline passed.
- `python packages\benchmark\reconai_benchmark\generate_phase0_artifacts.py` -> generated ground truth and PDFs.
- Digital PDF extraction returned `EXTRACTED` for `data/generated/northstar_invoice.pdf`.
- No-text PDF extraction returned `INSUFFICIENT_EVIDENCE` for `data/generated/northstar_no_text_scan.pdf`.
- Docker/PostgreSQL `BIGINT` cents check returned exact rows for `0`, `1`, `1845000`, and `99999999999`.

## Remaining Risks

- Local OCR for image-only/noisy documents is not implemented in Phase 0. Fallback: keep digital PDF text extraction for the MVP golden path and route no-text evidence to review until Phase 3 evaluates OCR/cloud adapters.
- The React check is a Node/toolchain baseline, not a scaffolded React app. Phase 1 should create the actual UI shell.
- The FastAPI check is an in-process health endpoint smoke test, not the final API app. Phase 1 should create the app structure.
