from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from api.deps import require_ap
from services import invoice_service, job_service, processing

router = APIRouter(prefix="/ap", tags=["ap"])

UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@router.get("/stats")
def ap_stats(_auth=Depends(require_ap)):
    return invoice_service.ap_stats()


@router.get("/invoices")
def ap_invoices(risk: str | None = None, _auth=Depends(require_ap)):
    return invoice_service.list_invoices(risk=risk)


@router.get("/invoices/{invoice_id}")
def ap_invoice_detail(invoice_id: int, _auth=Depends(require_ap)):
    inv = invoice_service.get_invoice(invoice_id, include_agents=True)
    if not inv:
        raise HTTPException(status_code=404, detail="Not found")
    return inv


@router.get("/decisions")
def ap_decisions(_auth=Depends(require_ap)):
    return invoice_service.decisions_grouped()


@router.post("/invoices/upload")
async def ap_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    _auth=Depends(require_ap),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return JSONResponse(status_code=400, content={"error": "Please upload a PDF file"})

    content = await file.read()
    path = UPLOAD_DIR / file.filename
    path.write_bytes(content)

    from database.db import get_conn

    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO invoices (filename, status) VALUES (?, 'processing')",
            (file.filename,),
        )
        conn.commit()
        invoice_id = cur.lastrowid

    job_id = job_service.create_job(invoice_id)
    background_tasks.add_task(processing.process_invoice_job, job_id, invoice_id, str(path))

    return {"jobId": job_id, "invoiceId": invoice_id, "status": "processing"}


@router.get("/invoices/jobs/{job_id}")
def ap_job_status(job_id: str, _auth=Depends(require_ap)):
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_service.job_response(job)
