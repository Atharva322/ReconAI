from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings


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

    return app


app = create_app()
