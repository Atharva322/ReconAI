from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .contracts import ExtractedField, ExtractionResult

SCENARIO_RE = re.compile(r"Scenario:\s*(?P<scenario>[a-z0-9_]+)", re.IGNORECASE)
REFERENCE_VALUE = r"[A-Z0-9_-]+"
INVOICE_RE = re.compile(rf"(?:Invoice Number|Invoice #|Inv No):?\s*(?P<invoice>{REFERENCE_VALUE})")
INVOICE_REFERENCE_RE = re.compile(rf"(?:Invoice Reference|Invoice #):?\s*(?P<invoice>[A-Z0-9_, -]+)")
PAYMENT_REFERENCE_RE = re.compile(rf"(?:Payment Reference|Transaction Reference|Advice Number):?\s*(?P<payment>{REFERENCE_VALUE})")
INVOICE_TOTAL_RE = re.compile(r"(?:Invoice Total|Amount Due|Total Due):?\s*\$(?P<amount>[0-9,]+\.[0-9]{2})")
PAYMENT_RECEIVED_RE = re.compile(r"(?:Payment Received|Net Paid|Payment Amount):?\s*\$(?P<amount>[0-9,]+\.[0-9]{2})")
AUTHORIZED_PROMOTION_RE = re.compile(r"(?:Authorized Promotion|Authorized Amount):?\s*\$(?P<amount>[0-9,]+\.[0-9]{2})")
CLAIMED_DEDUCTION_RE = re.compile(r"(?:Claimed Deduction|Discount/Deduction|Deduction):?\s*\$(?P<amount>[0-9,]+\.[0-9]{2})")
PROMOTION_ID_RE = re.compile(rf"(?:Promotion ID|Promotion Code):?\s*(?P<promotion>{REFERENCE_VALUE})")


def extract_invoice_summary(path: Path) -> ExtractionResult:
    try:
        page_text = extract_pdf_text(path)
    except ExtractionDocumentError as exc:
        return ExtractionResult(document_type="invoice", status="INVALID_DOCUMENT", errors=(str(exc),))

    if not page_text.strip():
        return ExtractionResult(
            document_type="invoice",
            status="INSUFFICIENT_EVIDENCE",
            errors=("no text layer found",),
        )

    fields: list[ExtractedField] = []
    _append_regex_field(fields, "scenario_id", SCENARIO_RE, "scenario", page_text)
    invoice_match = INVOICE_RE.search(page_text)
    amount_match = INVOICE_TOTAL_RE.search(page_text)

    if invoice_match:
        value = invoice_match.group("invoice")
        fields.append(
            ExtractedField(
                field_name="invoice_number",
                raw_value=value,
                normalized_value=value,
                confidence=0.98,
                page=1,
                source="digital_pdf_text",
            )
        )

    if amount_match:
        value = amount_match.group("amount")
        fields.append(
            ExtractedField(
                field_name="invoice_total",
                raw_value=f"${value}",
                normalized_value=value.replace(",", ""),
                confidence=0.98,
                page=1,
                source="digital_pdf_text",
            )
        )

    required_fields = {"invoice_number", "invoice_total"}
    found_fields = {field.field_name for field in fields}
    missing = sorted(required_fields - found_fields)
    if missing:
        return ExtractionResult(
            document_type="invoice",
            status="INSUFFICIENT_EVIDENCE",
            fields=tuple(fields),
            errors=(f"required invoice fields missing: {', '.join(missing)}",),
        )

    return ExtractionResult(document_type="invoice", status="EXTRACTED", fields=tuple(fields))


def extract_remittance_summary(path: Path) -> ExtractionResult:
    try:
        page_text = extract_pdf_text(path)
    except ExtractionDocumentError as exc:
        return ExtractionResult(document_type="remittance", status="INVALID_DOCUMENT", errors=(str(exc),))

    if not page_text.strip():
        return ExtractionResult(
            document_type="remittance",
            status="INSUFFICIENT_EVIDENCE",
            errors=("no text layer found",),
        )

    fields: list[ExtractedField] = []
    _append_regex_field(fields, "scenario_id", SCENARIO_RE, "scenario", page_text)
    _append_regex_field(fields, "payment_reference", PAYMENT_REFERENCE_RE, "payment", page_text)
    _append_regex_field(fields, "invoice_number", INVOICE_REFERENCE_RE, "invoice", page_text)
    _append_amount_field(fields, "payment_received", PAYMENT_RECEIVED_RE, page_text)
    _append_amount_field(fields, "claimed_deduction", CLAIMED_DEDUCTION_RE, page_text)
    _append_amount_field(fields, "authorized_promotion", AUTHORIZED_PROMOTION_RE, page_text)

    required_fields = {"payment_reference", "invoice_number", "payment_received"}
    found_fields = {field.field_name for field in fields}
    missing = sorted(required_fields - found_fields)
    if missing:
        return ExtractionResult(
            document_type="remittance",
            status="INSUFFICIENT_EVIDENCE",
            fields=tuple(fields),
            errors=(f"required remittance fields missing: {', '.join(missing)}",),
        )

    return ExtractionResult(document_type="remittance", status="EXTRACTED", fields=tuple(fields))


def extract_promotion_summary(path: Path) -> ExtractionResult:
    try:
        page_text = extract_pdf_text(path)
    except ExtractionDocumentError as exc:
        return ExtractionResult(document_type="promotion", status="INVALID_DOCUMENT", errors=(str(exc),))

    if not page_text.strip():
        return ExtractionResult(
            document_type="promotion",
            status="INSUFFICIENT_EVIDENCE",
            errors=("no text layer found",),
        )

    fields: list[ExtractedField] = []
    _append_regex_field(fields, "promotion_id", PROMOTION_ID_RE, "promotion", page_text)
    _append_amount_field(fields, "authorized_promotion", AUTHORIZED_PROMOTION_RE, page_text)

    required_fields = {"promotion_id", "authorized_promotion"}
    found_fields = {field.field_name for field in fields}
    missing = sorted(required_fields - found_fields)
    if missing:
        return ExtractionResult(
            document_type="promotion",
            status="INSUFFICIENT_EVIDENCE",
            fields=tuple(fields),
            errors=(f"required promotion fields missing: {', '.join(missing)}",),
        )

    return ExtractionResult(document_type="promotion", status="EXTRACTED", fields=tuple(fields))


def extract_pdf_text(path: Path) -> str:
    try:
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except (OSError, PdfReadError, ValueError) as exc:
        raise ExtractionDocumentError("invalid or unreadable PDF") from exc


class ExtractionDocumentError(Exception):
    pass


def _append_regex_field(
    fields: list[ExtractedField],
    field_name: str,
    pattern: re.Pattern[str],
    group_name: str,
    page_text: str,
) -> None:
    match = pattern.search(page_text)
    if not match:
        return
    value = match.group(group_name)
    fields.append(
        ExtractedField(
            field_name=field_name,
            raw_value=value,
            normalized_value=value,
            confidence=0.98,
            page=1,
            source="digital_pdf_text",
        )
    )


def _append_amount_field(
    fields: list[ExtractedField],
    field_name: str,
    pattern: re.Pattern[str],
    page_text: str,
) -> None:
    match = pattern.search(page_text)
    if not match:
        return
    value = match.group("amount")
    fields.append(
        ExtractedField(
            field_name=field_name,
            raw_value=f"${value}",
            normalized_value=value.replace(",", ""),
            confidence=0.98,
            page=1,
            source="digital_pdf_text",
        )
    )
