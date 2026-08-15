from __future__ import annotations

import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from services import auth_service, job_service
from services.processing import job_ws_clients

router = APIRouter(tags=["websocket"])


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

        job_ws_clients.setdefault(job_id, set()).add(websocket)

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if job_id and job_id in job_ws_clients:
            job_ws_clients[job_id].discard(websocket)
            if not job_ws_clients[job_id]:
                del job_ws_clients[job_id]
