from __future__ import annotations

import json
from typing import Any

from database.db import get_conn
from services.constants import AGENT_DISPLAY, agent_ws_status
from services.job_service import map_decision_to_status


def _parse_json_list(val: str | None) -> list[str] | None:
    if not val:
        return None
    try:
        data = json.loads(val)
        return data if isinstance(data, list) else [str(data)]
    except json.JSONDecodeError:
        return [val]


def _get_agents(invoice_id: int) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM agent_results WHERE invoice_id = ? ORDER BY id",
            (invoice_id,),
        ).fetchall()
    agents = []
    for r in rows:
        aid = r["agent"]
        agents.append(
            {
                "agent": AGENT_DISPLAY.get(aid, aid),
                "result": r["result"] or "",
                "confidence": r["confidence"],
                "model": r["model"] or "",
                "status": r["status"] or "pass",
                "detail": r["detail"] or "",
            }
        )
    return agents


def invoice_to_dict(row: Any, *, include_agents: bool = False) -> dict[str, Any]:
    if hasattr(row, "keys"):
        d = dict(row)
    else:
        d = row
    status = d.get("status") or "processing"
    if status == "complete" and d.get("decision"):
        status = map_decision_to_status(d["decision"])
    inv = {
        "id": d["id"],
        "number": d.get("invoice_number") or d.get("filename") or f"INV-{d['id']}",
        "vendor": d.get("vendor_name") or "",
        "amount": float(d["amount"]) if d.get("amount") is not None else 0.0,
        "risk": d.get("risk_score") or "",
        "status": status,
        "timestamp": d.get("created_at") or "",
        "agents": _get_agents(d["id"]) if include_agents else [],
        "riskReasons": _parse_json_list(d.get("risk_reasons")),
        "evidence": d.get("evidence"),
    }
    return inv


def list_invoices(*, risk: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM invoices ORDER BY created_at DESC"
    params: tuple = ()
    if risk:
        query = "SELECT * FROM invoices WHERE risk_score = ? ORDER BY created_at DESC"
        params = (risk.upper(),)
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [invoice_to_dict(r, include_agents=False) for r in rows]


def get_invoice(invoice_id: int, *, include_agents: bool = True) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    if not row:
        return None
    return invoice_to_dict(row, include_agents=include_agents)


def ap_stats() -> dict[str, int]:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
        auto = conn.execute(
            "SELECT COUNT(*) FROM invoices WHERE decision = 'AUTO_APPROVED' OR status = 'auto_approved'"
        ).fetchone()[0]
        flagged = conn.execute(
            "SELECT COUNT(*) FROM invoices WHERE risk_score IN ('HIGH','MEDIUM') OR decision IN ('PENDING_AP','PENDING_CFO')"
        ).fetchone()[0]
        blocked = conn.execute(
            "SELECT COUNT(*) FROM invoices WHERE risk_score = 'CRITICAL' OR decision = 'BLOCKED' OR status IN ('escalated','blocked')"
        ).fetchone()[0]
    return {"total": total, "autoApproved": auto, "flagged": flagged, "blocked": blocked}


def cfo_stats() -> dict[str, Any]:
    with get_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM invoices WHERE status NOT IN ('processing')"
        ).fetchone()[0]
        auto = conn.execute(
            "SELECT COUNT(*) FROM invoices WHERE decision = 'AUTO_APPROVED' OR status = 'auto_approved'"
        ).fetchone()[0]
        pending = conn.execute(
            "SELECT COUNT(*) FROM invoices WHERE status IN ('pending_cfo','escalated') OR decision IN ('PENDING_CFO','BLOCKED')"
        ).fetchone()[0]
        saved = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM invoices WHERE risk_score = 'CRITICAL' AND status IN ('escalated','rejected','blocked')"
        ).fetchone()[0]
    return {
        "totalProcessed": total,
        "autoApproved": auto,
        "pendingApproval": pending,
        "totalSaved": float(saved or 0),
    }


def decisions_grouped() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list] = {"LOW": [], "MEDIUM": [], "HIGH": [], "CRITICAL": []}
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, invoice_number, filename, vendor_name, amount, status, decision, risk_score FROM invoices"
        ).fetchall()
    for r in rows:
        risk = (r["risk_score"] or "LOW").upper()
        if risk not in out:
            continue
        status = map_decision_to_status(r["decision"]) if r["decision"] else r["status"]
        out[risk].append(
            {
                "id": r["id"],
                "number": r["invoice_number"] or r["filename"] or f"INV-{r['id']}",
                "vendor": r["vendor_name"] or "",
                "amount": float(r["amount"] or 0),
                "status": status,
            }
        )
    return out


def pending_cfo() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM invoices
            WHERE status IN ('pending_cfo','escalated')
               OR decision IN ('PENDING_CFO','BLOCKED')
            ORDER BY
              CASE risk_score WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
              created_at ASC
            """
        ).fetchall()
    return [invoice_to_dict(r, include_agents=True) for r in rows]


def save_agent_result(invoice_id: int, agent_id: str, msg: dict[str, Any]) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO agent_results (invoice_id, agent, result, confidence, model, status, detail)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice_id,
                agent_id,
                msg.get("result", ""),
                msg.get("confidence"),
                msg.get("model_used") or msg.get("model") or "",
                agent_ws_status(agent_id, str(msg.get("result", ""))),
                msg.get("detail", ""),
            ),
        )
        conn.commit()


def finalize_invoice(invoice_id: int, risk: str, decision: str, reasons: list[str], evidence: str) -> None:
    status = map_decision_to_status(decision)
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE invoices SET risk_score=?, decision=?, status=?, risk_reasons=?, evidence=?
            WHERE id=?
            """,
            (risk, decision, status, json.dumps(reasons), evidence, invoice_id),
        )
        conn.commit()


def approve_invoice_cfo(invoice_id: int) -> dict[str, Any] | None:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE invoices SET status='approved', decision='APPROVED', approved_by='CFO', approved_at=? WHERE id=?",
            (now, invoice_id),
        )
        conn.execute(
            """
            INSERT INTO audit_log (invoice_id, agent_name, output_summary, approved_by, confidence)
            VALUES (?, 'human_approver', 'approved', 'CFO', 1.0)
            """,
            (invoice_id,),
        )
        conn.commit()
    return get_invoice(invoice_id)


def reject_invoice_cfo(invoice_id: int, reason: str | None) -> dict[str, Any] | None:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE invoices SET status='rejected', decision='REJECTED',
            approved_by='CFO', approved_at=?, rejection_reason=? WHERE id=?
            """,
            (now, reason, invoice_id),
        )
        conn.execute(
            """
            INSERT INTO audit_log (invoice_id, agent_name, output_summary, input_summary, approved_by, confidence)
            VALUES (?, 'human_approver', 'rejected', ?, 'CFO', 1.0)
            """,
            (invoice_id, reason or ""),
        )
        conn.commit()
    return get_invoice(invoice_id)


def audit_log_page(page: int = 1, limit: int = 15) -> dict[str, Any]:
    offset = (page - 1) * limit
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
        rows = conn.execute(
            """
            SELECT a.*, i.invoice_number, i.filename
            FROM audit_log a
            LEFT JOIN invoices i ON i.id = a.invoice_id
            ORDER BY a.created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
    pages = max(1, (total + limit - 1) // limit)
    entries = []
    for r in rows:
        inv_label = r["invoice_number"] or r["filename"] or f"INV-{r['invoice_id']}"
        entries.append(
            {
                "id": r["id"],
                "timestamp": r["created_at"],
                "invoice": inv_label,
                "agent": r["agent_name"],
                "decision": r["output_summary"] or "",
                "model": r["model_used"] or "",
                "confidence": r["confidence"],
                "approvedBy": r["approved_by"] or "",
            }
        )
    return {"entries": entries, "total": total, "page": page, "pages": pages}


def audit_log_csv_rows() -> list[list[str]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT a.*, i.invoice_number, i.filename
            FROM audit_log a
            LEFT JOIN invoices i ON i.id = a.invoice_id
            ORDER BY a.created_at DESC
            """
        ).fetchall()
    out = [["Timestamp", "Invoice", "Agent", "Decision", "Model", "Confidence", "Approved By"]]
    for r in rows:
        inv_label = r["invoice_number"] or r["filename"] or f"INV-{r['invoice_id']}"
        out.append(
            [
                r["created_at"] or "",
                inv_label,
                r["agent_name"] or "",
                r["output_summary"] or "",
                r["model_used"] or "",
                str(r["confidence"] if r["confidence"] is not None else ""),
                r["approved_by"] or "",
            ]
        )
    return out
