from __future__ import annotations

import os
import sqlite3
from pathlib import Path

# On Render this points at the mounted persistent disk, so human labels and
# ledger history survive redeploys instead of dying with the build's filesystem.
DB_PATH = Path(os.getenv("PO1_DB_PATH", str(Path(__file__).resolve().parent / "invoice_os.db")))


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(invoices)").fetchall()}
    additions = [
        ("risk_reasons", "TEXT"),
        ("evidence", "TEXT"),
        ("approved_by", "TEXT"),
        ("approved_at", "TEXT"),
        ("rejection_reason", "TEXT"),
    ]
    for name, typ in additions:
        if name not in cols:
            conn.execute(f"ALTER TABLE invoices ADD COLUMN {name} {typ}")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            invoice_id INTEGER NOT NULL,
            status TEXT DEFAULT 'processing',
            error TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        )
        """
    )
    cols_audit = {row[1] for row in conn.execute("PRAGMA table_info(audit_log)").fetchall()}
    if "approved_by" not in cols_audit:
        conn.execute("ALTER TABLE audit_log ADD COLUMN approved_by TEXT")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            agent TEXT NOT NULL,
            result TEXT,
            confidence REAL,
            model TEXT,
            status TEXT,
            detail TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # --- PO1 additions: real-world AP structures ---

    # Vendor master: track banking-detail changes (the #1 real AP fraud vector)
    vendor_cols = {row[1] for row in conn.execute("PRAGMA table_info(vendors)").fetchall()}
    for name, typ in [
        ("tax_id", "TEXT"),
        ("bank_details_changed_at", "TEXT"),
        ("previous_bank_account", "TEXT"),
        ("onboarded_at", "TEXT"),
        ("trust_score", "REAL DEFAULT 0.5"),
    ]:
        if name not in vendor_cols:
            conn.execute(f"ALTER TABLE vendors ADD COLUMN {name} {typ}")

    # Invoice: GL coding + payment scheduling fields
    inv_cols = {row[1] for row in conn.execute("PRAGMA table_info(invoices)").fetchall()}
    for name, typ in [
        ("gl_code", "TEXT"),
        ("cost_center", "TEXT"),
        ("payment_terms", "TEXT"),
        ("due_date", "TEXT"),
        ("discount_terms", "TEXT"),
    ]:
        if name not in inv_cols:
            conn.execute(f"ALTER TABLE invoices ADD COLUMN {name} {typ}")

    conn.executescript(
        """
        -- Third leg of the 3-way match: proof goods/services were actually received
        CREATE TABLE IF NOT EXISTS goods_receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            po_number TEXT,
            vendor_name TEXT,
            quantity_received REAL,
            amount_received REAL,
            received_at TEXT DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        );

        -- Typed exceptions, mirroring a real AP exception policy (type -> owner -> SLA)
        CREATE TABLE IF NOT EXISTS exceptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            exception_type TEXT NOT NULL,
            severity TEXT,
            owner TEXT,
            evidence TEXT,
            resolution TEXT,
            resolved_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        );

        -- Payment runs: payment is a scheduled batch decision, not an instant reflex
        CREATE TABLE IF NOT EXISTS payment_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheduled_for TEXT,
            status TEXT DEFAULT 'pending',
            invoice_ids TEXT,
            total_amount REAL,
            discount_captured REAL DEFAULT 0,
            executed_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        -- Terac: both realtime escalations and batch labeling studies
        CREATE TABLE IF NOT EXISTS terac_escalations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER,
            kind TEXT,
            exception_type TEXT,
            question TEXT,
            payload TEXT,
            verdict TEXT,
            reasoning TEXT,
            reviewer_ref TEXT,
            cost REAL,
            requested_at TEXT DEFAULT CURRENT_TIMESTAMP,
            resolved_at TEXT
        );

        -- Before/after proof for the Terac-labels -> Pioneer fine-tune loop
        CREATE TABLE IF NOT EXISTS finetune_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            base_model TEXT,
            target_agent TEXT,
            dataset_ref TEXT,
            label_count INTEGER,
            metric_before REAL,
            metric_after REAL,
            cost_before REAL,
            cost_after REAL,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        -- Revenue: PO1's own subscriptions + metered escalation fees
        CREATE TABLE IF NOT EXISTS revenue_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT,
            amount REAL,
            customer_ref TEXT,
            stripe_ref TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # payments: link to the run that executed it, and how it was paid
    pay_cols = {row[1] for row in conn.execute("PRAGMA table_info(payments)").fetchall()}
    for name, typ in [
        ("invoice_id", "INTEGER"),
        ("payment_run_id", "INTEGER"),
        ("provider", "TEXT"),
        ("provider_ref", "TEXT"),
        ("status", "TEXT DEFAULT 'paid'"),
    ]:
        if name not in pay_cols:
            conn.execute(f"ALTER TABLE payments ADD COLUMN {name} {typ}")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                vendor_name TEXT,
                invoice_number TEXT,
                amount REAL,
                invoice_date TEXT,
                line_items TEXT,
                bank_details TEXT,
                po_reference TEXT,
                status TEXT DEFAULT 'processing',
                risk_score TEXT,
                decision TEXT,
                risk_reasons TEXT,
                evidence TEXT,
                approved_by TEXT,
                approved_at TEXT,
                rejection_reason TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS purchase_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                po_number TEXT UNIQUE,
                vendor_name TEXT,
                amount REAL,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT,
                vendor_name TEXT,
                amount REAL,
                paid_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS vendors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor_name TEXT UNIQUE,
                bank_account TEXT,
                known INTEGER DEFAULT 1,
                flagged INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER,
                agent_name TEXT,
                model_used TEXT,
                input_summary TEXT,
                output_summary TEXT,
                confidence REAL,
                approved_by TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        _migrate(conn)
        conn.commit()
