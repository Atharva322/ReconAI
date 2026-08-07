from pathlib import Path

from reconai_benchmark.pdf_renderer import render_blank_pdf, render_text_pdf
from reconai_extraction import extract_invoice_summary, extract_remittance_summary


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


def test_digital_remittance_pdf_extracts_basic_fields(tmp_path: Path) -> None:
    pdf_path = tmp_path / "remittance.pdf"
    render_text_pdf(
        pdf_path,
        "Northstar Beverages Remittance",
        [
            "Payment Reference: PAY-NORTHSTAR-0001",
            "Invoice Reference: NSB-INV-1001",
            "Payment Received: $17,200.00",
            "Authorized Promotion: $1,000.00",
        ],
    )

    result = extract_remittance_summary(pdf_path)
    fields = {field.field_name: field for field in result.fields}

    assert result.status == "EXTRACTED"
    assert fields["payment_reference"].normalized_value == "PAY-NORTHSTAR-0001"
    assert fields["invoice_number"].normalized_value == "NSB-INV-1001"
    assert fields["payment_received"].normalized_value == "17200.00"
    assert fields["authorized_promotion"].normalized_value == "1000.00"
    assert fields["payment_received"].raw_value == "$17,200.00"
    assert fields["payment_received"].page == 1
    assert fields["payment_received"].source == "digital_pdf_text"


def test_no_text_pdf_is_explicitly_not_trusted(tmp_path: Path) -> None:
    pdf_path = tmp_path / "blank.pdf"
    render_blank_pdf(pdf_path)

    result = extract_invoice_summary(pdf_path)

    assert result.status == "INSUFFICIENT_EVIDENCE"
    assert result.requires_review
    assert result.errors == ("no text layer found",)


def test_corrupt_pdf_returns_invalid_document(tmp_path: Path) -> None:
    pdf_path = tmp_path / "corrupt.pdf"
    pdf_path.write_bytes(b"not actually a pdf")

    result = extract_invoice_summary(pdf_path)

    assert result.status == "INVALID_DOCUMENT"
    assert result.requires_review
    assert result.fields == ()
    assert result.errors == ("invalid or unreadable PDF",)


def test_missing_invoice_required_field_is_insufficient_evidence(tmp_path: Path) -> None:
    pdf_path = tmp_path / "invoice_missing_total.pdf"
    render_text_pdf(pdf_path, "Northstar Beverages Invoice", ["Invoice Number: NSB-INV-1001"])

    result = extract_invoice_summary(pdf_path)

    assert result.status == "INSUFFICIENT_EVIDENCE"
    assert result.requires_review
    assert result.errors == ("required invoice fields missing: invoice_total",)


def test_missing_remittance_required_field_is_insufficient_evidence(tmp_path: Path) -> None:
    pdf_path = tmp_path / "remittance_missing_payment.pdf"
    render_text_pdf(
        pdf_path,
        "Northstar Beverages Remittance",
        [
            "Payment Reference: PAY-NORTHSTAR-0001",
            "Invoice Reference: NSB-INV-1001",
            "Authorized Promotion: $1,000.00",
        ],
    )

    result = extract_remittance_summary(pdf_path)

    assert result.status == "INSUFFICIENT_EVIDENCE"
    assert result.requires_review
    assert result.errors == ("required remittance fields missing: payment_received",)
