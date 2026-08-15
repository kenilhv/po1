from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from api.ap import router as ap_router
from api.auth import router as auth_router
from api.cfo import router as cfo_router
from api.ws import router as ws_router
from database.db import get_conn, init_db
from models.schemas import ApproveRequest, WebSocketTraceMessage
from services.processing import process_invoice_job
from services import job_service

load_dotenv(ROOT / ".env")

app = FastAPI(title="PayCrew API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "*",
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "ngrok-skip-browser-warning",
    ],
    expose_headers=["*"],
)

# PayCrew v1 API
app.include_router(auth_router, prefix="/v1")
app.include_router(ap_router, prefix="/v1")
app.include_router(cfo_router, prefix="/v1")
app.include_router(ws_router, prefix="/v1")

UPLOAD_DIR = ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Legacy InvoiceOS routes (unchanged)
ws_clients: dict[int, set[WebSocket]] = {}


def log_audit(
    invoice_id: int,
    agent_name: str,
    model_used: str | None,
    input_summary: str,
    output_summary: str,
    confidence: float | None = None,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO audit_log (invoice_id, agent_name, model_used, input_summary, output_summary, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (invoice_id, agent_name, model_used, input_summary, output_summary, confidence),
        )
        conn.commit()


async def broadcast(invoice_id: int, msg: WebSocketTraceMessage) -> None:
    payload = msg.model_dump()
    dead: list[WebSocket] = []
    for ws in ws_clients.get(invoice_id, set()):
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        ws_clients[invoice_id].discard(ws)


async def run_crew_legacy(invoice_id: int, pdf_path: str) -> None:
    from crew.orchestrator import run_invoice_pipeline

    async def on_agent(msg: dict[str, Any]) -> None:
        trace = WebSocketTraceMessage(invoice_id=invoice_id, **msg)
        log_audit(
            invoice_id,
            trace.agent,
            trace.model_used,
            trace.detail[:200],
            trace.result,
            trace.confidence,
        )
        await broadcast(invoice_id, trace)

    await run_invoice_pipeline(invoice_id, pdf_path, on_agent)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.post("/invoice/upload")
async def upload_invoice_legacy(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    path = UPLOAD_DIR / file.filename
    content = await file.read()
    path.write_bytes(content)
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO invoices (filename, status) VALUES (?, 'processing')",
            (file.filename,),
        )
        conn.commit()
        invoice_id = cur.lastrowid
    background_tasks.add_task(run_crew_legacy, invoice_id, str(path))
    return {"invoice_id": invoice_id, "status": "processing"}


@app.get("/invoice/list")
def list_invoices_legacy():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, filename, vendor_name, amount, status, risk_score, decision, created_at FROM invoices ORDER BY id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/invoice/{invoice_id}")
def get_invoice_legacy(invoice_id: int):
    with get_conn() as conn:
        inv = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        audit = conn.execute(
            "SELECT * FROM audit_log WHERE invoice_id = ? ORDER BY id",
            (invoice_id,),
        ).fetchall()
    if not inv:
        return {"error": "not found"}
    return {"invoice": dict(inv), "audit_log": [dict(a) for a in audit]}


@app.post("/invoice/{invoice_id}/approve")
def approve_invoice_legacy(invoice_id: int, body: ApproveRequest):
    decision = "APPROVED" if body.action == "approve" else "REJECTED"
    with get_conn() as conn:
        conn.execute(
            "UPDATE invoices SET status = ?, decision = ? WHERE id = ?",
            ("complete", decision, invoice_id),
        )
        conn.execute(
            """
            INSERT INTO audit_log (invoice_id, agent_name, model_used, input_summary, output_summary, confidence)
            VALUES (?, 'human_approver', NULL, ?, ?, 1.0)
            """,
            (invoice_id, body.approver, decision),
        )
        conn.commit()
    return {"invoice_id": invoice_id, "decision": decision}


@app.get("/audit/log")
def audit_log_legacy():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 200").fetchall()
    return [dict(r) for r in rows]


@app.websocket("/ws/trace/{invoice_id}")
async def ws_trace_legacy(websocket: WebSocket, invoice_id: int):
    await websocket.accept()
    ws_clients.setdefault(invoice_id, set()).add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_clients.get(invoice_id, set()).discard(websocket)
