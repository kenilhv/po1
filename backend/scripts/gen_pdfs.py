"""Generate real test PDFs for stress-testing the upload pipeline.

Run from backend/:  python scripts/gen_pdfs.py
Outputs to /tmp/paycrew_pdfs/
"""
from __future__ import annotations

import os
from pathlib import Path

import fitz

OUT = Path("/tmp/paycrew_pdfs")
OUT.mkdir(parents=True, exist_ok=True)


def make_pdf(name: str, text: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), text, fontsize=11)
    doc.save(str(OUT / name))
    doc.close()


CASES = {
    # Demo-keyword vendors (canned parse)
    "office_low.pdf": "INVOICE\nFrom: OfficeSupplyCo\nPO-8821\nOffice supplies\nAmount: $750.00",
    "tech_dup.pdf": "INVOICE\nVendor: TechSoftware Inc\nSoftware license renewal\nPO-7743\nAmount: $1,200.00",
    "fast_critical.pdf": "INVOICE\nFastConsult LLC\nConsulting services\nAmount: $45,000.00\nBank: ACC-999-SUSPICIOUS",
    # Generic regex parse, unknown vendor
    "unknown_vendor.pdf": "Vendor: Acme Widgets Co\nInvoice Number: INV-ACME-501\nPO Reference: PO-0000\nAmount: $3,200.00\nBank: ACC-777-NEW",
    "big_amount.pdf": "Vendor: MegaCorp Unlimited\nInvoice Number: INV-MEGA-9\nAmount: $250,000.00\nBank: ACC-123",
    # Edge cases
    "empty.pdf": " ",
    "weird_chars.pdf": "Vendor: Robert'); DROP TABLE invoices;--\nInvoice Number: INV-<script>alert(1)</script>\nAmount: $1,000.00",
    "unicode.pdf": "Vendor: Sociedad Anonima Espanola\nInvoice Number: INV-UNI-7\nAmount: EUR 9.999,50\nMontant total: $4200",
    "negative.pdf": "Vendor: Refund Vendor LLC\nInvoice Number: INV-NEG-1\nAmount: $-500.00",
    "no_amount.pdf": "Vendor: NoMoney Ltd\nInvoice Number: INV-NM-1\nPO Reference: PO-XYZ",
}

for fname, body in CASES.items():
    make_pdf(fname, body)

# Corrupt "PDF" (valid extension, invalid content) -> should be handled gracefully
(OUT / "corrupt.pdf").write_bytes(b"%PDF-1.4 this is not a real pdf \x00\x01\x02 garbage")

# Completely empty file
(OUT / "zero_bytes.pdf").write_bytes(b"")

print(f"Generated {len(os.listdir(OUT))} files in {OUT}")
for f in sorted(os.listdir(OUT)):
    print("  ", f)
