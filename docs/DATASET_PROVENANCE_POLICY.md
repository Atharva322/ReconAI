# Dataset Provenance Policy

ReconAI Phase 0 uses generated fictional data only.

## Rules

- Northstar Beverages, retailers, people, references, invoices, remittances, and promotions are fictional.
- Canonical JSON is the source of truth; PDFs are rendered evidence derived from that truth.
- Generated artifacts must be reproducible from checked-in code and fixed scenario identifiers.
- Do not commit real invoices, remittances, bank data, account numbers, addresses, customer records, or proprietary retailer documents.
- If external public samples are ever introduced, record source URL, license, access date, and reason for inclusion before committing them.
- Benchmark metrics must disclose that the dataset is generated/synthetic.

## Phase 0 Artifacts

- `data/ground_truth/golden_northstar.json`
- `data/generated/northstar_invoice.pdf`
- `data/generated/northstar_remittance.pdf`
- `data/generated/northstar_no_text_scan.pdf`
