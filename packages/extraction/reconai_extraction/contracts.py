from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ExtractionStatus = Literal["EXTRACTED", "INSUFFICIENT_EVIDENCE", "INVALID_DOCUMENT"]


@dataclass(frozen=True)
class ExtractedField:
    field_name: str
    raw_value: str
    normalized_value: str
    confidence: float
    page: int
    source: str
    bbox: tuple[float, float, float, float] | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if self.page < 1:
            raise ValueError("page numbers are 1-based")


@dataclass(frozen=True)
class ExtractionResult:
    document_type: str
    status: ExtractionStatus
    fields: tuple[ExtractedField, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def requires_review(self) -> bool:
        return self.status != "EXTRACTED" or any(field.confidence < 0.8 for field in self.fields)
