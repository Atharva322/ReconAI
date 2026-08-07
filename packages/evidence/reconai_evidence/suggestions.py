from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SuggestionStatus = Literal["ACCEPTED", "REJECTED"]


@dataclass(frozen=True)
class EvidenceCitation:
    source_id: str
    evidence_type: str
    excerpt: str
    supports_amount_cents: int | None = None


@dataclass(frozen=True)
class EvidenceSuggestion:
    scenario_id: str
    suggested_reason: str
    suggested_validated_cents: int
    suggested_unexplained_cents: int
    confidence: float
    citations: tuple[EvidenceCitation, ...]


@dataclass(frozen=True)
class ValidatedSuggestion:
    scenario_id: str
    status: SuggestionStatus
    suggested_reason: str
    accepted_reason: str | None
    rejection_reason: str | None
    citation_count: int


def validate_suggestion(
    suggestion: EvidenceSuggestion,
    *,
    expected_validated_cents: int,
    expected_unexplained_cents: int,
    expected_review_reason: str | None,
) -> ValidatedSuggestion:
    if not suggestion.citations:
        return _reject(suggestion, "missing_citation")
    if suggestion.suggested_validated_cents != expected_validated_cents:
        return _reject(suggestion, "validated_amount_conflict")
    if suggestion.suggested_unexplained_cents != expected_unexplained_cents:
        return _reject(suggestion, "unexplained_amount_conflict")
    if expected_review_reason and suggestion.suggested_reason != expected_review_reason:
        return _reject(suggestion, "review_reason_conflict")
    if any(citation.supports_amount_cents is None for citation in suggestion.citations):
        return _reject(suggestion, "unsupported_citation_amount")

    return ValidatedSuggestion(
        scenario_id=suggestion.scenario_id,
        status="ACCEPTED",
        suggested_reason=suggestion.suggested_reason,
        accepted_reason=suggestion.suggested_reason,
        rejection_reason=None,
        citation_count=len(suggestion.citations),
    )


def _reject(suggestion: EvidenceSuggestion, reason: str) -> ValidatedSuggestion:
    return ValidatedSuggestion(
        scenario_id=suggestion.scenario_id,
        status="REJECTED",
        suggested_reason=suggestion.suggested_reason,
        accepted_reason=None,
        rejection_reason=reason,
        citation_count=len(suggestion.citations),
    )
