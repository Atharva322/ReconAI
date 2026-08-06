# Phase 0 Decisions

Status: not started.

Use this file to record the actual spike results before Phase 1 begins.

## Decisions To Make

| Area | Decision | Result | Notes |
|---|---|---|---|
| Money representation | TBD | Pending | Choose API/Python/DB representation and prove exact round trips |
| Golden transaction source | Generated Northstar fixture | Pending | Must match the demo arithmetic exactly |
| PDF generation | TBD | Pending | Canonical JSON should be truth; PDF should be rendered evidence |
| Local extraction route | TBD | Pending | Digital PDF extraction first; OCR fallback optional |
| Extraction contract | TBD | Pending | Must include field value, normalized value, confidence, page, and provenance |
| PostgreSQL setup | TBD | Pending | Docker preferred; local Postgres fallback is acceptable |
| Dataset policy | Generated-only by default | Pending | No real PII or proprietary data |
| Toolchains | TBD | Pending | Verify FastAPI and React/TypeScript startup |

## Spike Log

Record commands, outcomes, and links to committed artifacts here.

## Remaining Risks

Add unresolved risks with an explicit fallback before moving to Phase 1.
