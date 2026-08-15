"""10 edge-case tests for risk_scorer agent."""

from __future__ import annotations

from crew.agents.rules import score_risk_rules


def _evidence(*, po_match=True, duplicate=False, flagged=False, signals=None, amount=800.0):
    return {
        "po": {"match": po_match, "po_number": "PO-8821"} if po_match else {"match": False, "detail": "No PO"},
        "duplicate": {"duplicate": duplicate, "detail": "Duplicate"} if duplicate else {"duplicate": False},
        "fraud": {"flagged": flagged, "signals": signals or []},
        "amount": amount,
        "vendor": "TestVendor",
    }


class TestRiskScorer:
    def test_all_clean_low_risk(self):
        risk, detail = score_risk_rules(_evidence())
        assert risk == "LOW"
        assert "passed" in detail.lower()

    def test_duplicate_high_risk(self):
        risk, _ = score_risk_rules(_evidence(duplicate=True))
        assert risk == "HIGH"

    def test_no_po_medium_risk(self):
        risk, detail = score_risk_rules(_evidence(po_match=False, amount=500))
        assert risk == "MEDIUM"
        assert "purchase order" in detail.lower()

    def test_flagged_vendor_critical(self):
        risk, _ = score_risk_rules(_evidence(flagged=True, signals=["Vendor flagged in registry"]))
        assert risk == "CRITICAL"

    def test_large_amount_no_po_critical(self):
        risk, detail = score_risk_rules(_evidence(po_match=False, amount=45000))
        assert risk == "CRITICAL"
        assert "large amount" in detail.lower()

    def test_duplicate_overrides_medium_po_miss(self):
        risk, _ = score_risk_rules(_evidence(po_match=False, duplicate=True, amount=500))
        assert risk == "HIGH"

    def test_fraud_signals_without_flag_medium(self):
        risk, _ = score_risk_rules(
            _evidence(signals=["Bank account mismatch"], flagged=False, po_match=True)
        )
        assert risk == "MEDIUM"

    def test_zero_amount_clean_po_low(self):
        risk, _ = score_risk_rules(_evidence(amount=0))
        assert risk == "LOW"

    def test_flagged_takes_precedence_over_duplicate(self):
        risk, _ = score_risk_rules(_evidence(flagged=True, duplicate=True))
        assert risk == "CRITICAL"

    def test_amount_exactly_10000_no_po_is_medium_not_critical(self):
        risk, _ = score_risk_rules(_evidence(po_match=False, amount=10000))
        assert risk == "MEDIUM"
