"""Generate demo invoice PDFs. Run: python scripts/create_demo_invoices.py"""

from __future__ import annotations

from pathlib import Path

import fitz

OUT = Path(__file__).resolve().parents[1] / "demo_invoices"
OUT.mkdir(exist_ok=True)

INVOICES = [
    (
        "invoice_good.pdf",
        """
INVOICE
Vendor: OfficeSupplyCo
Invoice Number: INV-2024-441
Amount: $800.00
Date: 2024-03-01
PO Reference: PO-8821
Bank Account: ACC-001-VALID
Line Items: Office chairs x4, desks x2
""",
    ),
    (
        "invoice_duplicate.pdf",
        """
INVOICE
Vendor: TechSoftware Inc
Invoice Number: INV-9921
Amount: $1,200.00
Date: 2024-03-10
PO Reference: PO-7743
Bank Account: ACC-002-VALID
Notes: Related to prior payment INV-9891
Line Items: Annual software license
""",
    ),
    (
        "invoice_fraud.pdf",
        """
INVOICE
Vendor: FastConsult LLC
Invoice Number: INV-F-0042
Amount: $45,000.00
Date: 2024-03-12
Bank Account: ACC-999-SUSPICIOUS
Line Items: Consulting services - urgent
""",
    ),
]


def main() -> None:
    for filename, body in INVOICES:
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), body.strip(), fontsize=11)
        path = OUT / filename
        doc.save(path)
        doc.close()
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
