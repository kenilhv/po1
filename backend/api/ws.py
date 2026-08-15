from __future__ import annotations

import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from services import auth_service, invoice_service, job_service
from services.processing import job_ws_clients

router = APIRouter(tags=["websocket"])


async def _replay_saved_agents(websocket: WebSocket, job_id: str, invoice_id: int) -> int:
    """Replay agents already persisted so mid-flight subscribers catch up."""
    invoice = invoice_service.get_invoice(invoice_id, include_agents=True)
    if not invoice:
        return 0

    for agent in invoice.get("agents", []):
        await websocket.send_json(
            {"type": "agent_start", "jobId": job_id, "agent": agent["agent"]}
        )
        await websocket.send_json(
            {
                "type": "agent_complete",
                "jobId": job_id,
                "agent": agent["agent"],
                "result": agent.get("result", ""),
                "confidence": agent.get("confidence"),
                "model": agent.get("model", ""),
                "status": agent.get("status", "pass"),
                "detail": agent.get("detail", ""),
            }
        )
    return len(invoice.get("agents", []))


async def _replay_finished_job(websocket: WebSocket, job: dict) -> None:
    """If a client subscribes after the job already finished, replay the stored
    agent results so late/reconnecting clients still get the full trace."""
    job_id = job["job_id"]

    if job["status"] == "failed":
        await websocket.send_json(
            {"type": "job_failed", "jobId": job_id, "error": job.get("error") or "Processing failed"}
        )
        return

    invoice = invoice_service.get_invoice(job["invoice_id"], include_agents=True)
    if not invoice:
        return

    await _replay_saved_agents(websocket, job_id, job["invoice_id"])
    await websocket.send_json({"type": "job_complete", "jobId": job_id, "invoice": invoice})


@router.websocket("/ws")
async def paycrew_ws(websocket: WebSocket, token: str = Query(...)):
    role = auth_service.get_role(token)
    if not role:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    job_id: str | None = None

    try:
        raw = await websocket.receive_text()
        data = json.loads(raw)
        job_id = data.get("jobId")
        if not job_id:
            await websocket.close(code=4001)
            return

        job = job_service.get_job(job_id)
        if not job:
            await websocket.close(code=4001)
            return

        # Register for live events first so nothing is missed mid-flight.
        job_ws_clients.setdefault(job_id, set()).add(websocket)

        if job["status"] in ("complete", "failed"):
            await _replay_finished_job(websocket, job)
        elif job["status"] == "processing":
            # Catch up on agents that finished before this socket subscribed.
            await _replay_saved_agents(websocket, job_id, job["invoice_id"])
            # Job may have finished while we replayed — send final event if so.
            job = job_service.get_job(job_id) or job
            if job["status"] == "complete":
                invoice = invoice_service.get_invoice(job["invoice_id"], include_agents=True)
                if invoice:
                    await websocket.send_json(
                        {"type": "job_complete", "jobId": job_id, "invoice": invoice}
                    )
            elif job["status"] == "failed":
                await websocket.send_json(
                    {
                        "type": "job_failed",
                        "jobId": job_id,
                        "error": job.get("error") or "Processing failed",
                    }
                )

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if job_id and job_id in job_ws_clients:
            job_ws_clients[job_id].discard(websocket)
            if not job_ws_clients[job_id]:
                del job_ws_clients[job_id]
