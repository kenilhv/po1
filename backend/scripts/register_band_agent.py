"""Register PO1's orchestrator agent with Band.

Band issues two kinds of key. The one in the dashboard under "REST API Keys"
is a HUMAN key, and a fresh one is scoped Register-only — it can do exactly one
thing: mint an agent. The resulting AGENT key is what can post messages, read
peers, and add participants.

    python scripts/register_band_agent.py

Prints the agent id and agent API key to paste into backend/.env as
BAND_AGENT_ID and BAND_AGENT_API_KEY.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BASE = os.getenv("BAND_BASE_URL", "https://app.band.ai/api/v1")
HUMAN_KEY = os.getenv("BAND_API_KEY", "")

AGENT = {
    "name": "PO1 Orchestrator",
    "description": (
        "Runs an autonomous accounts-payable department. Coordinates ten agents "
        "that verify vendors, match invoices against purchase orders and goods "
        "receipts, classify exceptions, and decide what may be paid without a human."
    ),
}


def _try(method: str, path: str, payload: dict | None = None, key: str | None = None):
    for header in ({"X-API-Key": key or HUMAN_KEY}, {"Authorization": f"Bearer {key or HUMAN_KEY}"}):
        try:
            r = requests.request(
                method,
                f"{BASE}{path}",
                headers={**header, "Content-Type": "application/json"},
                json=payload,
                timeout=30,
            )
            if r.status_code < 400:
                return r.json() if r.content else {}
            print(f"  {method} {path} [{list(header)[0]}] -> {r.status_code}: {r.text[:200]}")
        except requests.RequestException as exc:
            print(f"  {method} {path} -> {exc}")
    return None


def main() -> None:
    if not HUMAN_KEY:
        sys.exit("BAND_API_KEY is not set in backend/.env")

    print(f"Registering with {BASE} ...")
    result = _try("POST", "/me/agents/register", AGENT)

    if not result:
        print("\nRegistration failed on every documented shape.")
        print("Check the dashboard: the key may need a scope beyond Register-only,")
        print("or the agent may already exist (grab its key from agent settings).")
        sys.exit(1)

    print("\nRegistered:\n" + json.dumps(result, indent=2)[:1200])

    agent_id = result.get("agent_id") or result.get("id") or (result.get("agent") or {}).get("id")
    agent_key = (
        result.get("api_key")
        or result.get("agent_api_key")
        or (result.get("agent") or {}).get("api_key")
    )

    print("\nPaste into backend/.env:")
    print(f"BAND_AGENT_ID={agent_id or '<see output above>'}")
    print(f"BAND_AGENT_API_KEY={agent_key or '<shown only once — see output above>'}")

    if agent_key:
        chats = _try("GET", "/agent/chats", key=agent_key)
        if chats:
            print("\nChats visible to this agent:")
            print(json.dumps(chats, indent=2)[:800])
            print("\nSet BAND_CHAT_ID to the room PO1 should post into.")


if __name__ == "__main__":
    main()
