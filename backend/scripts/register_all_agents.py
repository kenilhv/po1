"""Register every PO1 agent with Band as its own remote agent.

The AP floor should read like a room full of specialists, not one narrator.
Each agent posts findings under its own identity, so the transcript shows
three_way_matcher handing evidence to exception_classifier, and the controller
being pulled in when a vendor's banking details change.

Needs the HUMAN REST API key from the Band dashboard (Settings -> REST API
Keys). An agent key cannot register other agents.

    BAND_HUMAN_KEY=<key> python scripts/register_all_agents.py

Writes the resulting identities to backend/band_agents.json.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

BASE = os.getenv("BAND_BASE_URL", "https://app.band.ai/api/v1")
HUMAN_KEY = os.getenv("BAND_HUMAN_KEY", "")
OUT = ROOT / "band_agents.json"

# The orchestrator is already registered; these are its colleagues on the floor.
AGENTS = [
    ("vendor_onboarder", "PO1 Vendor Onboarder",
     "Gates every invoice on vendor master data: verifies the W-9 and tax ID are on file "
     "and flags any change to a known vendor's banking details."),
    ("invoice_parser", "PO1 Invoice Parser",
     "Extracts vendor, amount, invoice number, PO reference and payment terms from the raw document."),
    ("three_way_matcher", "PO1 Three-Way Matcher",
     "Compares the invoice against both the purchase order and the goods receipt, "
     "reporting which of the three legs agree."),
    ("duplicate_detector", "PO1 Duplicate Detector",
     "Checks payment history for an invoice number already paid to this vendor."),
    ("fraud_signal", "PO1 Fraud Signal",
     "Screens vendor and banking signals for indicators that a payment should not go out."),
    ("gl_coder", "PO1 GL Coder",
     "Assigns the general-ledger account and cost centre so spend can be checked against budget."),
    ("exception_classifier", "PO1 Exception Classifier",
     "Reads every upstream finding and names one typed exception with the team that owns "
     "resolving it, rather than a single blended risk score."),
    ("risk_scorer", "PO1 Risk Scorer",
     "Scores the severity of a typed exception given the amount, the vendor's history "
     "and the size of any variance."),
    ("approval_router", "PO1 Approval Router",
     "Applies delegation-of-authority limits and decides whether the agent may clear a "
     "payment alone, or must buy human judgment."),
    ("payment_scheduler", "PO1 Payment Scheduler",
     "Times payment to capture early-payment discounts instead of paying the instant an "
     "invoice clears."),
    ("controller", "PO1 Controller",
     "The specialist pulled into a case at runtime when a vendor's banking details change. "
     "Banking changes are never self-approved."),
]


def register(name: str, description: str) -> dict | None:
    r = requests.post(
        f"{BASE}/me/agents/register",
        headers={"X-API-Key": HUMAN_KEY, "Content-Type": "application/json"},
        json={"agent": {"name": name, "description": description}},
        timeout=30,
    )
    if r.status_code >= 400:
        print(f"  FAILED {name}: {r.status_code} {r.text[:200]}")
        return None
    # Band returns {data: {credentials: {api_key}, agent: {id, name, ...}}}
    # and the key is shown exactly once, so flatten it here.
    data = r.json().get("data") or {}
    agent = data.get("agent") or {}
    return {
        "id": agent.get("id"),
        "api_key": (data.get("credentials") or {}).get("api_key"),
        "handle": agent.get("handle"),
        "name": agent.get("name") or name,
    }


def main() -> None:
    if not HUMAN_KEY:
        sys.exit(
            "Set BAND_HUMAN_KEY to the human REST API key from the Band dashboard\n"
            "(Settings -> REST API Keys). An agent key cannot register agents."
        )

    registry: dict[str, dict] = {}
    if OUT.exists():
        registry = json.loads(OUT.read_text())

    for slug, name, desc in AGENTS:
        if slug in registry:
            print(f"  have {slug}")
            continue
        data = register(name, desc)
        if not data:
            continue
        if not data.get("api_key"):
            print(f"  FAILED {slug}: no api_key in response")
            continue
        registry[slug] = data
        print(f"  registered {slug:22} key ok  id={str(data.get('id'))[:8]}")
        OUT.write_text(json.dumps(registry, indent=2))

    print(f"\n{len(registry)} agents in {OUT}")
    print("Add each to the Band room, then restart the API so they post under their own names.")


if __name__ == "__main__":
    main()
