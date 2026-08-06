from pathlib import Path

from reconai_benchmark.pdf_renderer import render_blank_pdf, render_text_pdf
from reconai_extraction import extract_invoice_summary


def test_digital_invoice_pdf_extracts_basic_fields(tmp_path: Path) -> None:
    pdf_path = tmp_path / "invoice.pdf"
    render_text_pdf(
        pdf_path,
        "Northstar Beverages Invoice",
        [
            "Invoice Number: NSB-INV-1001",
            "Invoice Total: $18,450.00",
        ],
    )

    result = extract_invoice_summary(pdf_path)
    fields = {field.field_name: field for field in result.fields}

    assert result.status == "EXTRACTED"
    assert fields["invoice_number"].normalized_value == "NSB-INV-1001"
    assert fields["invoice_total"].normalized_value == "18450.00"
    assert not result.requires_review


def test_no_text_pdf_is_explicitly_not_trusted(tmp_path: Path) -> None:
    pdf_path = tmp_path / "blank.pdf"
    render_blank_pdf(pdf_path)

    result = extract_invoice_summary(pdf_path)

    assert result.status == "INSUFFICIENT_EVIDENCE"
    assert result.requires_review
    assert result.errors == ("no text layer found",)
