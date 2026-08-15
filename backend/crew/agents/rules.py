"""Deterministic rule-based agent logic (used when LLM unavailable or as fallback)."""

from __future__ import annotations

import re
from typing import Any

VALID_RISKS = frozenset({"LOW", "MEDIUM", "HIGH", "CRITICAL"})
VALID_DECISIONS = frozenset({"AUTO_APPROVED", "PENDING_AP", "PENDING_CFO", "BLOCKED"})

_DEMO_PARSERS: list[tuple[str, dict[str, Any]]] = [
    (
        "OfficeSupplyCo",
        {
            "vendor_name": "OfficeSupplyCo",
            "amount": 800.0,
            "invoice_number": "INV-2024-441",
            "po_reference": "PO-8821",
            "bank_details": "ACC-001-VALID",
        },
    ),
    (
        "TechSoftware",
        {
            "vendor_name": "TechSoftware Inc",
            "amount": 1200.0,
            "invoice_number": "INV-9921",
            "po_reference": "PO-7743",
            "bank_details": "ACC-002-VALID",
        },
    ),
    (
        "FastConsult",
        {
            "vendor_name": "FastConsult LLC",
            "amount": 45000.0,
            "invoice_number": "INV-F-0042",
            "po_reference": None,
            "bank_details": "ACC-999-SUSPICIOUS",
        },
    ),
    (
        "CleanVendor",
        {
            "vendor_name": "CleanVendor Inc",
            "amount": 500.0,
            "invoice_number": "INV-2024-300",
            "po_reference": "PO-9901",
            "bank_details": "ACC-003-VALID",
        },
    ),
    (
        "PaperWorks",
        {
            "vendor_name": "PaperWorks Ltd",
            "amount": 350.0,
            "invoice_number": "INV-2024-400",
            "po_reference": "PO-4412",
            "bank_details": "ACC-004-VALID",
        },
    ),
]


def _extract(pattern: str, text: str, default: str | None = None) -> str | None:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else default


def _extract_amount(text: str) -> float:
    normalized = text.replace(",", "")
    m = re.search(r"(?:Amount|Total)\s*:\s*\$?\s*([\d]+(?:\.\d+)?)", normalized, re.IGNORECASE)
    if m:
        return float(m.group(1))
    m = re.search(r"\$\s*([\d]+(?:\.\d+)?)", normalized)
    return float(m.group(1)) if m else 0.0


def parse_invoice_rules(text: str) -> dict[str, Any]:
    if not text or not text.strip():
        return {}

    for keyword, fields in _DEMO_PARSERS:
        if keyword in text:
            return dict(fields)

    vendor = _extract(r"Vendor\s*:\s*(.+)", text)
    inv_num = _extract(r"Invoice\s*(?:Number|#)\s*:\s*(\S+)", text)
    po_ref = _extract(r"PO\s*(?:Reference|#)?\s*:\s*(\S+)", text)
    bank = _extract(r"Bank\s*(?:Account|Details)?\s*:\s*(\S+)", text)
    amount = _extract_amount(text)

    if not vendor and not inv_num and amount == 0.0:
        return {}

    return {
        "vendor_name": vendor or "",
        "amount": amount,
        "invoice_number": inv_num or "",
        "po_reference": po_ref,
        "bank_details": bank or "",
    }


def score_risk_rules(evidence: dict[str, Any]) -> tuple[str, str]:
    po = evidence.get("po") or {}
    dup = evidence.get("duplicate") or {}
    fraud = evidence.get("fraud") or {}
    amount = float(evidence.get("amount") or 0)

    if fraud.get("flagged"):
        signals = fraud.get("signals") or []
        detail = "; ".join(signals) if signals else "Vendor flagged in registry"
        return "CRITICAL", detail

    if dup.get("duplicate"):
        return "HIGH", dup.get("detail", "Duplicate payment detected")

    if not po.get("match") and amount > 10_000:
        return "CRITICAL", "Large amount without purchase order match"

    if not po.get("match"):
        return "MEDIUM", "No purchase order match"

    if fraud.get("signals"):
        return "MEDIUM", "; ".join(fraud["signals"])

    return "LOW", "All checks passed"


def route_rules(risk: str) -> str:
    normalized = (risk or "MEDIUM").upper()
    if normalized not in VALID_RISKS:
        normalized = "MEDIUM"
    return {
        "LOW": "AUTO_APPROVED",
        "MEDIUM": "PENDING_AP",
        "HIGH": "PENDING_CFO",
        "CRITICAL": "BLOCKED",
    }[normalized]


def parse_router_decision(raw: str, risk: str) -> tuple[str, str]:
    """Parse approval_router LLM output; fall back to rules on invalid data."""
    data: dict[str, Any] = {}
    if "{" in raw:
        try:
            data = __import__("json").loads(raw[raw.find("{") : raw.rfind("}") + 1])
        except Exception:
            data = {}

    decision = str(data.get("decision", route_rules(risk))).upper()
    if decision not in VALID_DECISIONS:
        decision = route_rules(risk)
    detail = str(data.get("detail") or f"Routed as {decision}")
    return decision, detail
