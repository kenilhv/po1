#!/usr/bin/env python3
"""Upload all sample PDFs and verify risk/decision outcomes."""

from __future__ import annotations

import asyncio
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIR = ROOT / "sample_invoices"
BASE = "http://localhost:8000/v1"

# Import sample definitions for expected outcomes
sys.path.insert(0, str(Path(__file__).parent))
from generate_sample_pdfs import SAMPLES  # noqa: E402


def _login() -> str:
    req = urllib.request.Request(
        f"{BASE}/auth/login",
        data=json.dumps({"code": "AP2024"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return json.load(urllib.request.urlopen(req))["token"]


def _upload(token: str, path: Path) -> dict:
    boundary = f"----PayCrew{int(time.time() * 1000)}"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{BASE}/ap/invoices/upload",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    return json.load(urllib.request.urlopen(req))


def _poll_job(token: str, job_id: str, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        req = urllib.request.Request(
            f"{BASE}/ap/invoices/jobs/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        job = json.load(urllib.request.urlopen(req))
        if job.get("status") in ("complete", "failed"):
            return job
        time.sleep(0.3)
    raise TimeoutError(f"Job {job_id} did not complete")


def _extract_text(path: Path) -> str:
    doc = fitz.open(str(path))
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


def main() -> int:
    print("PayCrew Sample PDF Test Suite\n" + "=" * 60)
    try:
        token = _login()
    except urllib.error.URLError as e:
        print(f"FAIL — backend not reachable at {BASE}: {e}")
        return 1

    passed = 0
    failed = 0
    results = []

    for spec in SAMPLES:
        path = SAMPLE_DIR / spec["file"]
        exp_risk, exp_decision = spec["expect"]
        print(f"\n{spec['file']}")
        if not path.exists():
            print(f"  FAIL — file missing")
            failed += 1
            continue

        text = _extract_text(path)
        if "Vendor:" not in text:
            print(f"  WARN — parser fields may not extract cleanly")

        try:
            up = _upload(token, path)
            job = _poll_job(token, up["jobId"])
        except Exception as exc:
            print(f"  FAIL — {exc}")
            failed += 1
            continue

        if job.get("status") == "failed":
            print(f"  FAIL — job failed: {job.get('error')}")
            failed += 1
            continue

        inv = job.get("invoice") or {}
        risk = (inv.get("risk") or "").upper()
        decision = (inv.get("decision") or "").upper()
        agents = len(inv.get("agents") or [])
        ok = risk == exp_risk and decision == exp_decision and agents == 6

        status = "PASS" if ok else "FAIL"
        print(f"  {status} — risk={risk} decision={decision} agents={agents} amount=${inv.get('amount', 0):,.2f}")
        if not ok:
            print(f"         expected risk={exp_risk} decision={exp_decision}")
            failed += 1
        else:
            passed += 1

        results.append({
            "file": spec["file"],
            "expected": {"risk": exp_risk, "decision": exp_decision},
            "actual": {"risk": risk, "decision": decision, "amount": inv.get("amount"), "vendor": inv.get("vendor")},
            "pass": ok,
        })

    print("\n" + "=" * 60)
    print(f"RESULT: {passed}/{passed + failed} passed")
    manifest_path = SAMPLE_DIR / "test_results.json"
    manifest_path.write_text(json.dumps(results, indent=2))
    print(f"Details saved → {manifest_path}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
