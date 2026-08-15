from __future__ import annotations

import json
from typing import Any

from crewai import Crew, Process, Task

from crew.agents.factory import build_agent
from crew.config import model_name
from crew.tools.crew_tools import check_duplicate_payment, check_vendor_fraud_signals, lookup_purchase_order


def run_parser(text: str) -> dict[str, Any]:
    agent = build_agent("invoice_parser")
    task = Task(
        description=(
            "Parse invoice text. Return ONLY JSON with keys: vendor_name, invoice_number, "
            f"amount (number), po_reference, bank_details, line_items.\n\n{text[:4000]}"
        ),
        expected_output="Valid JSON object",
        agent=agent,
    )
    raw = str(Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False).kickoff())
    return _json(raw)


def run_po_matcher(vendor: str, po_ref: str) -> str:
    agent = build_agent("po_matcher")
    agent.tools = [lookup_purchase_order]
    task = Task(
        description=f"Match vendor '{vendor}' PO '{po_ref}'. Use lookup_purchase_order tool. Return JSON summary.",
        expected_output="JSON with match true/false",
        agent=agent,
    )
    return str(Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False).kickoff())


def run_duplicate(vendor: str, amount: float, invoice_number: str) -> str:
    agent = build_agent("duplicate_detector")
    agent.tools = [check_duplicate_payment]
    task = Task(
        description=(
            f"Check duplicates for vendor={vendor} amount={amount} invoice={invoice_number}. "
            "Use check_duplicate_payment tool."
        ),
        expected_output="JSON duplicate true/false",
        agent=agent,
    )
    return str(Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False).kickoff())


def run_fraud(vendor: str, bank: str) -> str:
    agent = build_agent("fraud_signal")
    agent.tools = [check_vendor_fraud_signals]
    task = Task(
        description=f"Check fraud signals vendor={vendor} bank={bank}. Use check_vendor_fraud_signals tool.",
        expected_output="JSON signals list",
        agent=agent,
    )
    return str(Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False).kickoff())


def run_risk_scorer(evidence: dict[str, Any]) -> tuple[str, str]:
    agent = build_agent("risk_scorer")
    task = Task(
        description=(
            "Score risk LOW|MEDIUM|HIGH|CRITICAL with explanation. Return JSON "
            f"{{risk_score, explanation}}.\n\n{json.dumps(evidence, indent=2)}"
        ),
        expected_output="JSON risk_score and explanation",
        agent=agent,
    )
    raw = str(Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False).kickoff())
    data = _json(raw)
    risk = str(data.get("risk_score", "MEDIUM")).upper()
    if risk not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        risk = "MEDIUM"
    return risk, str(data.get("explanation", raw[:300]))


def run_router(risk: str, evidence: dict[str, Any]) -> str:
    agent = build_agent("approval_router")
    task = Task(
        description=(
            "Route invoice based on risk. Return JSON {decision, detail}. "
            "decision must be one of: AUTO_APPROVED, PENDING_AP, PENDING_CFO, BLOCKED. "
            "You must NOT submit payment.\n\n"
            f"Risk: {risk}\nEvidence: {json.dumps(evidence)[:2000]}"
        ),
        expected_output="JSON decision and detail",
        agent=agent,
    )
    return str(Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False).kickoff())


def agent_model(agent_id: str) -> str:
    from crew.agents.registry import get_agent

    spec = get_agent(agent_id)
    return model_name(expensive=(spec.model_tier == "expensive"))


def _json(raw: str) -> dict[str, Any]:
    import re

    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return {}
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        return {}
