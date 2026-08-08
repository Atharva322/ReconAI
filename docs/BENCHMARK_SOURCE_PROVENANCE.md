# Benchmark Source Provenance

ReconAI's linked financial benchmark is generated from project-owned canonical truth. Public datasets are used only as reference material for realistic concepts such as payment linkage, remittance vocabulary, payment timing and document variation.

No raw public dataset rows, invoice images, remittance documents or private financial records are stored in this repository.

| Source | URL | Access Date | License Status | Informs | Raw Rows Stored | Raw Documents Redistributed |
|---|---|---|---|---|---|---|
| MSME Invoices & Transactions | `https://www.kaggle.com/datasets/kiruthikas005/msme-invoices-and-transactions` | 2026-08-07 | Unknown from project context | Invoice-to-transaction linkage, payment status, payment dates | No | No |
| Global B2B Invoice & Payments datasets on Kaggle | Kaggle public dataset listings | 2026-08-07 | Varies/verify before use | Amount distributions, payment timing, B2B status vocabulary | No | No |
| Remittance datasets on Hugging Face, including `chandraReddy/remittanceDataset` | Hugging Face dataset listings | 2026-08-07 | Unknown from project context | Remittance field vocabulary such as invoice reference, transaction reference and remittance date | No | No |
| RVL-CDIP-derived invoice extraction datasets | Hugging Face dataset listings | 2026-08-07 | Verify upstream image license before redistribution | Scanned-document characteristics, OCR text variation, invoice field vocabulary | No | No |

## Generation Policy

- Canonical financial truth is generated first.
- Invoice, remittance and promotion evidence are rendered from that canonical truth.
- Expected workflow outcomes are stored only in ground truth JSON and reports.
- Rendered evidence must not contain benchmark labels such as `Expected Status` or expected review reasons.
- Public datasets are not required for normal tests, generation or evaluation.

## Current Limitation

The v2 benchmark includes missing-remittance, one-payment-to-many-invoices and many-payments-to-one-invoice cases as generated truth, but the current production domain reconciler still scores complete one invoice/payment/remittance evidence sets. Those families are therefore reported as unsupported by the current reconciliation scorer rather than counted as successful.
