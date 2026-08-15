from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "invoice_os.db"


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
