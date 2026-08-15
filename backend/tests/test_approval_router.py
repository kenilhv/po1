"""10 edge-case tests for approval_router agent."""

from __future__ import annotations

from crew.agents.rules import parse_router_decision, route_rules


class TestApprovalRouter:
    def test_low_risk_auto_approved(self):
        assert route_rules("LOW") == "AUTO_APPROVED"

    def test_medium_risk_pending_ap(self):
        assert route_rules("MEDIUM") == "PENDING_AP"

    def test_high_risk_pending_cfo(self):
        assert route_rules("HIGH") == "PENDING_CFO"

    def test_critical_risk_blocked(self):
        assert route_rules("CRITICAL") == "BLOCKED"

    def test_lowercase_risk_normalized(self):
        assert route_rules("low") == "AUTO_APPROVED"

    def test_invalid_risk_defaults_to_pending_ap(self):
        assert route_rules("UNKNOWN") == "PENDING_AP"

    def test_empty_risk_defaults_to_pending_ap(self):
        assert route_rules("") == "PENDING_AP"

    def test_parse_valid_llm_json(self):
        raw = '{"decision": "PENDING_CFO", "detail": "High risk duplicate"}'
        decision, detail = parse_router_decision(raw, "HIGH")
        assert decision == "PENDING_CFO"
        assert "duplicate" in detail

    def test_parse_invalid_decision_falls_back_to_rules(self):
        raw = '{"decision": "SUBMIT_PAYMENT", "detail": "bad"}'
        decision, _ = parse_router_decision(raw, "LOW")
        assert decision == "AUTO_APPROVED"

    def test_parse_malformed_json_uses_rule_fallback(self):
        decision, detail = parse_router_decision("not json at all", "CRITICAL")
        assert decision == "BLOCKED"
        assert "BLOCKED" in detail
