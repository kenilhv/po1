from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
Decision = Literal["AUTO_APPROVED", "PENDING_AP", "PENDING_CFO", "BLOCKED", "APPROVED", "REJECTED"]


class InvoiceSummary(BaseModel):
    id: int
    filename: str
    vendor_name: str | None
    amount: float | None
    status: str
    risk_score: RiskLevel | None
    decision: Decision | None
    created_at: str


class AuditEntry(BaseModel):
    id: int
    invoice_id: int | None
    agent_name: str
    model_used: str | None
    input_summary: str | None
    output_summary: str | None
    confidence: float | None
    created_at: str


class WebSocketTraceMessage(BaseModel):
    invoice_id: int
    agent: str
    status: Literal["running", "complete", "error"] = "complete"
    result: str
    detail: str
    confidence: float | None = None
    risk_contribution: str | None = None
    model_used: str | None = None
    risk_score: RiskLevel | None = None
    decision: Decision | None = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class ApproveRequest(BaseModel):
    action: Literal["approve", "reject"]
    approver: str = "CFO"
