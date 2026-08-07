from __future__ import annotations

PAYMENT_MODES = ("ACH", "wire", "check")
CURRENCIES = ("USD",)
DEDUCTION_REASONS = (
    "PROMOTION",
    "SHORTAGE",
    "PRICE_DIFFERENCE",
    "UNAUTHORIZED_ALLOWANCE",
    "DUPLICATE_CLAIM",
)
INVOICE_AMOUNT_BUCKETS_CENTS = (
    (2_500_00, 7_500_00),
    (7_500_00, 15_000_00),
    (15_000_00, 30_000_00),
)
PAYMENT_DELAY_DAYS = (7, 14, 21, 30, 45)

INVOICE_TEMPLATES = (
    "invoice_basic_v2",
    "invoice_table_v1",
    "invoice_compact_v1",
    "invoice_retailer_v1",
)
REMITTANCE_TEMPLATES = (
    "remittance_advice_v1",
    "payment_advice_table_v1",
    "remittance_multi_invoice_v1",
    "remittance_compact_v1",
)
PROMOTION_TEMPLATES = ("promotion_agreement_v1", "promotion_allowance_v1")
DEGRADATIONS = (
    "clean_digital",
    "low_resolution_metadata",
    "rotation_metadata",
    "cropped_field_metadata",
    "image_only",
)

FAMILY_COUNTS = {
    "exact_full_payment": 20,
    "valid_deduction": 15,
    "promotion_overclaim": 15,
    "partial_payment": 15,
    "one_payment_multiple_invoices": 10,
    "multiple_payments_one_invoice": 10,
    "missing_remittance": 10,
    "incorrect_invoice_reference": 10,
    "duplicate_invoice_remittance": 10,
    "unauthorized_deduction": 10,
    "amount_extraction_degradation": 10,
    "reference_extraction_degradation": 5,
    "image_only_no_text": 5,
    "contradictory_evidence": 5,
}
