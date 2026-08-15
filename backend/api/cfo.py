from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.deps import require_cfo
from services import invoice_service

router = APIRouter(prefix="/cfo", tags=["cfo"])


class RejectBody(BaseModel):
    reason: str | None = None


@router.get("/stats")
def cfo_stats(_auth=Depends(require_cfo)):
    return invoice_service.cfo_stats()


@router.get("/invoices")
def cfo_invoices(risk: str | None = None, _auth=Depends(require_cfo)):
    return invoice_service.list_invoices(risk=risk)


@router.get("/invoices/{invoice_id}")
def cfo_invoice_detail(invoice_id: int, _auth=Depends(require_cfo)):
    inv = invoice_service.get_invoice(invoice_id, include_agents=True)
    if not inv:
        raise HTTPException(status_code=404, detail="Not found")
    return inv


@router.get("/pending-approvals")
def cfo_pending(_auth=Depends(require_cfo)):
    return invoice_service.pending_cfo()


@router.post("/invoices/{invoice_id}/approve")
def cfo_approve(invoice_id: int, _auth=Depends(require_cfo)):
    inv = invoice_service.approve_invoice_cfo(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Not found")
    return inv


@router.post("/invoices/{invoice_id}/reject")
def cfo_reject(invoice_id: int, body: RejectBody, _auth=Depends(require_cfo)):
    inv = invoice_service.reject_invoice_cfo(invoice_id, body.reason)
    if not inv:
        raise HTTPException(status_code=404, detail="Not found")
    return inv


@router.get("/audit-log")
def cfo_audit_log(page: int = 1, limit: int = 15, _auth=Depends(require_cfo)):
    return invoice_service.audit_log_page(page=page, limit=limit)


@router.get("/audit-log/export")
def cfo_audit_export(_auth=Depends(require_cfo)):
    rows = invoice_service.audit_log_csv_rows()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="audit-log.csv"'},
    )
