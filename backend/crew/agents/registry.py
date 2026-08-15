"""Agent registry for InvoiceOS — share with Aditya for TrueFoundry Agent Gateway + MCP guardrails."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentSpec:
    id: str
    name: str
    tier: str  # L1 Observe | L2 Advise | L3 Act w/ approval
    model_tier: str  # cheap | expensive
    tools: list[str]
    description: str
    guardrails: list[str] = field(default_factory=list)


MCP_SERVER_NAME = "invoice-os-mcp"
MCP_TOOLS = [
    "lookup_purchase_order",
    "check_duplicate_payment",
    "check_vendor_fraud_signals",
    "submit_payment",  # L3 — Aditya MUST block without human approval
    "write_audit_log",
]

AGENTS: list[AgentSpec] = [
    AgentSpec(
        id="invoice_parser",
        name="Invoice Parser",
        tier="L1",
        model_tier="cheap",
        tools=["extract_pdf_text"],
        description="Extract vendor, amount, PO, bank details from PDF.",
        guardrails=["read-only", "no external writes", "token budget: 4k"],
    ),
    AgentSpec(
        id="po_matcher",
        name="PO Matcher",
        tier="L1",
        model_tier="cheap",
        tools=["lookup_purchase_order"],
        description="Match invoice to purchase order in SQLite.",
        guardrails=["read-only DB", "MCP scoped to PO lookup"],
    ),
    AgentSpec(
        id="duplicate_detector",
        name="Duplicate Detector",
        tier="L1",
        model_tier="cheap",
        tools=["check_duplicate_payment"],
        description="Detect duplicate payments in history.",
        guardrails=["read-only DB", "MCP scoped to payments read"],
    ),
    AgentSpec(
        id="fraud_signal",
        name="Fraud Signal Agent",
        tier="L2",
        model_tier="expensive",
        tools=["check_vendor_fraud_signals"],
        description="Flag unknown vendors, bank mismatches, suspicious amounts.",
        guardrails=["read-only vendor registry", "hallucination check on output"],
    ),
    AgentSpec(
        id="risk_scorer",
        name="Risk Scorer",
        tier="L2",
        model_tier="expensive",
        tools=[],
        description="Synthesize PO + duplicate + fraud into LOW/MEDIUM/HIGH/CRITICAL.",
        guardrails=["no tool access", "structured JSON output only"],
    ),
    AgentSpec(
        id="approval_router",
        name="Approval Router",
        tier="L3",
        model_tier="cheap",
        tools=["write_audit_log"],
        description="Route decision — NEVER submits payment autonomously.",
        guardrails=[
            "BLOCK submit_payment always",
            "BLOCK any output containing 'payment sent' or 'payment approved'",
            "human approval required before submit_payment",
        ],
    ),
]


def agent_ids() -> list[str]:
    return [a.id for a in AGENTS]


def get_agent(agent_id: str) -> AgentSpec:
    for a in AGENTS:
        if a.id == agent_id:
            return a
    raise KeyError(agent_id)
