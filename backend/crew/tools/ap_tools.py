"""PO1 — database lookups for the AP-grounded agents."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from database.db import get_conn


def lookup_vendor_record(vendor_name: str) -> dict[str, Any] | None:
    """Fetch the vendor master record — the basis for every onboarding check."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM vendors WHERE vendor_name = ?", (vendor_name,)
        ).fetchone()
        return dict(row) if row else None


def lookup_goods_receipt(vendor_name: str, po_reference: str | None) -> dict[str, Any]:
    """Third leg of the 3-way match: did the goods/services actually arrive?"""
    with get_conn() as conn:
        row = None
        if po_reference:
            row = conn.execute(
                "SELECT * FROM goods_receipts WHERE po_number = ?", (po_reference,)
            ).fetchone()
        if row is None and vendor_name:
            row = conn.execute(
                "SELECT * FROM goods_receipts WHERE vendor_name = ? ORDER BY received_at DESC LIMIT 1",
                (vendor_name,),
            ).fetchone()

        if not row:
            return {"found": False, "detail": "No goods receipt on file"}

        return {
            "found": True,
            "po_number": row["po_number"],
            "quantity_received": row["quantity_received"],
            "amount_received": row["amount_received"],
            "received_at": row["received_at"],
        }


def check_budget(cost_center: str, amount: float) -> dict[str, Any]:
    """Compare this spend against what the cost center has already absorbed.

    Deliberately simple: monthly soft caps per cost center. Real systems pull
    this from the GL, but the control shape is the same.
    """
    caps = {
        "Engineering": 50_000.0,
        "Marketing": 25_000.0,
        "Operations": 20_000.0,
        "People": 15_000.0,
        "G&A": 20_000.0,
    }
    cap = caps.get(cost_center, 20_000.0)

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS spent FROM invoices
            WHERE cost_center = ?
              AND decision IN ('AUTO_APPROVED', 'PAID')
              AND created_at >= date('now', 'start of month')
            """,
            (cost_center,),
        ).fetchone()
        spent = float(row["spent"] or 0)

    projected = spent + amount
    return {
        "exceeded": projected > cap,
        "cost_center": cost_center,
        "cap": cap,
        "spent_this_month": spent,
        "projected": projected,
        "detail": (
            f"{cost_center} would reach ${projected:,.0f} of a ${cap:,.0f} monthly cap"
            if projected > cap
            else f"{cost_center}: ${projected:,.0f} of ${cap:,.0f} used"
        ),
    }


def record_exception(invoice_id: int, exc: dict[str, Any], severity: str) -> int:
    """Persist a typed exception so it has an owner and an audit trail."""
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO exceptions (invoice_id, exception_type, severity, owner, evidence)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                invoice_id,
                exc.get("exception_type"),
                severity,
                exc.get("owner"),
                json.dumps(exc.get("evidence") or {}),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def resolve_exception(exception_id: int, resolution: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE exceptions SET resolution = ?, resolved_at = ? WHERE id = ?",
            (resolution, datetime.utcnow().isoformat(), exception_id),
        )
        conn.commit()


def upsert_vendor_bank(vendor_name: str, bank_account: str) -> None:
    """Record an accepted banking change, preserving the prior value."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT bank_account FROM vendors WHERE vendor_name = ?", (vendor_name,)
        ).fetchone()
        now = datetime.utcnow().isoformat()
        if row:
            conn.execute(
                """
                UPDATE vendors
                SET previous_bank_account = ?, bank_account = ?, bank_details_changed_at = ?
                WHERE vendor_name = ?
                """,
                (row["bank_account"], bank_account, now, vendor_name),
            )
        else:
            conn.execute(
                """
                INSERT INTO vendors (vendor_name, bank_account, known, flagged, onboarded_at, trust_score)
                VALUES (?, ?, 1, 0, ?, 0.5)
                """,
                (vendor_name, bank_account, now),
            )
        conn.commit()


def create_payment_run(invoice_ids: list[int], scheduled_for: str, total: float, discount: float) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO payment_runs (scheduled_for, status, invoice_ids, total_amount, discount_captured)
            VALUES (?, 'pending', ?, ?, ?)
            """,
            (scheduled_for, json.dumps(invoice_ids), total, discount),
        )
        conn.commit()
        return int(cur.lastrowid)


def record_payment(
    invoice_id: int,
    vendor_name: str,
    invoice_number: str,
    amount: float,
    provider: str,
    provider_ref: str | None = None,
    payment_run_id: int | None = None,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO payments
                (invoice_id, invoice_number, vendor_name, amount, provider, provider_ref, payment_run_id, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'paid')
            """,
            (invoice_id, invoice_number, vendor_name, amount, provider, provider_ref, payment_run_id),
        )
        conn.execute("UPDATE invoices SET status = 'PAID' WHERE id = ?", (invoice_id,))
        conn.commit()
        return int(cur.lastrowid)


def record_revenue(kind: str, amount: float, customer_ref: str, stripe_ref: str | None = None) -> None:
    """PO1's own income — subscriptions and metered escalation fees."""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO revenue_events (kind, amount, customer_ref, stripe_ref) VALUES (?, ?, ?, ?)",
            (kind, amount, customer_ref, stripe_ref),
        )
        conn.commit()


def revenue_summary() -> dict[str, Any]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT kind, COUNT(*) AS n, COALESCE(SUM(amount), 0) AS total FROM revenue_events GROUP BY kind"
        ).fetchall()
        total = conn.execute("SELECT COALESCE(SUM(amount), 0) AS t FROM revenue_events").fetchone()
    return {
        "total": float(total["t"] or 0),
        "by_kind": [{"kind": r["kind"], "count": r["n"], "total": float(r["total"])} for r in rows],
    }
