"""Verify PayCrew v1 endpoints. Run: python -m scripts.verify_api"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from database.db import init_db
from database import seed

init_db()
seed.seed()

from main import app

client = TestClient(app)


def test_auth():
    r = client.post("/v1/auth/login", json={"code": "AP2024"})
    assert r.status_code == 200, r.text
    assert "token" in r.json() and r.json()["role"] == "ap"
    bad = client.post("/v1/auth/login", json={"code": "WRONG"})
    assert bad.status_code == 401
    token = r.json()["token"]
    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["role"] == "ap"
    out = client.post("/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert out.json()["success"] is True
    print("OK auth")


def test_ap():
    login = client.post("/v1/auth/login", json={"code": "AP2024"}).json()
    h = {"Authorization": f"Bearer {login['token']}"}
    assert client.get("/v1/ap/stats", headers=h).status_code == 200
    assert isinstance(client.get("/v1/ap/invoices", headers=h).json(), list)
    assert "LOW" in client.get("/v1/ap/decisions", headers=h).json()
    pdf = ROOT / "demo_invoices" / "invoice_good.pdf"
    with pdf.open("rb") as f:
        up = client.post("/v1/ap/invoices/upload", headers=h, files={"file": ("invoice_good.pdf", f, "application/pdf")})
    assert up.status_code == 200, up.text
    data = up.json()
    assert "jobId" in data and data["status"] == "processing"
    job = client.get(f"/v1/ap/invoices/jobs/{data['jobId']}", headers=h)
    assert job.status_code == 200
    print("OK ap")


def test_cfo():
    login = client.post("/v1/auth/login", json={"code": "CFO2024"}).json()
    h = {"Authorization": f"Bearer {login['token']}"}
    stats = client.get("/v1/cfo/stats", headers=h).json()
    assert "totalProcessed" in stats
    audit = client.get("/v1/cfo/audit-log", headers=h).json()
    assert "entries" in audit and "pages" in audit
    exp = client.get("/v1/cfo/audit-log/export", headers=h)
    assert exp.status_code == 200
    assert "text/csv" in exp.headers.get("content-type", "")
    print("OK cfo")


if __name__ == "__main__":
    test_auth()
    test_ap()
    test_cfo()
    print("\n=== ALL CHECKS PASSED ===")
