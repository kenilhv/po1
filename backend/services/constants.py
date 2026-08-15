from __future__ import annotations

AGENT_ORDER = [
    "invoice_parser",
    "po_matcher",
    "duplicate_detector",
    "fraud_signal",
    "risk_scorer",
    "approval_router",
]

AGENT_DISPLAY: dict[str, str] = {
    "invoice_parser": "Invoice Parser",
    "po_matcher": "PO Matcher",
    "duplicate_detector": "Duplicate Detector",
    "fraud_signal": "Fraud Signal",
    "risk_scorer": "Risk Scorer",
    "approval_router": "Approval Router",
}

DISPLAY_TO_ID = {v: k for k, v in AGENT_DISPLAY.items()}

DECISION_TO_STATUS = {
    "AUTO_APPROVED": "auto_approved",
    "PENDING_AP": "pending_ap",
    "PENDING_CFO": "pending_cfo",
    "BLOCKED": "escalated",
    "APPROVED": "approved",
    "REJECTED": "rejected",
}


def agent_ws_status(agent_id: str, result: str) -> str:
    if agent_id == "approval_router":
        return "route"
    if agent_id == "risk_scorer":
        return "route"
    if agent_id == "duplicate_detector" and "duplicate" in result.lower():
        return "fail"
    if agent_id == "po_matcher" and result == "no_match":
        return "fail"
    if agent_id == "fraud_signal" and "signal" in result.lower():
        return "warn"
    if agent_id == "invoice_parser" and result == "parsed":
        return "pass"
    if "clean" in result.lower() or "match_found" in result.lower():
        return "pass"
    if result.upper() in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        return "route"
    return "pass"
