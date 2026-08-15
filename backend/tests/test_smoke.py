"""Regression smoke tests — run after fixes to confirm full stack."""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestSmoke:
    def test_all_agent_rule_modules_import(self):
        from crew.agents import rules
        from crew.tools import po_tool, crew_tools

        assert callable(rules.parse_invoice_rules)
        assert callable(po_tool.lookup_po)
        assert hasattr(crew_tools.lookup_purchase_order, "func")
        assert callable(crew_tools.lookup_purchase_order.func)

    def test_verify_api_still_passes(self):
        from database.db import init_db
        from database import seed
        from main import app

        init_db()
        seed.seed()
        client = TestClient(app)

        login = client.post("/v1/auth/login", json={"code": "AP2024"}).json()
        h = {"Authorization": f"Bearer {login['token']}"}
        assert client.get("/v1/ap/stats", headers=h).status_code == 200
        assert isinstance(client.get("/v1/ap/invoices", headers=h).json(), list)

        cfo = client.post("/v1/auth/login", json={"code": "CFO2024"}).json()
        ch = {"Authorization": f"Bearer {cfo['token']}"}
        assert client.get("/v1/cfo/pending-approvals", headers=ch).status_code == 200

    def test_risk_to_decision_mapping_consistent(self):
        from crew.agents.rules import route_rules, score_risk_rules

        scenarios = [
            ({"po": {"match": True}, "duplicate": {"duplicate": False}, "fraud": {"flagged": False, "signals": []}, "amount": 800}, "LOW", "AUTO_APPROVED"),
            ({"po": {"match": False}, "duplicate": {"duplicate": False}, "fraud": {"flagged": False, "signals": []}, "amount": 500}, "MEDIUM", "PENDING_AP"),
            ({"po": {"match": True}, "duplicate": {"duplicate": True, "detail": "dup"}, "fraud": {"flagged": False, "signals": []}, "amount": 1200}, "HIGH", "PENDING_CFO"),
            ({"po": {"match": False}, "duplicate": {"duplicate": False}, "fraud": {"flagged": True, "signals": ["flagged"]}, "amount": 45000}, "CRITICAL", "BLOCKED"),
        ]
        for evidence, expected_risk, expected_decision in scenarios:
            risk, _ = score_risk_rules(evidence)
            assert risk == expected_risk
            assert route_rules(risk) == expected_decision
