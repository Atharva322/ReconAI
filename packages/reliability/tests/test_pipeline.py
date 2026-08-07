from pathlib import Path

from reconai_reliability.evaluate import evaluate_reliability, write_reliability_report
from reconai_reliability.pipeline import DocumentRecord, InMemoryDocumentPipeline, ProcessingError


def test_duplicate_ingestion_returns_existing_record() -> None:
    pipeline = InMemoryDocumentPipeline(lambda _document, payload: {"size": str(len(payload))})

    first = pipeline.ingest("tenant-a", "upload", b"same")
    second = pipeline.ingest("tenant-a", "upload", b"same")

    assert first.document_id == second.document_id
    assert pipeline.metrics().ingested_documents == 1
    assert pipeline.metrics().duplicate_uploads == 1


def test_transient_processing_failure_recovers_with_retry() -> None:
    attempts = 0

    def flaky(_document: DocumentRecord, _payload: bytes) -> dict[str, str]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ProcessingError("temporary")
        return {"ok": "true"}

    pipeline = InMemoryDocumentPipeline(flaky, max_retries=1)
    document = pipeline.ingest("tenant-a", "upload", b"payload")

    processed = pipeline.process(document)

    assert processed.status == "EXTRACTED"
    assert processed.retry_count == 1
    assert pipeline.metrics().recovered_after_retry == 1


def test_permanent_failure_remains_failed_after_replay() -> None:
    def failing(_document: DocumentRecord, _payload: bytes) -> dict[str, str]:
        raise ProcessingError("permanent")

    pipeline = InMemoryDocumentPipeline(failing, max_retries=1)
    document = pipeline.ingest("tenant-a", "upload", b"payload")

    pipeline.process(document)
    replayed = pipeline.replay(document)

    assert replayed.status == "FAILED"
    assert pipeline.metrics().failed_documents == 1
    assert any(event.action == "replay_requested" for event in pipeline.audit_events)


def test_reliability_evaluation_is_valid_and_writes_reports(tmp_path: Path) -> None:
    assert evaluate_reliability()["valid"] is True

    write_reliability_report(tmp_path)

    assert (tmp_path / "data" / "benchmark" / "seed_20260806" / "reports" / "reliability_metrics.json").exists()
    assert (tmp_path / "data" / "benchmark" / "seed_20260806" / "reports" / "reliability_metrics.md").exists()
