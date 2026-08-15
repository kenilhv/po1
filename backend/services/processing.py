from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Awaitable

from crew.orchestrator import run_invoice_pipeline
from services.constants import AGENT_DISPLAY
from services.invoice_service import finalize_invoice, get_invoice, save_agent_result
from services.job_service import complete_job, fail_job

# job_id -> set of websocket connections
job_ws_clients: dict[str, set[Any]] = {}


async def broadcast_job(job_id: str, payload: dict[str, Any]) -> None:
    dead = []
    for ws in job_ws_clients.get(job_id, set()):
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        job_ws_clients.get(job_id, set()).discard(ws)


async def process_invoice_job(job_id: str, invoice_id: int, pdf_path: str) -> None:
    reasons: list[str] = []
    evidence_parts: list[str] = []
    final_risk = "LOW"
    final_decision = "AUTO_APPROVED"

    async def on_agent(msg: dict[str, Any]) -> None:
        nonlocal final_risk, final_decision
        agent_id = msg.get("agent", "")
        display = AGENT_DISPLAY.get(agent_id, agent_id)

        if msg.get("status") == "running":
            await broadcast_job(
                job_id,
                {"type": "agent_start", "jobId": job_id, "agent": display},
            )
            return

        save_agent_result(invoice_id, agent_id, msg)

        if msg.get("risk_contribution") == "high":
            reasons.append(f"{display}: {msg.get('detail', '')[:120]}")
        if agent_id == "risk_scorer":
            final_risk = str(msg.get("result", "LOW")).upper()
            evidence_parts.append(msg.get("detail", ""))
        if agent_id == "approval_router":
            final_decision = str(msg.get("decision") or msg.get("result", "")).upper()

        await broadcast_job(
            job_id,
            {
                "type": "agent_complete",
                "jobId": job_id,
                "agent": display,
                "result": msg.get("result", ""),
                "confidence": msg.get("confidence"),
                "model": msg.get("model_used") or "",
                "status": _agent_status(agent_id, str(msg.get("result", ""))),
                "detail": msg.get("detail", ""),
            },
        )

    try:
        await run_invoice_pipeline(invoice_id, pdf_path, on_agent)
        finalize_invoice(
            invoice_id,
            final_risk,
            final_decision,
            reasons,
            json.dumps(evidence_parts)[:2000],
        )
        complete_job(job_id, invoice_id)
        invoice = get_invoice(invoice_id, include_agents=True)
        if invoice:
            await broadcast_job(job_id, {"type": "job_complete", "jobId": job_id, "invoice": invoice})
    except Exception as exc:
        fail_job(job_id, str(exc))
        await broadcast_job(
            job_id,
            {"type": "job_failed", "jobId": job_id, "error": str(exc)},
        )


def _agent_status(agent_id: str, result: str) -> str:
    from services.constants import agent_ws_status

    return agent_ws_status(agent_id, result)
