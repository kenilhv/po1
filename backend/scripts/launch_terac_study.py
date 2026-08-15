"""Launch the Terac labeling study that trains PO1's fraud model.

This is the hackathon's core requirement in one script: collect real human
judgment during the event, then use it to make the system measurably better.

    python scripts/launch_terac_study.py --participants 8 --dry-run
    python scripts/launch_terac_study.py --participants 8

A draft costs nothing, so --dry-run builds one, prints the real price, and
stops. Drop the flag to launch for real.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

BASE = os.getenv("TERAC_BASE_URL", "https://terac.com/api/external/v2")
KEY = os.getenv("TERAC_API_KEY", "")
PUBLIC = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}


def api(method: str, path: str, payload: dict | None = None) -> dict:
    r = requests.request(method, f"{BASE}{path}", headers=H, json=payload, timeout=40)
    if r.status_code >= 400:
        sys.exit(f"{method} {path} -> {r.status_code}: {r.text[:400]}")
    return r.json() if r.content else {}


def balance_dollars() -> float:
    ctx = api("GET", "/organizations/current/context")
    md = ctx.get("markdown", "")
    for line in md.splitlines():
        if "Balance:" in line:
            try:
                return float(line.split("$")[1].split()[0].replace(",", ""))
            except (IndexError, ValueError):
                pass
    return 0.0


def ensure_project(name: str = "PO1 — Autonomous AP") -> str:
    for p in api("GET", "/projects").get("data") or []:
        if p.get("name") == name:
            return str(p["id"])
    return str((api("POST", "/projects", {"name": name}).get("data") or {}).get("id"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--participants", type=int, default=8)
    ap.add_argument("--minutes", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not KEY:
        sys.exit("TERAC_API_KEY is not set")
    if not PUBLIC or "localhost" in PUBLIC or "127.0.0.1" in PUBLIC:
        sys.exit(
            "PUBLIC_BASE_URL must be a public URL participants can reach.\n"
            "Deploy to Render first, then set it in backend/.env."
        )

    label_url = f"{PUBLIC}/label"
    print(f"Task URL : {label_url}")

    bal = balance_dollars()
    print(f"Balance  : ${bal:,.2f}")

    project_id = ensure_project()
    print(f"Project  : {project_id}")

    body = {
        "title": "Which of these business bills look risky to pay?",
        "internal_title": "PO1 fraud-signal training labels",
        "description": (
            "You'll see a few real business invoices. For each one, say whether a "
            "company should pay it right away or check it first, and why in a few "
            "words. No accounting background needed — we want ordinary judgment "
            "about what looks off. Takes about three minutes."
        ),
        "project_id": project_id,
        "num_participants": args.participants,
        "business_type": "b2c",
        "unrestricted_audience": True,  # general population fills fastest
        "expected_days_to_complete": 5,  # API minimum
        "tasks": [
            {
                "sequence": 1,
                "task_type": "activity",
                "review_type": "auto_approve",
                "task_url": label_url,
                "title": "Label invoices as risky or safe",
                "description": "Mark each invoice risky or safe and say why in a few words.",
                "duration_minutes": args.minutes,
            }
        ],
    }

    draft = api("POST", "/opportunities", body)
    oid = str(draft.get("id"))
    print(f"Draft    : {oid}")

    # Pricing is computed asynchronously after creation.
    cost = 0.0
    for _ in range(6):
        time.sleep(5)
        pricing = api("GET", f"/opportunities/{oid}").get("pricing") or {}
        cost = (pricing.get("total_cost_cents") or 0) / 100
        if cost:
            break

    per = cost / args.participants if args.participants else 0
    print(f"Price    : ${cost:,.2f} total (${per:,.2f} x {args.participants})")

    if cost > bal:
        sys.exit(f"Balance ${bal:,.2f} is short of ${cost:,.2f}. Add credit or lower --participants.")

    links = (draft.get("links") or {}).get("dashboard") or {}
    if args.dry_run:
        print("\nDRY RUN — nothing launched, nothing charged.")
        print("Draft editor:", links.get("draft_editor", "—"))
        return

    api("POST", f"/opportunities/{oid}/launch")
    print(f"\nLAUNCHED — ${cost:,.2f} committed for {args.participants} participants.")
    print("Submissions:", links.get("study") or links.get("submissions") or "—")
    print("\nLabels will land at POST /po1/labels as people complete the task.")
    print("Watch the count on the dashboard, then run scripts/run_finetune.py.")


if __name__ == "__main__":
    main()
