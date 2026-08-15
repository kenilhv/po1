"""10 edge-case tests for invoice_parser agent (rule-based)."""

from __future__ import annotations

from crew.agents.rules import parse_invoice_rules
from crew.orchestrator import _parse_invoice


GOOD_TEXT = """
INVOICE
Vendor: OfficeSupplyCo
Invoice Number: INV-2024-441
Amount: $800.00
PO Reference: PO-8821
Bank Account: ACC-001-VALID
"""


class TestInvoiceParser:
    def test_parses_demo_office_supply(self):
        result = parse_invoice_rules(GOOD_TEXT)
        assert result["vendor_name"] == "OfficeSupplyCo"
        assert result["amount"] == 800.0
        assert result["po_reference"] == "PO-8821"

    def test_parses_comma_formatted_amount(self):
        text = """
        Vendor: TechSoftware Inc
        Invoice Number: INV-9921
        Amount: $1,200.00
        PO Reference: PO-7743
        Bank Account: ACC-002-VALID
        """
        result = parse_invoice_rules(text)
        assert result["amount"] == 1200.0
        assert result["vendor_name"] == "TechSoftware Inc"

    def test_parses_fraud_invoice_without_po(self):
        text = """
        Vendor: FastConsult LLC
        Invoice Number: INV-F-0042
        Amount: $45,000.00
        Bank Account: ACC-999-SUSPICIOUS
        """
        result = parse_invoice_rules(text)
        assert result["vendor_name"] == "FastConsult LLC"
        assert result["amount"] == 45000.0
        assert result.get("po_reference") is None

    def test_empty_text_returns_empty_dict(self):
        assert parse_invoice_rules("") == {}
        assert parse_invoice_rules("   \n  ") == {}

    def test_generic_vendor_extraction(self):
        text = """
        Vendor: Mystery Corp
        Invoice Number: INV-0001
        Amount: $250.00
        PO Reference: PO-XXXX
        Bank Account: ACC-UNKNOWN
        """
        result = parse_invoice_rules(text)
        assert result["vendor_name"] == "Mystery Corp"
        assert result["amount"] == 250.0
        assert result["invoice_number"] == "INV-0001"

    def test_missing_optional_fields_use_defaults(self):
        text = "Vendor: SoloVendor\nAmount: $99.00"
        result = parse_invoice_rules(text)
        assert result["vendor_name"] == "SoloVendor"
        assert result["amount"] == 99.0
        assert result["invoice_number"] == ""
        assert result["bank_details"] == ""

    def test_garbage_text_without_invoice_markers(self):
        assert parse_invoice_rules("hello world random notes") == {}

    def test_orchestrator_parse_uses_rules_when_llm_off(self, monkeypatch):
        monkeypatch.setenv("USE_LLM", "0")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        result = _parse_invoice(GOOD_TEXT)
        assert result["vendor_name"] == "OfficeSupplyCo"

    def test_long_text_still_parses_known_vendor(self):
        padding = "noise line\n" * 500
        result = parse_invoice_rules(padding + GOOD_TEXT + padding)
        assert result["vendor_name"] == "OfficeSupplyCo"

    def test_case_insensitive_field_labels(self):
        text = """
        vendor: PaperWorks Ltd
        invoice number: INV-2024-400
        amount: $350.00
        po reference: PO-4412
        bank account: ACC-004-VALID
        """
        result = parse_invoice_rules(text)
        assert result["vendor_name"] == "PaperWorks Ltd"
        assert result["amount"] == 350.0
