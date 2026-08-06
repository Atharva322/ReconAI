# Phase 3 Extraction

Status: complete locally.

## Goal

Convert benchmark evidence into typed extracted fields with confidence, provenance, validation status, and measurable field-level results.

## Scope

- Invoice PDF text extraction.
- Remittance PDF text extraction.
- Typed `ExtractionResult` and `ExtractedField` outputs.
- Explicit `INSUFFICIENT_EVIDENCE` for no-text PDFs.
- Benchmark extraction evaluator.
- JSON and Markdown extraction metric reports.

## Exit Criteria

- [x] Invoice fields extract with normalized values and provenance.
- [x] Remittance fields extract with normalized values and provenance.
- [x] No-text benchmark evidence routes to review.
- [x] Field-level evaluator writes JSON and Markdown reports.
- [x] Extraction exact-match rate is measured against Phase 2 ground truth.
- [x] Existing Phase 0-2 tests still pass.

## Generated Reports

- `data/benchmark/seed_20260806/reports/extraction_metrics.json`
- `data/benchmark/seed_20260806/reports/extraction_metrics.md`

## Measured Results

- Scenarios: 12
- Fields scored: 72
- Matched fields: 66
- Field exact match rate: 0.917
- Documents requiring review: 2

## Status Counts

- `invoice:EXTRACTED`: 11
- `invoice:INSUFFICIENT_EVIDENCE`: 1
- `remittance:EXTRACTED`: 11
- `remittance:INSUFFICIENT_EVIDENCE`: 1

## Notes

- The six field misses are intentional for S11, where both evidence PDFs have no text layer.
- OCR is still out of scope. The current behavior is safer: no-text evidence is detected and routed to review.
- The extractor is template-aware through deterministic regexes for generated Phase 2 evidence. Phase 4 can now build reconciliation against typed extracted fields, while later extraction work can broaden template support.
