#!/usr/bin/env python3
"""Generate 10 realistic sample invoice PDFs for PayCrew testing.

Run from backend/:  python scripts/generate_sample_pdfs.py
Output: ../sample_invoices/
"""

from __future__ import annotations

from pathlib import Path

import fitz

OUT_DIR = Path(__file__).resolve().parents[2] / "sample_invoices"

# Each entry: filename, expected risk, expected decision, invoice fields + line items
SAMPLES = [
    {
        "file": "01-low-officesupply.pdf",
        "expect": ("LOW", "AUTO_APPROVED"),
        "vendor": "OfficeSupplyCo",
        "vendor_addr": "1200 Commerce Blvd\nSan Francisco, CA 94105",
        "invoice_number": "INV-2024-901",
        "date": "June 10, 2024",
        "due": "July 10, 2024",
        "po": "PO-8821",
        "bank": "ACC-001-VALID",
        "bill_to": "PayCrew Corp\n500 Market Street\nSan Francisco, CA 94103",
        "items": [
            ("Premium Copy Paper (10 reams)", "10", "45.00", "450.00"),
            ("Ballpoint Pens — Box of 50", "5", "22.00", "110.00"),
            ("Stapler Heavy-Duty", "4", "35.00", "140.00"),
            ("Desk Organizers", "2", "50.00", "100.00"),
        ],
        "tax_rate": 0.0,
    },
    {
        "file": "02-low-cleanvendor.pdf",
        "expect": ("LOW", "AUTO_APPROVED"),
        "vendor": "CleanVendor Inc",
        "vendor_addr": "88 Industrial Park Dr\nOakland, CA 94607",
        "invoice_number": "INV-2024-902",
        "date": "June 11, 2024",
        "due": "July 11, 2024",
        "po": "PO-9901",
        "bank": "ACC-003-VALID",
        "bill_to": "PayCrew Corp\n500 Market Street\nSan Francisco, CA 94103",
        "items": [
            ("Monthly Janitorial Service — June", "1", "325.00", "325.00"),
            ("Window Cleaning (Interior)", "1", "75.00", "75.00"),
            ("Restroom Supplies Restock", "1", "75.00", "75.00"),
        ],
        "tax_rate": 0.0,
    },
    {
        "file": "03-low-paperworks.pdf",
        "expect": ("LOW", "AUTO_APPROVED"),
        "vendor": "PaperWorks Ltd",
        "vendor_addr": "44 Mill Road\nPortland, OR 97201",
        "invoice_number": "INV-2024-903",
        "date": "June 12, 2024",
        "due": "July 12, 2024",
        "po": "PO-4412",
        "bank": "ACC-004-VALID",
        "bill_to": "PayCrew Corp\n500 Market Street\nSan Francisco, CA 94103",
        "items": [
            ("A4 Recycled Paper — 5 cases", "5", "45.00", "225.00"),
            ("Cardstock — White 100pk", "2", "40.00", "80.00"),
            ("Shipping Labels Roll", "4", "17.50", "70.00"),
        ],
        "tax_rate": 0.0,
    },
    {
        "file": "04-low-techsoftware.pdf",
        "expect": ("LOW", "AUTO_APPROVED"),
        "vendor": "TechSoftware Inc",
        "vendor_addr": "200 Innovation Way\nAustin, TX 78701",
        "invoice_number": "INV-2024-904",
        "date": "June 13, 2024",
        "due": "July 13, 2024",
        "po": "PO-6612",
        "bank": "ACC-002-VALID",
        "bill_to": "PayCrew Corp\n500 Market Street\nSan Francisco, CA 94103",
        "items": [
            ("Enterprise SaaS License — Annual", "1", "2800.00", "2800.00"),
            ("Premium Support Package", "1", "450.00", "450.00"),
            ("API Integration Module", "1", "250.00", "250.00"),
        ],
        "tax_rate": 0.0,
    },
    {
        "file": "05-high-duplicate.pdf",
        "expect": ("HIGH", "PENDING_CFO"),
        "vendor": "TechSoftware Inc",
        "vendor_addr": "200 Innovation Way\nAustin, TX 78701",
        "invoice_number": "INV-2024-905",
        "date": "June 14, 2024",
        "due": "July 14, 2024",
        "po": "PO-7743",
        "bank": "ACC-002-VALID",
        "bill_to": "PayCrew Corp\n500 Market Street\nSan Francisco, CA 94103",
        "items": [
            ("Software License Renewal — Q2", "1", "1200.00", "1200.00"),
        ],
        "tax_rate": 0.0,
        "note": "Same vendor + amount as paid invoice INV-9891",
    },
    {
        "file": "06-medium-no-po.pdf",
        "expect": ("MEDIUM", "PENDING_AP"),
        "vendor": "PaperWorks Ltd",
        "vendor_addr": "44 Mill Road\nPortland, OR 97201",
        "invoice_number": "INV-2024-906",
        "date": "June 15, 2024",
        "due": "July 15, 2024",
        "po": "PO-MISSING-906",
        "bank": "ACC-004-VALID",
        "bill_to": "PayCrew Corp\n500 Market Street\nSan Francisco, CA 94103",
        "items": [
            ("Emergency Paper Restock", "3", "85.00", "255.00"),
            ("Express Delivery Fee", "1", "45.00", "45.00"),
            ("Rush Processing", "1", "25.00", "25.00"),
        ],
        "tax_rate": 0.0,
        "note": "Invalid PO on file — should flag MEDIUM",
    },
    {
        "file": "07-critical-fraud.pdf",
        "expect": ("CRITICAL", "BLOCKED"),
        "vendor": "FastConsult LLC",
        "vendor_addr": "1 Shell Company Lane\nWilmington, DE 19801",
        "invoice_number": "INV-F-0042",
        "date": "June 16, 2024",
        "due": "June 30, 2024",
        "po": None,
        "bank": "ACC-999-SUSPICIOUS",
        "bill_to": "PayCrew Corp\n500 Market Street\nSan Francisco, CA 94103",
        "items": [
            ("Strategic Consulting — Phase 1", "1", "35000.00", "35000.00"),
            ("Executive Advisory Retainer", "1", "10000.00", "10000.00"),
        ],
        "tax_rate": 0.0,
    },
    {
        "file": "08-critical-unknown-vendor.pdf",
        "expect": ("CRITICAL", "BLOCKED"),
        "vendor": "ApexShell Corp",
        "vendor_addr": "999 Unknown Ave\nLas Vegas, NV 89101",
        "invoice_number": "INV-2024-908",
        "date": "June 16, 2024",
        "due": "July 16, 2024",
        "po": "PO-0000",
        "bank": "ACC-UNKNOWN-88",
        "bill_to": "PayCrew Corp\n500 Market Street\nSan Francisco, CA 94103",
        "items": [
            ("Miscellaneous Services", "1", "3200.00", "3200.00"),
        ],
        "tax_rate": 0.0,
    },
    {
        "file": "09-critical-large-no-po.pdf",
        "expect": ("CRITICAL", "BLOCKED"),
        "vendor": "OfficeSupplyCo",
        "vendor_addr": "1200 Commerce Blvd\nSan Francisco, CA 94105",
        "invoice_number": "INV-2024-909",
        "date": "June 16, 2024",
        "due": "August 16, 2024",
        "po": "PO-MISSING-909",
        "bank": "ACC-001-VALID",
        "bill_to": "PayCrew Corp\n500 Market Street\nSan Francisco, CA 94103",
        "items": [
            ("Bulk Office Furniture — 50 desks", "50", "280.00", "14000.00"),
            ("Ergonomic Chairs", "50", "90.00", "4500.00"),
        ],
        "tax_rate": 0.0,
    },
    {
        "file": "10-medium-bank-mismatch.pdf",
        "expect": ("MEDIUM", "PENDING_AP"),
        "vendor": "CleanVendor Inc",
        "vendor_addr": "88 Industrial Park Dr\nOakland, CA 94607",
        "invoice_number": "INV-2024-910",
        "date": "June 16, 2024",
        "due": "July 16, 2024",
        "po": "PO-9901",
        "bank": "ACC-FAKE-WRONG-99",
        "bill_to": "PayCrew Corp\n500 Market Street\nSan Francisco, CA 94103",
        "items": [
            ("Deep Clean — Office Floor 3", "1", "255.00", "255.00"),
            ("Carpet Shampooing", "1", "125.00", "125.00"),
            ("Sanitizer Supply Kit", "2", "50.00", "100.00"),
        ],
        "tax_rate": 0.0,
    },
]


def _draw_invoice(spec: dict) -> fitz.Document:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)  # US Letter

    subtotal = sum(float(row[3]) for row in spec["items"])
    tax = round(subtotal * spec.get("tax_rate", 0), 2)
    total = round(subtotal + tax, 2)

    # Colors
    dark = (0.12, 0.14, 0.18)
    muted = (0.45, 0.48, 0.55)
    accent = (0.39, 0.40, 0.95)
    line = (0.85, 0.86, 0.90)

    y = 48

    # Header bar
    page.draw_rect(fitz.Rect(0, 0, 612, 72), color=accent, fill=accent)
    page.insert_text((48, 46), spec["vendor"].upper(), fontsize=18, fontname="hebo", color=(1, 1, 1))
    page.insert_text((400, 46), "INVOICE", fontsize=22, fontname="hebo", color=(1, 1, 1))

    y = 96
    page.insert_text((48, y), spec["vendor"], fontsize=11, fontname="hebo", color=dark)
    y += 14
    for line_text in spec["vendor_addr"].split("\n"):
        page.insert_text((48, y), line_text, fontsize=9, color=muted)
        y += 12

    # Invoice meta (right column)
    meta_x = 380
    meta_y = 96
    meta_lines = [
        ("Invoice #:", spec["invoice_number"]),
        ("Date:", spec["date"]),
        ("Due Date:", spec["due"]),
    ]
    if spec.get("po"):
        meta_lines.append(("PO #:", spec["po"]))
    for label, val in meta_lines:
        page.insert_text((meta_x, meta_y), label, fontsize=9, fontname="hebo", color=muted)
        page.insert_text((meta_x + 72, meta_y), val, fontsize=9, color=dark)
        meta_y += 16

    y = max(y, meta_y) + 20

    # Bill To
    page.insert_text((48, y), "BILL TO", fontsize=8, fontname="hebo", color=muted)
    y += 14
    for line_text in spec["bill_to"].split("\n"):
        page.insert_text((48, y), line_text, fontsize=9, color=dark)
        y += 12

    y += 16
    page.draw_line((48, y), (564, y), color=line, width=0.5)
    y += 18

    # Table header
    cols = [(48, "DESCRIPTION"), (340, "QTY"), (400, "UNIT PRICE"), (490, "AMOUNT")]
    for x, hdr in cols:
        page.insert_text((x, y), hdr, fontsize=8, fontname="hebo", color=muted)
    y += 8
    page.draw_line((48, y), (564, y), color=line, width=0.5)
    y += 16

    for desc, qty, unit, amt in spec["items"]:
        page.insert_text((48, y), desc, fontsize=9, color=dark)
        page.insert_text((340, y), qty, fontsize=9, color=dark)
        page.insert_text((400, y), f"${unit}", fontsize=9, color=dark)
        page.insert_text((490, y), f"${amt}", fontsize=9, color=dark)
        y += 18

    y += 8
    page.draw_line((48, y), (564, y), color=line, width=0.5)
    y += 20

    # Totals
    page.insert_text((400, y), "Subtotal:", fontsize=9, color=muted)
    page.insert_text((490, y), f"${subtotal:,.2f}", fontsize=9, color=dark)
    y += 16
    if tax:
        page.insert_text((400, y), "Tax:", fontsize=9, color=muted)
        page.insert_text((490, y), f"${tax:,.2f}", fontsize=9, color=dark)
        y += 16
    page.insert_text((400, y), "TOTAL DUE:", fontsize=11, fontname="hebo", color=dark)
    page.insert_text((490, y), f"${total:,.2f}", fontsize=11, fontname="hebo", color=accent)

    y += 40
    page.draw_rect(fitz.Rect(48, y, 564, y + 80), color=line, width=0.5)
    y += 16
    page.insert_text((60, y), "PAYMENT DETAILS", fontsize=8, fontname="hebo", color=muted)
    y += 16
    page.insert_text((60, y), f"Bank Account: {spec['bank']}", fontsize=9, color=dark)
    y += 14
    page.insert_text((60, y), "Wire transfer within 30 days. Include invoice number in reference.", fontsize=8, color=muted)

    # Parser fields block (must be extractable as plain text)
    parser_lines = [
        f"Vendor: {spec['vendor']}",
        f"Invoice Number: {spec['invoice_number']}",
        f"Amount: ${total:,.2f}",
        f"Total: ${total:,.2f}",
    ]
    if spec.get("po"):
        parser_lines.append(f"PO Reference: {spec['po']}")
    parser_lines.append(f"Bank Account: {spec['bank']}")

    box_height = 28 + len(parser_lines) * 14 + (16 if spec.get("note") else 0)
    if y + box_height > 760:
        page = doc.new_page(width=612, height=792)
        y = 48
    page.draw_rect(fitz.Rect(48, y, 564, y + box_height), color=(0.95, 0.96, 0.98), fill=(0.95, 0.96, 0.98))
    y += 18
    page.insert_text((60, y), "— SYSTEM EXTRACTION FIELDS —", fontsize=7, fontname="hebo", color=muted)
    y += 16
    for pl in parser_lines:
        page.insert_text((60, y), pl, fontsize=8, color=dark)
        y += 14

    if spec.get("note"):
        y += 4
        page.insert_text((60, y), f"Note: {spec['note']}", fontsize=7, color=muted)

    return doc


def generate_all() -> list[dict]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    for spec in SAMPLES:
        path = OUT_DIR / spec["file"]
        doc = _draw_invoice(spec)
        doc.save(str(path))
        doc.close()
        manifest.append({**spec, "path": str(path)})
        print(f"  Created {path.name}")
    return manifest


if __name__ == "__main__":
    print(f"Generating sample invoices → {OUT_DIR}\n")
    generate_all()
    print(f"\nDone. {len(SAMPLES)} PDFs ready.")
