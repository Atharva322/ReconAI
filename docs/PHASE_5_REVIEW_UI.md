# Phase 5 Human Review Product

Status: complete locally.

## Goal

Turn the deterministic extraction and reconciliation work into a recruiter-visible local review workflow.

## Scope

- Review queue for the golden Northstar case.
- Side-by-side evidence summary with confidence/provenance.
- Reconciliation detail showing invoice, payment, claimed deduction, validated promotion, and unexplained amount.
- Review decision controls for approve/dispute.
- Audit timeline showing processing, reconciliation, and review-task creation.
- API endpoints for the golden review case and decision action.

## Exit Criteria

- [x] API exposes golden review case.
- [x] API accepts review decision and appends audit event.
- [x] UI renders review queue, evidence, reconciliation, decision controls, and audit timeline.
- [x] Web production build passes.
- [x] API and existing benchmark tests still pass.
- [x] Local dev server can run for manual review.

## Verification

- `python -m pytest -p no:cacheprovider` -> 24 passed.
- `python scripts\check_foundation.py` -> passed.
- `npm run check` from `apps/web` -> review workspace structure passed.
- `npm run build` from `apps/web` -> production build passed.
- `npm audit` from `apps/web` -> 0 vulnerabilities.
- `powershell -ExecutionPolicy Bypass -File scripts\check_migrations.ps1` -> migration check passed.
- `http://127.0.0.1:5173/` -> returned 200 from the local Vite dev server.

## Notes

- The UI uses static golden-case data for the first recruiter-visible review flow.
- The API exposes the same golden case and decision endpoint, but the frontend is not yet wired to fetch/update API state.
- Phase 6 should introduce reliability behavior and can also persist review decisions through the database.
