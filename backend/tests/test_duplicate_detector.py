"""10 edge-case tests for duplicate_detector agent."""

from __future__ import annotations

from crew.tools.po_tool import lookup_duplicate


class TestDuplicateDetector:
    def test_exact_amount_match_in_payment_history(self):
        result = lookup_duplicate("TechSoftware Inc", 1200.0, "INV-NEW-001")
        assert result["duplicate"] is True
        assert "matches" in result

    def test_invoice_number_references_paid_inv_9891(self):
        result = lookup_duplicate("SomeVendor", 50.0, "INV-9891-REISSUE")
        assert result["duplicate"] is True
        assert "9891" in result["detail"]

    def test_unique_vendor_amount_is_clean(self):
        result = lookup_duplicate("OfficeSupplyCo", 800.0, "INV-2024-441")
        assert result["duplicate"] is False

    def test_amount_within_one_dollar_tolerance(self):
        result = lookup_duplicate("TechSoftware Inc", 1200.50, "INV-X")
        assert result["duplicate"] is True

    def test_same_amount_different_vendor_is_clean(self):
        result = lookup_duplicate("OfficeSupplyCo", 1200.0, "INV-UNIQUE")
        assert result["duplicate"] is False

    def test_zero_amount_no_history_match(self):
        result = lookup_duplicate("CleanVendor Inc", 0.0, "INV-ZERO")
        assert result["duplicate"] is False

    def test_empty_invoice_number_no_special_rule(self):
        result = lookup_duplicate("OfficeSupplyCo", 800.0, "")
        assert result["duplicate"] is False

    def test_clean_vendor_existing_payment_amount(self):
        result = lookup_duplicate("CleanVendor Inc", 500.0, "INV-NEW")
        assert result["duplicate"] is True

    def test_paperworks_exact_payment_duplicate(self):
        result = lookup_duplicate("PaperWorks Ltd", 350.0, "INV-2024-999")
        assert result["duplicate"] is True

    def test_slightly_outside_tolerance_is_clean(self):
        result = lookup_duplicate("TechSoftware Inc", 1198.0, "INV-OK")
        assert result["duplicate"] is False
