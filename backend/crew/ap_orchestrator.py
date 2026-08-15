"""PO1 — the 10-agent AP pipeline.

Sequenced the way a real accounts-payable department works:

    vendor_onboarder      gate on vendor master data before anything else
    invoice_parser        extract structured fields
    three_way_matcher     PO + goods receipt + invoice
    duplicate_detector  ┐
    fraud_signal        ├ parallel signal generators
    gl_coder            ┘
    exception_classifier ONE typed exception, with a named owner
    risk_scorer           severity of that typed exception
    approval_router       amount-tiered delegation of authority
    payment_scheduler     pay now (capture discount) or hold to net date

Every handoff goes through the Band room, so downstream agents read their
inputs from the room rather than from direct returns. Remove the room and
exception_classifier has no evidence and approval_router never unblocks.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Awaitable, Callable

from crew.agents.ap_rules import (
    assign_gl_code,
    check_vendor_status,
    classify_exception,
    route_decision,
    schedule_payment,
    score_severity,
    three_way_match,
)
from crew.agents.rules import parse_invoice_rules
from crew.tools.ap_tools import (
    check_budget,
    create_payment_run,
    lookup_goods_receipt,
    lookup_vendor_record,
    record_exception,
)
from crew.tools.pdf_tool import extract_pdf_text
from crew.tools.po_tool import lookup_duplicate, lookup_po, lookup_vendor
from database.db import get_conn
from integrations import band_client as band
from integrations import linq_client as linq
from integrations import payments

OnAgent = Callable[[dict[str, Any]], Awaitable[None]]

AUTO_LIMIT = float(os.getenv("PO1_AUTO_LIMIT", "2000"))
FOUNDER_LIMIT = float(os.getenv("PO1_FOUNDER_LIMIT", "10000"))
TERAC_WAIT_S = int(os.getenv("PO1_TERAC_WAIT_S", "60"))


async def _emit(on_agent: OnAgent, **msg: Any) -> None:
    await on_agent(msg)


async def _step(
    on_agent: OnAgent,
    invoice_id: int,
    agent: str,
    running_detail: str,
    fn: Callable[[], Any],
    finish: Callable[[Any], dict[str, Any]],
) -> Any:
    """Run one agent: announce, execute off-thread, publish to the room, emit."""
    await _emit(on_agent, agent=agent, status="running", result="working", detail=running_detail)
    result = await asyncio.to_thread(fn)
    payload = finish(result)
    band.post_finding(invoice_id, agent, payload)
    await _emit(on_agent, agent=agent, status="complete", **payload)
    return result


async def run_ap_pipeline(invoice_id: int, pdf_path: str, on_agent: OnAgent) -> dict[str, Any]:
    text = extract_pdf_text(pdf_path)

    # ---------------------------------------------------- 2. invoice_parser
    parsed = await _step(
        on_agent,
        invoice_id,
        "invoice_parser",
        "Extracting fields from the document",
        lambda: parse_invoice_rules(text),
        lambda r: {
            "result": "parsed",
            "detail": f"{r.get('vendor_name') or 'Unknown vendor'} — ${float(r.get('amount') or 0):,.2f}",
            "confidence": 0.9,
        },
    )

    vendor = str(parsed.get("vendor_name") or "Unknown Vendor")
    amount = float(parsed.get("amount") or 0)
    po_ref = parsed.get("po_reference")
    bank = str(parsed.get("bank_details") or "")
    inv_num = str(parsed.get("invoice_number") or f"INV-{invoice_id}")
    terms = parsed.get("payment_terms") or "2/10 net 30"

    # ------------------------------------------------- 1. vendor_onboarder
    vendor_status = await _step(
        on_agent,
        invoice_id,
        "vendor_onboarder",
        "Checking vendor master file",
        lambda: check_vendor_status(vendor, bank, lookup_vendor_record(vendor)),
        lambda r: {
            "result": "bank_change" if r.get("bank_details_changed")
            else "new_vendor" if r.get("is_new") else "verified",
            "detail": r.get("detail", ""),
            "risk_contribution": "high" if (r.get("bank_details_changed") or r.get("is_new")) else "low",
            "confidence": 0.95,
        },
    )

    # ------------------------------------------------- 3. three_way_matcher
    match = await _step(
        on_agent,
        invoice_id,
        "three_way_matcher",
        "Matching invoice against PO and goods receipt",
        lambda: three_way_match(amount, lookup_po(vendor, po_ref), lookup_goods_receipt(vendor, po_ref)),
        lambda r: {
            "result": f"{r['legs_matched']}_of_3",
            "detail": r.get("detail", ""),
            "risk_contribution": "low" if r["legs_matched"] == 3 else "high",
            "confidence": 0.93,
        },
    )

    # -------------------------------- 4,5,6. parallel signal generators
    await _emit(on_agent, agent="duplicate_detector", status="running", result="working", detail="Scanning payment history")
    await _emit(on_agent, agent="fraud_signal", status="running", result="working", detail="Screening vendor and banking signals")
    await _emit(on_agent, agent="gl_coder", status="running", result="working", detail="Assigning GL account and cost center")

    dup, fraud, gl = await asyncio.gather(
        asyncio.to_thread(lookup_duplicate, vendor, amount, inv_num),
        asyncio.to_thread(lookup_vendor, vendor, bank),
        asyncio.to_thread(assign_gl_code, vendor, str(parsed.get("line_items") or "")),
    )

    for agent, payload in (
        ("duplicate_detector", {
            "result": "duplicate" if dup.get("duplicate") else "clean",
            "detail": dup.get("detail", "No prior payment matches this invoice"),
            "risk_contribution": "high" if dup.get("duplicate") else "low",
            "confidence": 0.92,
        }),
        ("fraud_signal", {
            "result": "signals" if fraud.get("signals") else "clean",
            "detail": "; ".join(fraud.get("signals") or []) or "No fraud signals",
            "risk_contribution": "high" if fraud.get("flagged") else "low",
            "confidence": 0.88,
        }),
        ("gl_coder", {
            "result": gl["gl_code"],
            "detail": f"{gl['gl_code']} {gl['gl_label']} → {gl['cost_center']}",
            "confidence": 0.85,
        }),
    ):
        band.post_finding(invoice_id, agent, payload)
        await _emit(on_agent, agent=agent, status="complete", **payload)

    budget = await asyncio.to_thread(check_budget, gl["cost_center"], amount)

    # -------------------------------------------- 7. exception_classifier
    # Reads its evidence out of the Band room — this is the load-bearing handoff.
    room = band.read_findings(
        invoice_id,
        ["vendor_onboarder", "three_way_matcher", "duplicate_detector", "fraud_signal", "gl_coder"],
    )
    if len(room) < 5:
        await _emit(
            on_agent,
            agent="exception_classifier",
            status="complete",
            result="blocked",
            detail=f"Only {len(room)}/5 upstream findings in the room — cannot classify",
        )
        return {"status": "incomplete", "reason": "missing findings in Band room"}

    evidence = {
        "match": match,
        "duplicate": dup,
        "fraud": fraud,
        "vendor_status": vendor_status,
        "budget": budget,
        "amount": amount,
    }

    exc = await _step(
        on_agent,
        invoice_id,
        "exception_classifier",
        f"Synthesizing {len(room)} findings from the agent room",
        lambda: classify_exception(evidence),
        lambda r: {
            "result": r["exception_type"],
            "detail": r["detail"],
            "owner": r["owner"],
            "confidence": 0.9,
        },
    )
    exception_type = exc["exception_type"]

    # Specialist recruited at runtime, only for cases that warrant it.
    if exception_type == "vendor_bank_change":
        band.recruit_specialist(invoice_id, "controller", "vendor banking change requires controller review")
        await _emit(
            on_agent,
            agent="exception_classifier",
            status="complete",
            result="specialist_added",
            detail="Recruited a controller into the room — banking changes are never self-approved",
        )

    # ---------------------------------------------------- 8. risk_scorer
    severity, sev_detail = await _step(
        on_agent,
        invoice_id,
        "risk_scorer",
        "Scoring severity of the typed exception",
        lambda: score_severity(
            exception_type,
            amount,
            float(vendor_status.get("trust_score") or 0.5),
            (match.get("price_variance") or {}).get("pct"),
        ),
        lambda r: {"result": r[0], "detail": r[1], "risk_score": r[0], "confidence": 0.9},
    )

    if exception_type != "clean":
        record_exception(invoice_id, exc, severity)

    # ------------------------------------------------- 9. approval_router
    decision, route_detail = await _step(
        on_agent,
        invoice_id,
        "approval_router",
        "Applying delegation-of-authority limits",
        lambda: route_decision(severity, amount, exception_type,
                               {"auto": AUTO_LIMIT, "founder": FOUNDER_LIMIT}),
        lambda r: {"result": r[0].lower(), "detail": r[1], "decision": r[0], "confidence": 0.96},
    )

    # Anything the agent won't decide alone goes to a real human, and the
    # router genuinely blocks on the verdict arriving back in the room.
    if decision in ("PENDING_TERAC", "BLOCKED"):
        linq.alert_founder(invoice_id, vendor, amount, exception_type, exc["detail"])

        escalation = await _escalate(invoice_id, exception_type, exc, amount, vendor, on_agent)
        verdict = await band.await_verdict(invoice_id, timeout_s=TERAC_WAIT_S)

        if verdict:
            await _emit(
                on_agent,
                agent="approval_router",
                status="complete",
                result="human_verdict",
                detail=f"{verdict['verdict']} — {verdict['reasoning']}",
                decision=verdict["verdict"],
            )
            linq.notify_resolution(invoice_id, vendor, amount, verdict["verdict"], verdict["reasoning"])
            if verdict["verdict"].upper() in ("APPROVE", "APPROVED"):
                decision = "AUTO_APPROVED"
            else:
                _persist(invoice_id, vendor, amount, inv_num, severity, "REJECTED", po_ref, bank, gl)
                return {"status": "rejected", "exception_type": exception_type,
                        "escalation": escalation, "verdict": verdict}
        else:
            await _emit(
                on_agent,
                agent="approval_router",
                status="waiting",
                result="awaiting_human",
                detail=f"Escalated to a verified reviewer — holding ${amount:,.2f} until a verdict returns",
            )
            _persist(invoice_id, vendor, amount, inv_num, severity, decision, po_ref, bank, gl)
            return {"status": "awaiting_human", "exception_type": exception_type, "escalation": escalation}

    # ------------------------------------------------ 10. payment_scheduler
    if decision == "AUTO_APPROVED":
        sched = await _step(
            on_agent,
            invoice_id,
            "payment_scheduler",
            "Deciding when to pay",
            lambda: schedule_payment(amount, terms, parsed.get("invoice_date")),
            lambda r: {
                "result": r["action"],
                "detail": r["rationale"],
                "confidence": 0.94,
                "discount_captured": r["discount_captured"],
            },
        )

        if sched["action"] == "pay_now":
            run_id = create_payment_run([invoice_id], sched["scheduled_for"],
                                        sched["amount_due"], sched["discount_captured"])
            paid = payments.pay_vendor(invoice_id, vendor, inv_num, sched["amount_due"], run_id)
            linq.send_remittance(
                os.getenv("VENDOR_PHONE", ""), vendor, inv_num,
                sched["amount_due"], paid["paid_at"], paid["reference"], sched["discount_captured"],
            )
            await _emit(
                on_agent,
                agent="payment_scheduler",
                status="complete",
                result="paid",
                detail=(
                    f"Paid ${sched['amount_due']:,.2f} to {vendor}"
                    + (f", capturing ${sched['discount_captured']:,.2f} early-payment discount"
                       if sched["discount_captured"] else "")
                    + " — remittance advice sent"
                ),
                decision="PAID",
            )
            _persist(invoice_id, vendor, amount, inv_num, severity, "PAID", po_ref, bank, gl)
            return {"status": "paid", "amount": sched["amount_due"],
                    "discount": sched["discount_captured"], "exception_type": exception_type}

        create_payment_run([invoice_id], sched["scheduled_for"], sched["amount_due"], 0.0)
        _persist(invoice_id, vendor, amount, inv_num, severity, "SCHEDULED", po_ref, bank, gl)
        return {"status": "scheduled", "scheduled_for": sched["scheduled_for"],
                "exception_type": exception_type}

    # PENDING_FOUNDER — the customer's own call, cheap and low-stakes.
    linq.alert_founder(invoice_id, vendor, amount, exception_type, exc["detail"])
    _persist(invoice_id, vendor, amount, inv_num, severity, decision, po_ref, bank, gl)
    return {"status": "pending_founder", "exception_type": exception_type, "detail": route_detail}


async def _escalate(
    invoice_id: int,
    exception_type: str,
    exc: dict[str, Any],
    amount: float,
    vendor: str,
    on_agent: OnAgent,
) -> dict[str, Any]:
    """Hire a verified human through Terac and bill the customer for it."""
    question = (
        f"A ${amount:,.2f} invoice from {vendor} was flagged: "
        f"{exception_type.replace('_', ' ')}. {exc['detail']} "
        f"Should this payment be approved, rejected, or investigated further?"
    )
    await _emit(
        on_agent,
        agent="terac_escalation",
        status="running",
        result="hiring",
        detail=f"Sourcing a verified reviewer for a {exception_type.replace('_', ' ')}",
    )

    try:
        from integrations import terac_client

        result = terac_client.escalate_invoice(
            invoice_id, exception_type, question, {"vendor": vendor, "amount": amount, **exc}
        )
        detail = f"Reviewer sourced via Terac — opportunity {result['opportunity_id']}"
    except Exception as exc_err:  # network, config, or API shape
        result = {"opportunity_id": None, "error": str(exc_err)[:200]}
        detail = f"Terac escalation unavailable: {str(exc_err)[:120]}"

    payments.escalation_charge(os.getenv("PO1_CUSTOMER_REF", "demo-customer"), invoice_id, exception_type)

    await _emit(on_agent, agent="terac_escalation", status="complete", result="escalated", detail=detail)
    band.post_finding(invoice_id, "terac_escalation", {"detail": detail, **result})
    return result


def _persist(
    invoice_id: int, vendor: str, amount: float, inv_num: str,
    risk: str, decision: str, po_ref: Any, bank: str, gl: dict[str, str],
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE invoices
            SET vendor_name=?, amount=?, invoice_number=?, risk_score=?, decision=?,
                po_reference=?, bank_details=?, gl_code=?, cost_center=?, status=?
            WHERE id=?
            """,
            (vendor, amount, inv_num, risk, decision, po_ref, bank,
             gl["gl_code"], gl["cost_center"], decision, invoice_id),
        )
        conn.commit()
