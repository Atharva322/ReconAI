from collections.abc import Iterator
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from psycopg import Connection

from .config import get_settings
from .database import connect, run_migrations
from .models import ReviewDecisionRequest
from .repositories.review_cases import ReviewCaseRepository
from .services.document_processing_service import DocumentProcessingService
from .services.review_service import ReviewService
from reconai_evidence.evaluate import evaluate_evidence_suggestions
from reconai_reliability.evaluate import evaluate_reliability


def create_app() -> FastAPI:
    settings = get_settings()
    run_migrations(settings)
    app = FastAPI(title=settings.app_name)

    def get_connection() -> Iterator[Connection]:
        with connect(settings) as conn:
            yield conn

    def get_review_service(conn: Connection = Depends(get_connection)) -> ReviewService:
        return ReviewService(ReviewCaseRepository(conn))

    def get_document_processing_service(conn: Connection = Depends(get_connection)) -> DocumentProcessingService:
        return DocumentProcessingService(ReviewCaseRepository(conn), Path.cwd())

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
    def golden_review_case(service: ReviewService = Depends(get_review_service)) -> dict[str, object]:
        return service.get_golden_case()

    @app.get(f"{settings.api_prefix}/review-cases/{{case_id}}", tags=["review"])
    def review_case(case_id: str, service: ReviewService = Depends(get_review_service)) -> dict[str, object]:
        return service.get_case(case_id)

    @app.post(f"{settings.api_prefix}/review-cases/golden/decision", tags=["review"])
    def decide_golden_review_case(
        request: ReviewDecisionRequest,
        service: ReviewService = Depends(get_review_service),
    ) -> dict[str, object]:
        return service.apply_decision(request.decision, request.comment)

    @app.post(f"{settings.api_prefix}/review-cases/{{case_id}}/decision", tags=["review"])
    def decide_review_case(
        case_id: str,
        request: ReviewDecisionRequest,
        service: ReviewService = Depends(get_review_service),
    ) -> dict[str, object]:
        return service.apply_case_decision(case_id, request.decision, request.comment)

    @app.post(f"{settings.api_prefix}/review-cases/golden/reset", tags=["review"])
    def reset_golden_review_case(service: ReviewService = Depends(get_review_service)) -> dict[str, object]:
        return service.reset_golden_case()

    @app.post(f"{settings.api_prefix}/reconciliation/process", tags=["reconciliation"])
    async def process_reconciliation_documents(
        invoice: UploadFile | None = File(default=None),
        remittance: UploadFile | None = File(default=None),
        use_sample: bool = Form(default=False),
        service: DocumentProcessingService = Depends(get_document_processing_service),
    ) -> dict[str, object]:
        if use_sample:
            return service.process_sample_documents()
        if invoice is None or remittance is None:
            raise HTTPException(status_code=422, detail="invoice and remittance PDF files are required")

        with TemporaryDirectory() as temp_dir:
            invoice_path = await _save_upload(invoice, Path(temp_dir) / "invoice.pdf")
            remittance_path = await _save_upload(remittance, Path(temp_dir) / "remittance.pdf")
            return service.process_documents(invoice_path, remittance_path)

    @app.get(f"{settings.api_prefix}/reliability/demo", tags=["reliability"])
    def reliability_demo() -> dict[str, object]:
        return evaluate_reliability()

    @app.get(f"{settings.api_prefix}/evidence/demo", tags=["evidence"])
    def evidence_demo() -> dict[str, object]:
        from pathlib import Path

        return evaluate_evidence_suggestions(Path.cwd())

    return app


async def _save_upload(upload: UploadFile, path: Path) -> Path:
    filename = upload.filename or ""
    content_type = upload.content_type or ""
    if not filename.lower().endswith(".pdf") or content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail=f"{upload.filename or 'upload'} must be a PDF")

    content = await upload.read()
    if not content:
        raise HTTPException(status_code=422, detail=f"{upload.filename or 'upload'} is empty")
    max_bytes = 5 * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="PDF upload exceeds 5 MB demo limit")
    path.write_bytes(content)
    return path


app = create_app()
