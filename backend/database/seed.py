"""Run: python -m database.seed (from backend/)"""

from __future__ import annotations

from database.db import get_conn, init_db


def seed() -> None:
    init_db()
    with get_conn() as conn:
        conn.execute("DELETE FROM vendors")
        conn.execute("DELETE FROM purchase_orders")
        conn.execute("DELETE FROM payments")
        conn.execute("DELETE FROM audit_log")
        conn.execute("DELETE FROM invoices")

        vendors = [
            ("OfficeSupplyCo", "ACC-001-VALID", 1, 0),
            ("TechSoftware Inc", "ACC-002-VALID", 1, 0),
            ("FastConsult LLC", "ACC-999-SUSPICIOUS", 0, 1),
            ("CleanVendor Inc", "ACC-003-VALID", 1, 0),
            ("PaperWorks Ltd", "ACC-004-VALID", 1, 0),
        ]
        conn.executemany(
            "INSERT INTO vendors (vendor_name, bank_account, known, flagged) VALUES (?, ?, ?, ?)",
            vendors,
        )

        pos = [
            ("PO-8821", "OfficeSupplyCo", 800.0, "Office supplies Q1"),
            ("PO-7743", "TechSoftware Inc", 1200.0, "Software license"),
            ("PO-9901", "CleanVendor Inc", 500.0, "Cleaning services"),
            ("PO-4412", "PaperWorks Ltd", 350.0, "Paper order"),
        ]
        conn.executemany(
            "INSERT INTO purchase_orders (po_number, vendor_name, amount, description) VALUES (?, ?, ?, ?)",
            pos,
        )

        payments = [
            ("INV-9891", "TechSoftware Inc", 1200.0),
            ("INV-2024-100", "CleanVendor Inc", 500.0),
            ("INV-2024-200", "PaperWorks Ltd", 350.0),
        ]
        conn.executemany(
            "INSERT INTO payments (invoice_number, vendor_name, amount) VALUES (?, ?, ?)",
            payments,
        )
        conn.commit()
        print("Seed complete.")


if __name__ == "__main__":
    seed()
