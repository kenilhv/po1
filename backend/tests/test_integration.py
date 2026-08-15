"""Additional integration tests for agent tool wrappers and pipeline helpers."""

from __future__ import annotations

import json

from crew.tools.crew_tools import (
    check_duplicate_payment,
    check_vendor_fraud_signals,
    lookup_purchase_order,
)


class TestCrewToolWrappers:
    def test_lookup_purchase_order_returns_json_string(self):
        raw = lookup_purchase_order.func("OfficeSupplyCo", "PO-8821")
        data = json.loads(raw)
        assert data["match"] is True

    def test_check_duplicate_payment_returns_json(self):
        raw = check_duplicate_payment.func("TechSoftware Inc", 1200.0, "INV-X")
        data = json.loads(raw)
        assert data["duplicate"] is True

    def test_check_fraud_signals_unknown_vendor(self):
        raw = check_vendor_fraud_signals.func("Unknown Co", "ACC-1")
        data = json.loads(raw)
        assert data["flagged"] is True

    def test_lookup_po_wrong_ref_via_tool(self):
        raw = lookup_purchase_order.func("OfficeSupplyCo", "PO-7743")
        data = json.loads(raw)
        assert data["match"] is False

    def test_full_evidence_chain_good_invoice(self):
        from crew.agents.rules import parse_invoice_rules, route_rules, score_risk_rules
        from crew.tools.pdf_tool import extract_pdf_text
        from crew.tools.po_tool import lookup_duplicate, lookup_po, lookup_vendor
        from pathlib import Path

        text = extract_pdf_text(str(Path(__file__).parents[1] / "demo_invoices" / "invoice_good.pdf"))
        parsed = parse_invoice_rules(text)
        po = lookup_po(parsed["vendor_name"], parsed.get("po_reference"))
        dup = lookup_duplicate(parsed["vendor_name"], parsed["amount"], parsed["invoice_number"])
        fraud = lookup_vendor(parsed["vendor_name"], parsed.get("bank_details"))
        evidence = {"po": po, "duplicate": dup, "fraud": fraud, "amount": parsed["amount"]}
        risk, _ = score_risk_rules(evidence)
        decision = route_rules(risk)
        assert risk == "LOW"
        assert decision == "AUTO_APPROVED"
