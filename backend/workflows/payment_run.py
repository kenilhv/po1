"""PO1 — the scheduled payment run (Render Workflow).

Real AP departments don't pay each invoice the instant it clears; they batch
approved invoices into runs and time them against discount windows and due
dates. This is that cycle, running unattended on a schedule.

Each pass:
  1. Collect invoices approved but not yet paid.
  2. Pay anything whose early-payment discount window closes before the next run.
  3. Pay anything reaching its net due date.
  4. Send remittance advice for everything paid.
  5. Poll open Terac escalations and resume any that a human has now ruled on.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from crew.agents.ap_rules import schedule_payment  # noqa: E402
from crew.tools.ap_tools import create_payment_run  # noqa: E402
from database.db import get_conn, init_db  # noqa: E402
from integrations import linq_client as linq  # noqa: E402
from integrations import payments  # noqa: E402

RUN_INTERVAL_HOURS = int(os.getenv("PO1_RUN_INTERVAL_HOURS", "1"))


def due_invoices() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, vendor_name, invoice_number, amount, payment_terms, invoice_date
            FROM invoices
            WHERE decision IN ('AUTO_APPROVED', 'SCHEDULED', 'APPROVED')
              AND status != 'PAID'
            ORDER BY id
            """
        ).fetchall()
    return [dict(r) for r in rows]


def resume_resolved_escalations() -> int:
    """Pick up invoices a human ruled on since the last run."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT e.invoice_id, e.verdict, e.reasoning, i.vendor_name, i.amount
            FROM terac_escalations e
            JOIN invoices i ON i.id = e.invoice_id
            WHERE e.verdict IS NOT NULL
              AND i.status NOT IN ('PAID', 'REJECTED')
            """
        ).fetchall()

        resumed = 0
        for r in rows:
            verdict = str(r["verdict"]).upper()
            new_state = "AUTO_APPROVED" if verdict in ("APPROVE", "APPROVED") else "REJECTED"
            conn.execute(
                "UPDATE invoices SET decision = ?, status = ? WHERE id = ?",
                (new_state, new_state, r["invoice_id"]),
            )
            resumed += 1
        conn.commit()
    return resumed


def main() -> None:
    init_db()
    now = datetime.utcnow()
    horizon = now + timedelta(hours=RUN_INTERVAL_HOURS)

    resumed = resume_resolved_escalations()
    if resumed:
        print(f"resumed {resumed} invoice(s) on a human verdict")

    batch, total, discount = [], 0.0, 0.0
    for inv in due_invoices():
        plan = schedule_payment(
            float(inv["amount"] or 0),
            inv.get("payment_terms") or "2/10 net 30",
            inv.get("invoice_date"),
        )
        pay_by = datetime.fromisoformat(plan["scheduled_for"])
        # Pay now if the window closes before we'd run again.
        if plan["action"] == "pay_now" or pay_by <= horizon:
            batch.append((inv, plan))
            total += plan["amount_due"]
            discount += plan["discount_captured"]

    if not batch:
        print("payment run: nothing due this cycle")
        return

    run_id = create_payment_run([i["id"] for i, _ in batch], now.isoformat(), total, discount)

    for inv, plan in batch:
        paid = payments.pay_vendor(
            inv["id"], inv["vendor_name"], inv["invoice_number"], plan["amount_due"], run_id
        )
        linq.send_remittance(
            os.getenv("VENDOR_PHONE", ""),
            inv["vendor_name"],
            inv["invoice_number"],
            plan["amount_due"],
            paid["paid_at"],
            paid["reference"],
            plan["discount_captured"],
        )
        print(f"  paid {inv['vendor_name']} {inv['invoice_number']} ${plan['amount_due']:,.2f}")

    with get_conn() as conn:
        conn.execute(
            "UPDATE payment_runs SET status = 'executed', executed_at = ? WHERE id = ?",
            (now.isoformat(), run_id),
        )
        conn.commit()

    print(json.dumps({
        "run_id": run_id,
        "invoices_paid": len(batch),
        "total": round(total, 2),
        "discount_captured": round(discount, 2),
    }))


if __name__ == "__main__":
    main()
