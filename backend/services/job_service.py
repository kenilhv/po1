from __future__ import annotations

import json
import uuid
from typing import Any

from database.db import get_conn
from services.constants import DECISION_TO_STATUS


def create_job(invoice_id: int) -> str:
    job_id = str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO jobs (job_id, invoice_id, status) VALUES (?, ?, 'processing')",
            (job_id, invoice_id),
        )
        conn.commit()
    return job_id


def get_job(job_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


def complete_job(job_id: str, invoice_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET status = 'complete', invoice_id = ? WHERE job_id = ?",
            (invoice_id, job_id),
        )
        conn.commit()


def fail_job(job_id: str, error: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET status = 'failed', error = ? WHERE job_id = ?",
            (error, job_id),
        )
        conn.commit()


def job_response(job: dict[str, Any]) -> dict[str, Any]:
    if job["status"] == "processing":
        return {"jobId": job["job_id"], "status": "processing"}
    if job["status"] == "failed":
        return {"jobId": job["job_id"], "status": "failed", "error": job.get("error") or "Unknown error"}
    from services.invoice_service import get_invoice

    invoice = get_invoice(job["invoice_id"], include_agents=True) if job.get("invoice_id") else None
    return {
        "jobId": job["job_id"],
        "status": "complete",
        "invoiceId": job["invoice_id"],
        "invoice": invoice,
    }


def map_decision_to_status(decision: str | None) -> str:
    if not decision:
        return "processing"
    return DECISION_TO_STATUS.get(decision.upper(), decision.lower())
