from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Callable, Literal
from uuid import NAMESPACE_URL, uuid5

DocumentStatus = Literal["UPLOADED", "PROCESSING", "EXTRACTED", "FAILED"]


class ProcessingError(RuntimeError):
    pass


@dataclass(frozen=True)
class AuditEvent:
    action: str
    entity_id: str
    correlation_id: str
    detail: str
    created_at_utc: str = field(default_factory=lambda: datetime.now(UTC).replace(microsecond=0).isoformat())


@dataclass
class DocumentRecord:
    document_id: str
    tenant_id: str
    source: str
    sha256: str
    status: DocumentStatus
    retry_count: int = 0
    extracted_fields: dict[str, str] = field(default_factory=dict)
    last_error: str | None = None


@dataclass(frozen=True)
class PipelineMetrics:
    ingested_documents: int
    duplicate_uploads: int
    processing_attempts: int
    recovered_after_retry: int
    failed_documents: int
    audit_event_count: int


Extractor = Callable[[DocumentRecord, bytes], dict[str, str]]


class InMemoryDocumentPipeline:
    def __init__(self, extractor: Extractor, max_retries: int = 2) -> None:
        self.extractor = extractor
        self.max_retries = max_retries
        self.records: dict[str, DocumentRecord] = {}
        self.audit_events: list[AuditEvent] = []
        self.duplicate_uploads = 0
        self.processing_attempts = 0
        self.recovered_after_retry = 0
        self._payloads: dict[str, bytes] = {}

    def ingest(self, tenant_id: str, source: str, payload: bytes, correlation_id: str | None = None) -> DocumentRecord:
        sha256 = hashlib.sha256(payload).hexdigest()
        key = self._key(tenant_id, source, sha256)
        correlation = correlation_id or self._correlation_id(key)

        existing = self.records.get(key)
        if existing:
            self.duplicate_uploads += 1
            self._audit("duplicate_upload_detected", existing.document_id, correlation, "Returned existing document record.")
            return existing

        document = DocumentRecord(
            document_id=str(uuid5(NAMESPACE_URL, key)),
            tenant_id=tenant_id,
            source=source,
            sha256=sha256,
            status="UPLOADED",
        )
        self.records[key] = document
        self._payloads[key] = payload
        self._audit("document_uploaded", document.document_id, correlation, "New document accepted for processing.")
        return document

    def process(self, document: DocumentRecord, correlation_id: str | None = None) -> DocumentRecord:
        key = self._key(document.tenant_id, document.source, document.sha256)
        payload = self._payloads[key]
        correlation = correlation_id or self._correlation_id(key)

        if document.status == "EXTRACTED":
            self._audit("processing_skipped_idempotent", document.document_id, correlation, "Document already extracted.")
            return document

        while document.retry_count <= self.max_retries:
            self.processing_attempts += 1
            document.status = "PROCESSING"
            self._audit("processing_attempted", document.document_id, correlation, f"Attempt {document.retry_count + 1}.")
            try:
                fields = self.extractor(document, payload)
            except ProcessingError as exc:
                document.last_error = str(exc)
                document.retry_count += 1
                self._audit("processing_failed", document.document_id, correlation, str(exc))
                if document.retry_count > self.max_retries:
                    document.status = "FAILED"
                    self._audit("document_failed", document.document_id, correlation, "Retry budget exhausted.")
                    return document
                continue

            document.extracted_fields = fields
            document.status = "EXTRACTED"
            document.last_error = None
            if document.retry_count:
                self.recovered_after_retry += 1
                self._audit("processing_recovered", document.document_id, correlation, "Document recovered after retry.")
            self._audit("document_extracted", document.document_id, correlation, "Document extracted successfully.")
            return document

        return document

    def replay(self, document: DocumentRecord, correlation_id: str | None = None) -> DocumentRecord:
        key = self._key(document.tenant_id, document.source, document.sha256)
        correlation = correlation_id or self._correlation_id(f"replay:{key}")
        self._audit("replay_requested", document.document_id, correlation, "Processing replay requested.")
        if document.status == "FAILED":
            document.retry_count = 0
        return self.process(document, correlation)

    def metrics(self) -> PipelineMetrics:
        return PipelineMetrics(
            ingested_documents=len(self.records),
            duplicate_uploads=self.duplicate_uploads,
            processing_attempts=self.processing_attempts,
            recovered_after_retry=self.recovered_after_retry,
            failed_documents=sum(1 for record in self.records.values() if record.status == "FAILED"),
            audit_event_count=len(self.audit_events),
        )

    def _audit(self, action: str, entity_id: str, correlation_id: str, detail: str) -> None:
        self.audit_events.append(
            AuditEvent(
                action=action,
                entity_id=entity_id,
                correlation_id=correlation_id,
                detail=detail,
            )
        )

    @staticmethod
    def _key(tenant_id: str, source: str, sha256: str) -> str:
        return f"{tenant_id}:{source}:{sha256}"

    @staticmethod
    def _correlation_id(value: str) -> str:
        return str(uuid5(NAMESPACE_URL, f"reconai:{value}"))
