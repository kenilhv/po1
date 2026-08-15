"""PO1 — seed realistic AP data covering each exception type.

Six scenarios, each exercising a different path through the pipeline, so the
demo can show clean auto-pay, a caught banking change, a price variance, an
unauthorized large invoice, a duplicate, and a missing goods receipt.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from database.db import get_conn, init_db


def seed() -> None:
    init_db()
    now = datetime.utcnow()
    recent = (now - timedelta(days=3)).isoformat()

    with get_conn() as conn:
        conn.executescript(
            "DELETE FROM vendors; DELETE FROM purchase_orders; "
            "DELETE FROM goods_receipts; DELETE FROM payments;"
        )

        # --- vendor master: tax IDs, banking, trust built over time
        conn.executemany(
            """
            INSERT INTO vendors
                (vendor_name, bank_account, known, flagged, tax_id, onboarded_at, trust_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("OfficeSupplyCo",   "ACC-001-VALID", 1, 0, "94-1234567", "2024-01-15", 0.95),
                ("TechSoftware Inc", "ACC-002-VALID", 1, 0, "94-2345678", "2024-03-02", 0.90),
                ("CleanVendor Inc",  "ACC-003-VALID", 1, 0, "94-3456789", "2024-02-20", 0.88),
                ("PaperWorks Ltd",   "ACC-004-VALID", 1, 0, "94-4567890", "2024-05-11", 0.82),
                ("AWS",              "ACC-005-VALID", 1, 0, "91-1144442", "2024-01-05", 0.97),
                # No tax ID, brand new, low trust — will trip unknown_vendor
                ("FastConsult LLC",  "ACC-999-NEW",   1, 0, None,        "2026-08-14", 0.15),
            ],
        )

        # --- purchase orders (leg 1 of the 3-way match)
        conn.executemany(
            "INSERT INTO purchase_orders (po_number, vendor_name, amount, description) VALUES (?,?,?,?)",
            [
                ("PO-8821", "OfficeSupplyCo",   800.00,  "Q3 office supplies"),
                ("PO-7743", "TechSoftware Inc", 1200.00, "Annual license renewal"),
                ("PO-9901", "CleanVendor Inc",  500.00,  "Monthly cleaning service"),
                ("PO-4412", "PaperWorks Ltd",   350.00,  "Paper stock"),
                ("PO-5500", "AWS",              12000.00, "Cloud infrastructure — Q3"),
            ],
        )

        # --- goods receipts (leg 3). PO-4412 deliberately has none.
        conn.executemany(
            """
            INSERT INTO goods_receipts
                (po_number, vendor_name, quantity_received, amount_received, received_at, notes)
            VALUES (?,?,?,?,?,?)
            """,
            [
                ("PO-8821", "OfficeSupplyCo",   1, 800.00,   recent, "Delivered in full"),
                ("PO-7743", "TechSoftware Inc", 1, 1200.00,  recent, "License keys issued"),
                ("PO-9901", "CleanVendor Inc",  1, 500.00,   recent, "Service completed"),
                ("PO-5500", "AWS",              1, 12000.00, recent, "Usage confirmed"),
            ],
        )

        # --- payment history, so the duplicate check has something to catch
        conn.executemany(
            """
            INSERT INTO payments (invoice_number, vendor_name, amount, provider, status)
            VALUES (?,?,?,?,'paid')
            """,
            [
                ("INV-9891", "TechSoftware Inc", 1200.00, "po1_disbursement"),
                ("INV-2024-100", "PaperWorks Ltd", 350.00, "po1_disbursement"),
            ],
        )
        conn.commit()

    print("Seeded vendor master, POs, goods receipts, and payment history.")


SCENARIOS = [
    ("Clean auto-pay",      "OfficeSupplyCo",   800.00,  "PO-8821", "ACC-001-VALID", "clean"),
    ("Banking change",      "CleanVendor Inc",  480.00,  "PO-9901", "ACC-FAKE-WRONG-99", "vendor_bank_change"),
    ("Price variance",      "TechSoftware Inc", 1850.00, "PO-7743", "ACC-002-VALID", "price_variance"),
    ("Unauthorized spend",  "FastConsult LLC",  45000.00, None,     "ACC-999-NEW",  "unknown_vendor"),
    ("Missing receipt",     "PaperWorks Ltd",   375.00,  "PO-4412", "ACC-004-VALID", "missing_receipt"),
    ("Large clean invoice", "AWS",              12000.00, "PO-5500", "ACC-005-VALID", "clean"),
]


if __name__ == "__main__":
    seed()
