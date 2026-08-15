"""10 edge-case tests for po_matcher agent (lookup_purchase_order tool)."""

from __future__ import annotations

from crew.tools.po_tool import lookup_po


class TestPoMatcher:
    def test_exact_po_and_vendor_match(self):
        result = lookup_po("OfficeSupplyCo", "PO-8821")
        assert result["match"] is True
        assert result["po_number"] == "PO-8821"
        assert result["amount"] == 800.0

    def test_vendor_only_match_when_po_omitted(self):
        result = lookup_po("TechSoftware Inc", None)
        assert result["match"] is True
        assert result["po_number"] == "PO-7743"

    def test_wrong_po_number_no_match(self):
        result = lookup_po("OfficeSupplyCo", "PO-9999")
        assert result["match"] is False
        assert "detail" in result

    def test_unknown_vendor_no_match(self):
        result = lookup_po("Nonexistent Vendor LLC", "PO-8821")
        assert result["match"] is False

    def test_empty_vendor_name(self):
        result = lookup_po("", "PO-8821")
        assert result["match"] is False

    def test_empty_po_ref_falls_back_to_vendor(self):
        result = lookup_po("CleanVendor Inc", "")
        assert result["match"] is True
        assert result["po_number"] == "PO-9901"

    def test_po_belongs_to_different_vendor(self):
        result = lookup_po("OfficeSupplyCo", "PO-7743")
        assert result["match"] is False

    def test_whitespace_po_ref_treated_as_missing(self):
        result = lookup_po("PaperWorks Ltd", "   ")
        assert result["match"] is True

    def test_amount_returned_on_match(self):
        result = lookup_po("PaperWorks Ltd", "PO-4412")
        assert result["match"] is True
        assert result["amount"] == 350.0

    def test_multiple_pos_same_vendor_returns_first(self):
        result = lookup_po("OfficeSupplyCo", None)
        assert result["match"] is True
        assert "po_number" in result
