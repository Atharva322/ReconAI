from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

from .contracts import ExtractedField, ExtractionResult

INVOICE_RE = re.compile(r"Invoice Number:\s*(?P<invoice>[A-Z0-9-]+)")
AMOUNT_RE = re.compile(r"Invoice Total:\s*\$(?P<amount>[0-9,]+\.[0-9]{2})")


def extract_invoice_summary(path: Path) -> ExtractionResult:
    reader = PdfReader(str(path))
    page_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    if not page_text.strip():
        return ExtractionResult(
            document_type="invoice",
            status="INSUFFICIENT_EVIDENCE",
            errors=("no text layer found",),
        )

    fields: list[ExtractedField] = []
    invoice_match = INVOICE_RE.search(page_text)
    amount_match = AMOUNT_RE.search(page_text)

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

    if len(fields) < 2:
        return ExtractionResult(
            document_type="invoice",
            status="INSUFFICIENT_EVIDENCE",
            fields=tuple(fields),
            errors=("required invoice fields missing",),
        )

    return ExtractionResult(document_type="invoice", status="EXTRACTED", fields=tuple(fields))
