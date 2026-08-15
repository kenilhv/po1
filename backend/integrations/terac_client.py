"""PO1 — Terac External API v2 client.

Two distinct uses, both required by the hackathon criteria:

  1. REALTIME ESCALATION — when the pipeline hits an exception it must not
     resolve alone (a vendor banking change, a large unmatched invoice), it
     sources ONE verified reviewer and blocks on their verdict.

  2. LABELING STUDY — a batch of sample invoice exceptions is sent to a
     general-population panel for labels, which then train the Pioneer
     fine-tune. This is the "real human input -> measurably better project"
     before/after the rules explicitly ask for.

Both surface as Terac "opportunities" whose task_url points at a page PO1
hosts, so participants are responding to a real app, not a form.

API: https://terac.com/api/external/v2   Auth: Authorization: Bearer <key>
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

import requests

from database.db import get_conn

BASE_URL = os.getenv("TERAC_BASE_URL", "https://terac.com/api/external/v2")
API_KEY = os.getenv("TERAC_API_KEY", "")
PUBLIC_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:5173")
TIMEOUT = 30


class TeracError(RuntimeError):
    pass


def _headers() -> dict[str, str]:
    if not API_KEY:
        raise TeracError("TERAC_API_KEY is not set")
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def _request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    resp = requests.request(method, url, headers=_headers(), json=payload, timeout=TIMEOUT)
    if resp.status_code >= 400:
        raise TeracError(f"{method} {path} -> {resp.status_code}: {resp.text[:400]}")
    return resp.json() if resp.content else {}


def is_configured() -> bool:
    return bool(API_KEY)


# ------------------------------------------------------------------ projects

def ensure_project(name: str = "PO1 — Autonomous AP") -> str:
    """Reuse the project across the day so opportunities stay grouped."""
    cached = os.getenv("TERAC_PROJECT_ID")
    if cached:
        return cached

    try:
        existing = _request("GET", "/projects").get("data") or []
        for p in existing:
            if p.get("name") == name:
                return str(p["id"])
    except TeracError:
        pass

    created = _request("POST", "/projects", {"name": name})
    project_id = str((created.get("data") or created).get("id"))
    os.environ["TERAC_PROJECT_ID"] = project_id
    return project_id


# ------------------------------------------------------- realtime escalation

def escalate_invoice(
    invoice_id: int,
    exception_type: str,
    question: str,
    context: dict[str, Any],
    num_reviewers: int = 1,
) -> dict[str, Any]:
    """Hire a verified human to rule on ONE invoice exception the agent won't.

    The reviewer lands on PO1's own review page for this invoice — they see the
    evidence the agents gathered and record an approve / reject / investigate
    verdict, which the pipeline then acts on.
    """
    project_id = ensure_project()
    review_url = f"{PUBLIC_URL}/review/{invoice_id}"

    body = {
        "title": f"AP exception review: {exception_type.replace('_', ' ')}",
        "internal_title": f"PO1 invoice #{invoice_id} — {exception_type}",
        "description": question,
        "project_id": project_id,
        "num_participants": num_reviewers,
        "business_type": "b2c",
        "unrestricted_audience": True,  # general population — fastest fill
        "expected_days_to_complete": 1,
        "tasks": [
            {
                "sequence": 1,
                "task_type": "activity",
                "review_type": "auto_approve",
                "task_url": review_url,
                "title": "Review this accounts-payable exception",
                "description": question,
                "duration_minutes": 5,
            }
        ],
    }

    created = _request("POST", "/opportunities", body)
    opportunity_id = str((created.get("data") or created).get("id"))
    _request("POST", f"/opportunities/{opportunity_id}/launch")

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO terac_escalations
                (invoice_id, kind, exception_type, question, payload, reviewer_ref)
            VALUES (?, 'realtime', ?, ?, ?, ?)
            """,
            (invoice_id, exception_type, question, json.dumps(context), opportunity_id),
        )
        conn.commit()

    return {
        "opportunity_id": opportunity_id,
        "review_url": review_url,
        "status": "launched",
    }


def check_escalation(opportunity_id: str) -> dict[str, Any]:
    """Poll for the reviewer's verdict."""
    data = _request("GET", f"/opportunities/{opportunity_id}/submissions").get("data") or []
    done = [s for s in data if s.get("status") in ("approved", "awaiting_review")]
    return {
        "resolved": bool(done),
        "submissions": data,
        "count": len(data),
    }


def record_verdict(
    opportunity_id: str,
    verdict: str,
    reasoning: str,
    cost: float = 15.0,
) -> None:
    """Write the human's decision back so the pipeline can act and audit it."""
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE terac_escalations
            SET verdict = ?, reasoning = ?, cost = ?, resolved_at = ?
            WHERE reviewer_ref = ?
            """,
            (verdict, reasoning, cost, datetime.utcnow().isoformat(), opportunity_id),
        )
        conn.commit()


# ----------------------------------------------------------- labeling study

def launch_labeling_study(num_participants: int = 25) -> dict[str, Any]:
    """Send a batch of real invoice exceptions to the general population for labels.

    Those labels become the training set for the Pioneer fine-tune, which is
    what produces the measurable before/after the rules require.
    """
    project_id = ensure_project()
    label_url = f"{PUBLIC_URL}/label"

    body = {
        "title": "Which of these vendor invoices look risky?",
        "internal_title": "PO1 fraud-signal training labels",
        "description": (
            "Review a short series of real vendor invoices and mark which ones "
            "look risky to pay, and why. No accounting background needed — we "
            "want ordinary judgment about what looks off."
        ),
        "project_id": project_id,
        "num_participants": num_participants,
        "business_type": "b2c",
        "unrestricted_audience": True,
        "expected_days_to_complete": 1,
        "tasks": [
            {
                "sequence": 1,
                "task_type": "activity",
                "review_type": "auto_approve",
                "task_url": label_url,
                "title": "Label invoices as risky or safe",
                "description": "About 5 minutes. Mark each invoice risky or safe and say why in a few words.",
                "duration_minutes": 5,
            }
        ],
    }

    created = _request("POST", "/opportunities", body)
    opportunity_id = str((created.get("data") or created).get("id"))
    _request("POST", f"/opportunities/{opportunity_id}/launch")

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO terac_escalations (kind, question, payload, reviewer_ref)
            VALUES ('study', ?, ?, ?)
            """,
            ("fraud-signal labeling study", json.dumps({"n": num_participants}), opportunity_id),
        )
        conn.commit()

    return {"opportunity_id": opportunity_id, "label_url": label_url, "status": "launched"}


def collect_labels(opportunity_id: str) -> list[dict[str, Any]]:
    """Pull completed submissions to build the fine-tuning dataset."""
    data = _request("GET", f"/opportunities/{opportunity_id}/submissions").get("data") or []
    return [s for s in data if s.get("status") in ("approved", "awaiting_review")]


def escalation_stats() -> dict[str, Any]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT kind, COUNT(*) AS n,
                   SUM(CASE WHEN resolved_at IS NOT NULL THEN 1 ELSE 0 END) AS resolved,
                   COALESCE(SUM(cost), 0) AS spend
            FROM terac_escalations GROUP BY kind
            """
        ).fetchall()
    return {r["kind"]: {"total": r["n"], "resolved": r["resolved"], "spend": float(r["spend"])} for r in rows}
