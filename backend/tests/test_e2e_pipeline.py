"""End-to-end pipeline tests for all 6 agents working together."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo_invoices"


async def _run_pipeline(pdf_name: str) -> tuple[list[dict], dict | None]:
    from database.db import get_conn
    from crew.orchestrator import run_invoice_pipeline

    pdf_path = str(DEMO / pdf_name)
    events: list[dict] = []

    async def on_agent(msg: dict) -> None:
        events.append(msg)

    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO invoices (filename, status) VALUES (?, 'processing')",
            (pdf_name,),
        )
        conn.commit()
        invoice_id = cur.lastrowid

    await run_invoice_pipeline(invoice_id, pdf_path, on_agent)

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()

    return events, dict(row) if row else None


def _completed_agents(events: list[dict]) -> list[str]:
    return [e["agent"] for e in events if e.get("status") == "complete"]


class TestE2EPipeline:
    @pytest.mark.asyncio
    async def test_good_invoice_low_auto_approved(self):
        events, inv = await _run_pipeline("invoice_good.pdf")
        assert inv is not None
        assert inv["risk_score"] == "LOW"
        assert inv["decision"] == "AUTO_APPROVED"
        assert inv["vendor_name"] == "OfficeSupplyCo"
        completed = _completed_agents(events)
        assert completed == [
            "invoice_parser",
            "po_matcher",
            "duplicate_detector",
            "fraud_signal",
            "risk_scorer",
            "approval_router",
        ]

    @pytest.mark.asyncio
    async def test_duplicate_invoice_high_pending_cfo(self):
        events, inv = await _run_pipeline("invoice_duplicate.pdf")
        assert inv["risk_score"] == "HIGH"
        assert inv["decision"] == "PENDING_CFO"
        assert inv["vendor_name"] == "TechSoftware Inc"
        dup_events = [e for e in events if e["agent"] == "duplicate_detector" and e["status"] == "complete"]
        assert dup_events[0]["result"] == "duplicate_found"

    @pytest.mark.asyncio
    async def test_fraud_invoice_critical_blocked(self):
        events, inv = await _run_pipeline("invoice_fraud.pdf")
        assert inv["risk_score"] == "CRITICAL"
        assert inv["decision"] == "BLOCKED"
        assert inv["vendor_name"] == "FastConsult LLC"
        fraud_events = [e for e in events if e["agent"] == "fraud_signal" and e["status"] == "complete"]
        assert fraud_events[0]["result"] == "signals_found"

    @pytest.mark.asyncio
    async def test_pipeline_emits_running_then_complete_per_agent(self):
        events, _ = await _run_pipeline("invoice_good.pdf")
        parsers = [e for e in events if e["agent"] == "invoice_parser"]
        assert parsers[0]["status"] == "running"
        assert parsers[1]["status"] == "complete"

    @pytest.mark.asyncio
    async def test_parallel_agents_all_complete(self):
        events, _ = await _run_pipeline("invoice_good.pdf")
        for agent in ("po_matcher", "duplicate_detector", "fraud_signal"):
            completed = [e for e in events if e["agent"] == agent and e["status"] == "complete"]
            assert len(completed) == 1

    @pytest.mark.asyncio
    async def test_invoice_db_fields_populated(self):
        _, inv = await _run_pipeline("invoice_good.pdf")
        assert inv["amount"] == 800.0
        assert inv["invoice_number"] == "INV-2024-441"
        assert inv["po_reference"] == "PO-8821"
        assert inv["bank_details"] == "ACC-001-VALID"
