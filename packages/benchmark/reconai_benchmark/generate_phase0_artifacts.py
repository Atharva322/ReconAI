from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reconai_benchmark.golden import GOLDEN_NORTHSTAR_TRUTH
from reconai_benchmark.pdf_renderer import render_blank_pdf, render_text_pdf


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    generated_dir = root / "data" / "generated"
    truth_dir = root / "data" / "ground_truth"
    truth_dir.mkdir(parents=True, exist_ok=True)

    (truth_dir / "golden_northstar.json").write_text(
        json.dumps(GOLDEN_NORTHSTAR_TRUTH, indent=2) + "\n",
        encoding="utf-8",
    )

    render_text_pdf(
        generated_dir / "northstar_invoice.pdf",
        "Northstar Beverages Invoice",
        [
            "Tenant: Northstar Beverages",
            "Retailer: Fictional Market Co.",
            "Invoice Number: NSB-INV-1001",
            "Purchase Order: PO-FMC-2026-001",
            "Invoice Total: $18,450.00",
        ],
    )
    render_text_pdf(
        generated_dir / "northstar_remittance.pdf",
        "Northstar Beverages Remittance",
        [
            "Payment Reference: PAY-NORTHSTAR-0001",
            "Invoice Reference: NSB-INV-1001",
            "Payment Received: $17,200.00",
            "Claimed Deduction: $1,250.00",
            "Promotion Code: PROMO-SUMMER-1000",
        ],
    )
    render_blank_pdf(generated_dir / "northstar_no_text_scan.pdf")


if __name__ == "__main__":
    main()
