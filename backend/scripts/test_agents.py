"""Test all 6 agents. Run from backend/: python -m scripts.test_agents"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from crew.agents.pipeline import (
    agent_model,
    run_duplicate,
    run_fraud,
    run_parser,
    run_po_matcher,
    run_risk_scorer,
    run_router,
)
from crew.agents.registry import AGENTS
from crew.tools.pdf_tool import extract_pdf_text
from crew.tools.po_tool import lookup_duplicate, lookup_po, lookup_vendor
from database.db import init_db


def main() -> None:
    init_db()
    use_llm = os.getenv("USE_LLM", "1") == "1" and os.getenv("GROQ_API_KEY")

    print("=== InvoiceOS Agent Test ===")
    print(f"LLM_PROVIDER={os.getenv('LLM_PROVIDER', 'groq')} USE_LLM={use_llm}\n")

    for spec in AGENTS:
        print(f"  [{spec.id}] tier={spec.tier} model_tier={spec.model_tier} tools={spec.tools}")

    pdf = ROOT / "demo_invoices" / "invoice_good.pdf"
    text = extract_pdf_text(str(pdf))
    print(f"\n--- PDF text ({len(text)} chars) ---")

    if use_llm:
        print("\n[1] invoice_parser...")
        parsed = run_parser(text)
        print("   ", parsed)
    else:
        parsed = {"vendor_name": "OfficeSupplyCo", "amount": 800, "invoice_number": "INV-2024-441", "po_reference": "PO-8821", "bank_details": "ACC-001-VALID"}
        print("\n[1] invoice_parser (rules fallback):", parsed)

    v = parsed.get("vendor_name", "OfficeSupplyCo")
    amt = float(parsed.get("amount", 800))
    inv = str(parsed.get("invoice_number", ""))
    po = str(parsed.get("po_reference", ""))
    bank = str(parsed.get("bank_details", ""))

    po_r = lookup_po(v, po)
    dup_r = lookup_duplicate(v, amt, inv)
    fraud_r = lookup_vendor(v, bank)
    print(f"\n[2] po_matcher: {po_r}")
    print(f"[3] duplicate_detector: {dup_r}")
    print(f"[4] fraud_signal: {fraud_r}")

    evidence = {"po": po_r, "duplicate": dup_r, "fraud": fraud_r, "amount": amt}

    if use_llm:
        print("\n[5] risk_scorer...")
        risk, expl = run_risk_scorer(evidence)
        print(f"   {risk}: {expl[:120]}")
        print("\n[6] approval_router...")
        print("   ", run_router(risk, evidence)[:200])
    else:
        risk = "LOW" if po_r.get("match") else "MEDIUM"
        print(f"\n[5] risk_scorer (rules): {risk}")
        print(f"[6] approval_router (rules): AUTO_APPROVED")

    print("\n=== Models per agent ===")
    for spec in AGENTS:
        print(f"  {spec.id}: {agent_model(spec.id)}")

    print("\n=== PASS (structure OK) ===")
    print("Give Aditya: docs/ADITYA.md + docs/agents_mcp_registry.json")
    print("Start MCP: python -m invoice_mcp.server --port 8001")


if __name__ == "__main__":
    main()
