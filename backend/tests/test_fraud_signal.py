"""10 edge-case tests for fraud_signal agent."""

from __future__ import annotations

from crew.tools.po_tool import lookup_vendor


class TestFraudSignal:
    def test_unknown_vendor_flagged(self):
        result = lookup_vendor("GhostVendor Inc", "ACC-000")
        assert result["known"] is False
        assert result["flagged"] is True
        assert "Unknown vendor" in result["signals"]

    def test_flagged_vendor_in_registry(self):
        result = lookup_vendor("FastConsult LLC", "ACC-999-SUSPICIOUS")
        assert result["flagged"] is True
        assert "Vendor flagged in registry" in result["signals"]

    def test_bank_mismatch_on_known_vendor(self):
        result = lookup_vendor("OfficeSupplyCo", "ACC-WRONG-BANK")
        assert "Bank account mismatch" in result["signals"]

    def test_correct_bank_no_mismatch(self):
        result = lookup_vendor("OfficeSupplyCo", "ACC-001-VALID")
        assert "Bank account mismatch" not in result["signals"]

    def test_empty_bank_skips_mismatch_check(self):
        result = lookup_vendor("TechSoftware Inc", "")
        assert "Bank account mismatch" not in result["signals"]
        assert result["known"] is True

    def test_clean_vendor_no_signals(self):
        result = lookup_vendor("CleanVendor Inc", "ACC-003-VALID")
        assert result["flagged"] is False
        assert result["signals"] == []

    def test_fastconsult_matching_bank_still_flagged(self):
        result = lookup_vendor("FastConsult LLC", "ACC-999-SUSPICIOUS")
        assert result["flagged"] is True
        assert len(result["signals"]) >= 1

    def test_empty_vendor_name_unknown(self):
        result = lookup_vendor("", "ACC-001")
        assert result["flagged"] is True
        assert "Unknown vendor" in result["signals"]

    def test_known_vendor_not_flagged_in_registry(self):
        result = lookup_vendor("PaperWorks Ltd", "ACC-004-VALID")
        assert result["known"] is True
        assert result["flagged"] is False

    def test_whitespace_bank_treated_as_empty(self):
        result = lookup_vendor("OfficeSupplyCo", "   ")
        assert "Bank account mismatch" not in result["signals"]
