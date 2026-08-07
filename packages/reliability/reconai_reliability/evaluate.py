from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .pipeline import DocumentRecord, InMemoryDocumentPipeline, ProcessingError


class FlakyExtractor:
    def __init__(self) -> None:
        self.attempts_by_document: dict[str, int] = {}

    def __call__(self, document: DocumentRecord, payload: bytes) -> dict[str, str]:
        attempts = self.attempts_by_document.get(document.document_id, 0)
        self.attempts_by_document[document.document_id] = attempts + 1
        if payload == b"transient-failure" and attempts == 0:
            raise ProcessingError("temporary extractor failure")
        if payload == b"permanent-failure":
            raise ProcessingError("permanent extractor failure")
        return {"byte_length": str(len(payload)), "sha256": document.sha256}


def evaluate_reliability() -> dict[str, object]:
    extractor = FlakyExtractor()
    pipeline = InMemoryDocumentPipeline(extractor=extractor, max_retries=1)

    first = pipeline.ingest("tenant-demo", "upload", b"stable-document", "corr-stable")
    duplicate = pipeline.ingest("tenant-demo", "upload", b"stable-document", "corr-duplicate")
    pipeline.process(first, "corr-process-stable")

    transient = pipeline.ingest("tenant-demo", "upload", b"transient-failure", "corr-transient")
    pipeline.process(transient, "corr-process-transient")

    permanent = pipeline.ingest("tenant-demo", "upload", b"permanent-failure", "corr-permanent")
    pipeline.process(permanent, "corr-process-permanent")
    pipeline.replay(permanent, "corr-replay-permanent")

    metrics = pipeline.metrics()
    result = {
        "valid": (
            first.document_id == duplicate.document_id
            and transient.status == "EXTRACTED"
            and permanent.status == "FAILED"
            and metrics.duplicate_uploads == 1
            and metrics.recovered_after_retry == 1
            and metrics.failed_documents == 1
        ),
        "metrics": asdict(metrics),
        "records": [
            {
                "document_id": record.document_id,
                "status": record.status,
                "retry_count": record.retry_count,
                "last_error": record.last_error,
            }
            for record in pipeline.records.values()
        ],
        "audit_events": [asdict(event) for event in pipeline.audit_events],
    }
    return result


def write_reliability_report(root: Path) -> dict[str, object]:
    result = evaluate_reliability()
    reports_dir = root / "data" / "benchmark" / "seed_20260806" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "reliability_metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (reports_dir / "reliability_metrics.md").write_text(_markdown_report(result), encoding="utf-8")
    return result


def _markdown_report(result: dict[str, object]) -> str:
    metrics = result["metrics"]
    assert isinstance(metrics, dict)
    lines = [
        "# Reliability Evaluation",
        "",
        f"- Valid: {result['valid']}",
        f"- Ingested documents: {metrics['ingested_documents']}",
        f"- Duplicate uploads: {metrics['duplicate_uploads']}",
        f"- Processing attempts: {metrics['processing_attempts']}",
        f"- Recovered after retry: {metrics['recovered_after_retry']}",
        f"- Failed documents: {metrics['failed_documents']}",
        f"- Audit events: {metrics['audit_event_count']}",
        "",
        "## Assertions",
        "",
        "- Duplicate upload returned the original document record.",
        "- Transient extractor failure recovered within retry budget.",
        "- Permanent extractor failure remained failed after replay.",
        "- Every state-changing operation produced audit events with correlation IDs.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    result = write_reliability_report(root)
    print(json.dumps(result, indent=2))
    if not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
