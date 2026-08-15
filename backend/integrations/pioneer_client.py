"""PO1 — Pioneer (Fastino Labs): fine-tune fraud_signal on real human labels.

The loop this implements is the hackathon's core requirement — real human
input making the project measurably better, with a before/after you can check:

    1. Baseline the current fraud_signal on a fixed test batch.
    2. Terac panel labels real invoices (risky / safe, and why).
    3. Fine-tune an open-weight model on those labels via Pioneer.
    4. Re-run the SAME fixed batch against the fine-tuned model.
    5. Report the delta in accuracy and cost per call.

Docs: https://docs.pioneer.ai/guides/fine-tune-llm
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import requests

from database.db import get_conn

BASE = os.getenv("PIONEER_BASE_URL", "https://api.pioneer.ai")
API_KEY = os.getenv("PIONEER_API_KEY", "")
# Small open-weight instruct model — fastest to fine-tune for a narrow
# binary-with-reasoning task, which is what fraud triage is.
BASE_MODEL = os.getenv("PIONEER_BASE_MODEL", "meta-llama/Llama-3.2-1B-Instruct")
TIMEOUT = 60

SYSTEM_PROMPT = (
    "You are an accounts-payable fraud triage model. Given an invoice summary, "
    "answer with 'risky' or 'safe' followed by a one-sentence reason."
)


def is_configured() -> bool:
    return bool(API_KEY)


def _headers() -> dict[str, str]:
    return {"X-API-Key": API_KEY, "Content-Type": "application/json"}


# ------------------------------------------------------------------ dataset

def build_training_jsonl(labels: list[dict[str, Any]]) -> str:
    """Turn Terac human labels into Pioneer's chat JSONL format."""
    lines = []
    for item in labels:
        verdict = str(item.get("verdict", "")).lower()
        verdict = "risky" if verdict in ("risky", "reject", "rejected", "investigate") else "safe"
        reason = item.get("reasoning") or "Consistent with the vendor's history."
        lines.append(
            json.dumps(
                {
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": item["invoice_summary"]},
                        {"role": "assistant", "content": f"{verdict} — {reason}"},
                    ]
                }
            )
        )
    return "\n".join(lines)


def upload_dataset(name: str, jsonl: str) -> dict[str, Any]:
    resp = requests.post(
        f"{BASE}/datasets",
        headers=_headers(),
        json={"dataset_name": name, "task_type": "decoder", "data": jsonl},
        timeout=TIMEOUT,
    )
    if resp.status_code >= 400:
        # Fall back to the multipart upload shape if the JSON body isn't accepted.
        resp = requests.post(
            f"{BASE}/datasets",
            headers={"X-API-Key": API_KEY},
            files={"file": (f"{name}.jsonl", jsonl, "application/jsonl")},
            data={"dataset_name": name, "task_type": "decoder"},
            timeout=TIMEOUT,
        )
    return {"status": resp.status_code, "body": resp.text[:500]}


# ----------------------------------------------------------------- training

def start_finetune(dataset_name: str, model_name: str = "po1-fraud-signal") -> dict[str, Any]:
    resp = requests.post(
        f"{BASE}/felix/training-jobs",
        headers=_headers(),
        json={
            "model_name": model_name,
            "base_model": BASE_MODEL,
            "training_type": "lora",
            "datasets": [{"name": dataset_name, "version": "1"}],
            "lora_r": 16,
            "lora_alpha": 32,
            "learning_rate": 2e-5,
            "nr_epochs": 3,
        },
        timeout=TIMEOUT,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"fine-tune start failed {resp.status_code}: {resp.text[:400]}")
    return resp.json()


def job_status(job_id: str) -> dict[str, Any]:
    resp = requests.get(f"{BASE}/felix/training-jobs/{job_id}", headers=_headers(), timeout=TIMEOUT)
    return resp.json() if resp.status_code < 400 else {"status": "error", "detail": resp.text[:300]}


def wait_for_deploy(job_id: str, max_wait_s: int = 1200, poll_s: int = 20) -> dict[str, Any]:
    deadline = time.time() + max_wait_s
    last: dict[str, Any] = {}
    while time.time() < deadline:
        last = job_status(job_id)
        state = str(last.get("status", "")).lower()
        if state in ("deployed", "complete", "completed"):
            return last
        if state in ("failed", "error", "cancelled"):
            raise RuntimeError(f"fine-tune {state}: {json.dumps(last)[:300]}")
        time.sleep(poll_s)
    return last


# ---------------------------------------------------------------- inference

def classify(invoice_summary: str, model_id: str | None = None) -> dict[str, Any]:
    """Run fraud triage. Uses the fine-tuned model when one is available."""
    model = model_id or os.getenv("PIONEER_MODEL_ID") or BASE_MODEL
    started = time.time()
    resp = requests.post(
        f"{BASE}/inference",
        headers=_headers(),
        json={
            "model_id": model,
            "task": "generate",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": invoice_summary},
            ],
        },
        timeout=TIMEOUT,
    )
    elapsed = time.time() - started

    if resp.status_code >= 400:
        return {"error": resp.text[:300], "model": model, "latency_s": elapsed}

    data = resp.json()
    text = (
        data.get("output")
        or data.get("text")
        or (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
    )
    lowered = str(text).lower()
    return {
        "verdict": "risky" if "risky" in lowered else "safe",
        "raw": str(text)[:300],
        "model": model,
        "latency_s": round(elapsed, 2),
    }


# -------------------------------------------------------------- before/after

def evaluate(test_batch: list[dict[str, Any]], model_id: str | None = None) -> dict[str, Any]:
    """Score a fixed batch so before and after are directly comparable."""
    correct, total, latency = 0, 0, 0.0
    for case in test_batch:
        out = classify(case["invoice_summary"], model_id)
        if out.get("error"):
            continue
        total += 1
        latency += out.get("latency_s", 0)
        if out["verdict"] == case["expected"]:
            correct += 1
    return {
        "model": model_id or BASE_MODEL,
        "accuracy": round(correct / total, 3) if total else 0.0,
        "correct": correct,
        "total": total,
        "avg_latency_s": round(latency / total, 2) if total else 0.0,
    }


def record_run(
    target_agent: str,
    dataset_ref: str,
    label_count: int,
    before: dict[str, Any],
    after: dict[str, Any],
    notes: str = "",
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO finetune_runs
                (base_model, target_agent, dataset_ref, label_count,
                 metric_before, metric_after, cost_before, cost_after, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                BASE_MODEL,
                target_agent,
                dataset_ref,
                label_count,
                before.get("accuracy"),
                after.get("accuracy"),
                before.get("avg_latency_s"),
                after.get("avg_latency_s"),
                notes,
            ),
        )
        conn.commit()


def latest_run() -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM finetune_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return dict(row) if row else None
