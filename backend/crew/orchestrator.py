from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Awaitable, Callable

from crew.agents.pipeline import (
    agent_model,
    run_duplicate,
    run_fraud,
    run_parser,
    run_po_matcher,
    run_risk_scorer,
    run_router,
)
from crew.agents.rules import parse_invoice_rules, parse_router_decision, route_rules, score_risk_rules
from crew.tools.pdf_tool import extract_pdf_text
from crew.tools.po_tool import lookup_duplicate, lookup_po, lookup_vendor
from database.db import get_conn

OnAgent = Callable[[dict[str, Any]], Awaitable[None]]

USE_LLM = os.getenv("USE_LLM", "1") == "1"


def _llm_ready() -> bool:
    if not USE_LLM:
        return False
    key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    return bool(key) and key not in ("not-set", "your-groq-api-key")


async def emit(on_agent: OnAgent, **msg: Any) -> None:
    await on_agent(msg)


async def run_invoice_pipeline(
    invoice_id: int,
    pdf_path: str,
    on_agent: OnAgent,
) -> None:
    text = extract_pdf_text(pdf_path)

    # --- Agent 1: invoice_parser (CrewAI when LLM ready) ---
    await emit(
        on_agent,
        agent="invoice_parser",
        status="running",
        result="parsing",
        detail="Reading PDF",
        model_used=agent_model("invoice_parser"),
    )
    parsed = await asyncio.to_thread(_parse_invoice, text)
    await emit(
        on_agent,
        agent="invoice_parser",
        status="complete",
        result="parsed",
        detail=f"Extracted {parsed.get('vendor_name')} ${parsed.get('amount')}",
        confidence=0.9,
        model_used=agent_model("invoice_parser"),
    )

    vendor = str(parsed.get("vendor_name") or "")
    amount = float(parsed.get("amount") or 0)
    po_ref = parsed.get("po_reference")
    bank = str(parsed.get("bank_details") or "")
    inv_num = str(parsed.get("invoice_number") or "")

    # --- Agents 2, 3, 4 in parallel (CrewAI + tools when LLM ready) ---
    await emit(on_agent, agent="po_matcher", status="running", result="matching", detail="Checking PO", model_used=agent_model("po_matcher"))
    await emit(on_agent, agent="duplicate_detector", status="running", result="checking", detail="Checking duplicates", model_used=agent_model("duplicate_detector"))
    await emit(on_agent, agent="fraud_signal", status="running", result="checking", detail="Checking fraud signals", model_used=agent_model("fraud_signal"))

    po_raw, dup_raw, fraud_raw = await asyncio.gather(
        _run_po_agent(vendor, str(po_ref or "")),
        _run_dup_agent(vendor, amount, inv_num),
        _run_fraud_agent(vendor, bank),
    )

    po = lookup_po(vendor, po_ref)
    dup = lookup_duplicate(vendor, amount, inv_num)
    fraud = lookup_vendor(vendor, bank)

    await emit(
        on_agent,
        agent="po_matcher",
        status="complete",
        result="match_found" if po["match"] else "no_match",
        detail=po_raw or str(po),
        confidence=0.95 if po["match"] else 0.7,
        risk_contribution="low" if po["match"] else "high",
        model_used=agent_model("po_matcher"),
    )
    await emit(
        on_agent,
        agent="duplicate_detector",
        status="complete",
        result="duplicate_found" if dup.get("duplicate") else "clean",
        detail=dup_raw or dup.get("detail", str(dup)),
        confidence=0.92,
        risk_contribution="high" if dup.get("duplicate") else "low",
        model_used=agent_model("duplicate_detector"),
    )
    await emit(
        on_agent,
        agent="fraud_signal",
        status="complete",
        result="signals_found" if fraud.get("signals") else "clean",
        detail=fraud_raw or str(fraud.get("signals", [])),
        confidence=0.88,
        risk_contribution="high" if fraud.get("flagged") else "low",
        model_used=agent_model("fraud_signal"),
    )

    evidence = {"po": po, "duplicate": dup, "fraud": fraud, "amount": amount, "vendor": vendor}

    await emit(on_agent, agent="risk_scorer", status="running", result="scoring", detail="Computing risk", model_used=agent_model("risk_scorer"))
    risk, explanation = await asyncio.to_thread(_score_risk, evidence)
    await emit(
        on_agent,
        agent="risk_scorer",
        status="complete",
        result=risk,
        detail=explanation,
        confidence=0.9,
        risk_score=risk,
        model_used=agent_model("risk_scorer"),
    )

    # --- Agent 6: approval_router (CrewAI) ---
    await emit(on_agent, agent="approval_router", status="running", result="routing", detail="Routing decision", model_used=agent_model("approval_router"))
    decision, router_detail = await asyncio.to_thread(_route, risk, evidence)
    await emit(
        on_agent,
        agent="approval_router",
        status="complete",
        result=decision.lower(),
        detail=router_detail,
        confidence=0.97,
        risk_score=risk,
        decision=decision,
        model_used=agent_model("approval_router"),
    )

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE invoices SET vendor_name=?, amount=?, invoice_number=?, status='complete',
            risk_score=?, decision=?, po_reference=?, bank_details=?
            WHERE id=?
            """,
            (vendor, amount, inv_num, risk, decision, po_ref, bank, invoice_id),
        )
        conn.commit()


def _parse_invoice(text: str) -> dict[str, Any]:
    if _llm_ready():
        try:
            return run_parser(text)
        except Exception:
            pass
    return parse_invoice_rules(text)


async def _run_po_agent(vendor: str, po_ref: str) -> str:
    if _llm_ready():
        try:
            return await asyncio.to_thread(run_po_matcher, vendor, po_ref)
        except Exception:
            pass
    return json.dumps(lookup_po(vendor, po_ref or None))


async def _run_dup_agent(vendor: str, amount: float, inv_num: str) -> str:
    if _llm_ready():
        try:
            return await asyncio.to_thread(run_duplicate, vendor, amount, inv_num)
        except Exception:
            pass
    return json.dumps(lookup_duplicate(vendor, amount, inv_num))


async def _run_fraud_agent(vendor: str, bank: str) -> str:
    if _llm_ready():
        try:
            return await asyncio.to_thread(run_fraud, vendor, bank)
        except Exception:
            pass
    return json.dumps(lookup_vendor(vendor, bank or None))


def _score_risk(evidence: dict[str, Any]) -> tuple[str, str]:
    if _llm_ready():
        try:
            return run_risk_scorer(evidence)
        except Exception:
            pass
    return score_risk_rules(evidence)


def _route(risk: str, evidence: dict[str, Any]) -> tuple[str, str]:
    if _llm_ready():
        try:
            raw = run_router(risk, evidence)
            return parse_router_decision(raw, risk)
        except Exception:
            pass
    decision = route_rules(risk)
    return decision, f"Routed as {decision}. Human approval required for payment."
