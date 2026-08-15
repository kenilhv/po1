"""Run: python -m database.seed (from backend/)

Seeds 5 demo invoices (2 LOW, 1 MEDIUM #10 bank mismatch, 1 HIGH, 1 CRITICAL #9) with full
agent traces and audit-log entries.
"""

from __future__ import annotations

import json

from database.db import get_conn, init_db

CHEAP = "gpt-3.5-turbo"
EXPENSIVE = "gpt-4o"


def _all_pass(vendor: str, amount: int, number: str, po: str):
    return [
        ("invoice_parser", f"Extracted: {vendor}, ${amount:,}, {number}", 99, CHEAP, "pass", f"Extracted: {vendor}, ${amount:,}, {number}"),
        ("po_matcher", f"Matched {po}", 95, CHEAP, "pass", f"Matched {po}"),
        ("duplicate_detector", "No duplicate found", 97, CHEAP, "pass", "No duplicate found"),
        ("fraud_signal", "Vendor verified", 91, EXPENSIVE, "pass", "Vendor verified"),
        ("risk_scorer", "Risk: LOW — all checks passed", 94, EXPENSIVE, "route", "Risk: LOW — all checks passed"),
        ("approval_router", "Auto approved", None, CHEAP, "route", "Auto approved"),
    ]


# (number, vendor, amount, risk, decision, status, risk_reasons, evidence, created_at, agents)
INVOICES = [
    (
        "INV-2024-441", "OfficeSupplyCo", 800, "LOW", "AUTO_APPROVED", "auto_approved",
        None, None, "2024-06-14T09:12:00",
        _all_pass("OfficeSupplyCo", 800, "INV-2024-441", "PO-8821"),
    ),
    (
        "INV-2024-442", "TechSoftware Inc", 3500, "LOW", "AUTO_APPROVED", "auto_approved",
        None, None, "2024-06-14T10:30:00",
        _all_pass("TechSoftware Inc", 3500, "INV-2024-442", "PO-6612"),
    ),
    (
        "INV-2024-910", "CleanVendor Inc", 480, "MEDIUM", "PENDING_AP", "pending_ap",
        ["Bank account mismatch"],
        "Bank account ACC-FAKE-WRONG-99 does not match vendor registry ACC-003-VALID.",
        "2024-06-14T14:05:00",
        [
            ("invoice_parser", "parsed", 90, CHEAP, "pass", "Extracted CleanVendor Inc $480"),
            ("po_matcher", "match_found", 95, CHEAP, "pass", "Matched PO-9901"),
            ("duplicate_detector", "clean", 97, CHEAP, "pass", "No duplicate found"),
            ("fraud_signal", "signals_found", 88, EXPENSIVE, "warn", "Bank account mismatch"),
            ("risk_scorer", "MEDIUM", 90, EXPENSIVE, "route", "Bank account mismatch"),
            ("approval_router", "pending_ap", 97, CHEAP, "route", "Flagged for AP review"),
        ],
    ),
    (
        "INV-2024-447", "GlobalSupplier", 15000, "HIGH", "PENDING_CFO", "pending_cfo",
        ["No PO found", "New vendor", "Large amount"],
        "New vendor with no purchase history. $15,000 invoice with no matching PO. Escalated to CFO.",
        "2024-06-14T16:15:00",
        [
            ("invoice_parser", "Extracted: GlobalSupplier, $15,000, INV-2024-447", 96, CHEAP, "pass", "Extracted: GlobalSupplier, $15,000, INV-2024-447"),
            ("po_matcher", "No PO found", 85, CHEAP, "fail", "No PO found"),
            ("duplicate_detector", "No duplicate found", 94, CHEAP, "pass", "No duplicate found"),
            ("fraud_signal", "New vendor — unverified", 78, EXPENSIVE, "warn", "New vendor — unverified"),
            ("risk_scorer", "Risk: HIGH — new vendor, large amount", 84, EXPENSIVE, "route", "Risk: HIGH — new vendor, large amount"),
            ("approval_router", "Escalated to CFO", None, CHEAP, "route", "Escalated to CFO"),
        ],
    ),
    (
        "INV-2024-909", "OfficeSupplyCo", 18500, "CRITICAL", "BLOCKED", "escalated",
        ["No PO found", "Large amount"],
        "Large amount without purchase order match. PO-MISSING-909 not found for vendor OfficeSupplyCo.",
        "2024-06-14T17:00:00",
        [
            ("invoice_parser", "parsed", 90, CHEAP, "pass", "Extracted OfficeSupplyCo $18,500"),
            ("po_matcher", "no_match", 70, CHEAP, "fail", "PO-MISSING-909 not found for vendor OfficeSupplyCo"),
            ("duplicate_detector", "clean", 92, CHEAP, "pass", "No duplicate found"),
            ("fraud_signal", "clean", 88, EXPENSIVE, "pass", "Vendor verified"),
            ("risk_scorer", "CRITICAL", 90, EXPENSIVE, "route", "Large amount without purchase order match"),
            ("approval_router", "blocked", 97, CHEAP, "route", "Routed as BLOCKED. Human approval required for payment."),
        ],
    ),
]


def seed() -> None:
    init_db()
    with get_conn() as conn:
        conn.execute("DELETE FROM agent_results")
        conn.execute("DELETE FROM jobs")
        conn.execute("DELETE FROM audit_log")
        conn.execute("DELETE FROM invoices")
        conn.execute("DELETE FROM payments")
        conn.execute("DELETE FROM purchase_orders")
        conn.execute("DELETE FROM vendors")

        try:
            conn.execute("DELETE FROM sqlite_sequence")
        except Exception:
            pass

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
            ("PO-6612", "TechSoftware Inc", 3500.0, "Software license"),
            ("PO-7743", "TechSoftware Inc", 1200.0, "Software license renewal"),
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

        for (number, vendor, amount, risk, decision, status, reasons, evidence, created_at, agents) in INVOICES:
            cur = conn.execute(
                """
                INSERT INTO invoices
                  (filename, vendor_name, invoice_number, amount, status, risk_score, decision, risk_reasons, evidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{number}.pdf", vendor, number, float(amount), status, risk, decision,
                    json.dumps(reasons) if reasons else None,
                    evidence, created_at,
                ),
            )
            invoice_id = cur.lastrowid

            for (agent_id, result, confidence, model, ag_status, detail) in agents:
                conn.execute(
                    """
                    INSERT INTO agent_results (invoice_id, agent, result, confidence, model, status, detail, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (invoice_id, agent_id, result, confidence, model, ag_status, detail, created_at),
                )
                conn.execute(
                    """
                    INSERT INTO audit_log
                      (invoice_id, agent_name, model_used, input_summary, output_summary, confidence, approved_by, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        invoice_id, agent_id, model, detail[:200], result, confidence,
                        "System" if decision == "AUTO_APPROVED" else "—",
                        created_at,
                    ),
                )

        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
        print(f"Seed complete. {count} invoices loaded.")


if __name__ == "__main__":
    seed()
