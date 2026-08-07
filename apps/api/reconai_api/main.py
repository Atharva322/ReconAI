from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .demo_data import apply_review_decision, get_review_case, reset_review_case
from .models import ReviewDecisionRequest
from reconai_evidence.evaluate import evaluate_evidence_suggestions
from reconai_reliability.evaluate import evaluate_reliability


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "reconai-api",
            "environment": settings.environment,
        }

    @app.get(f"{settings.api_prefix}/demo-tenant", tags=["demo"])
    def demo_tenant() -> dict[str, str]:
        return {
            "id": "00000000-0000-4000-8000-000000000001",
            "name": "Northstar Beverages",
            "mode": "seeded-demo",
        }

    @app.get(f"{settings.api_prefix}/review-cases/golden", tags=["review"])
    def golden_review_case() -> dict[str, object]:
        return get_review_case()

    @app.post(f"{settings.api_prefix}/review-cases/golden/decision", tags=["review"])
    def decide_golden_review_case(request: ReviewDecisionRequest) -> dict[str, object]:
        return apply_review_decision(request.decision, request.comment)

    @app.post(f"{settings.api_prefix}/review-cases/golden/reset", tags=["review"])
    def reset_golden_review_case() -> dict[str, object]:
        return reset_review_case()

    @app.get(f"{settings.api_prefix}/reliability/demo", tags=["reliability"])
    def reliability_demo() -> dict[str, object]:
        return evaluate_reliability()

    @app.get(f"{settings.api_prefix}/evidence/demo", tags=["evidence"])
    def evidence_demo() -> dict[str, object]:
        from pathlib import Path

        return evaluate_evidence_suggestions(Path.cwd())

    return app


app = create_app()
