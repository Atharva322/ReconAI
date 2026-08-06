# Phase 1 Foundation

Status: complete locally.

## Goal

Create the smallest reliable local foundation for ReconAI:

- FastAPI app structure;
- React/TypeScript web shell;
- PostgreSQL migration and demo seed SQL;
- Docker Compose wiring;
- local smoke checks.

## Exit Criteria

- [x] FastAPI health and demo tenant endpoints pass tests.
- [x] React/TypeScript shell structure is present and checkable.
- [x] PostgreSQL migrations and seed SQL execute successfully.
- [x] Docker Compose config validates.
- [x] Existing Phase 0 tests still pass.
- [x] Known limitations are documented.

## Verification

- `python -m pytest -p no:cacheprovider` -> 14 passed.
- `python scripts\check_foundation.py` -> API health and demo tenant checks passed.
- `npm run build` from `apps/web` -> React/Vite production build passed.
- `npm audit` from `apps/web` -> 0 vulnerabilities.
- `powershell -ExecutionPolicy Bypass -File scripts\check_migrations.ps1` -> migration and seed SQL passed.
- `docker compose config` -> Compose file validated.
- `docker compose build api` -> API image built successfully.
- `docker compose up -d` followed by `GET http://localhost:8000/health` -> returned `status=ok`, `service=reconai-api`, `environment=docker`.

## Known Limitations

- The API does not connect to Postgres yet at request time; Phase 1 only proves app structure, migrations, seed data, and container boot.
- The web app is a React/TypeScript shell, not the final reconciliation workflow.
- Migrations are plain ordered SQL files. Phase 2/3 can introduce a formal migration runner if needed.
- The Compose stack does not yet auto-apply migrations on startup; migrations are verified through `scripts/check_migrations.ps1`.
