"""
InvoiceOS MCP server — Aditya registers in TrueFoundry MCP Gateway.

Run:  python -m invoice_mcp.server --port 8001
SSE:  http://<KENIL_IP>:8001/sse
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from crew.tools.po_tool import lookup_duplicate, lookup_po, lookup_vendor

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    raise SystemExit("pip install mcp")

mcp = FastMCP("invoice-os-mcp", host="0.0.0.0")


@mcp.tool()
def lookup_purchase_order(vendor_name: str, po_reference: str = "") -> str:
    """Look up purchase order by vendor and optional PO number."""
    return json.dumps(lookup_po(vendor_name, po_reference or None))


@mcp.tool()
def check_duplicate_payment(vendor_name: str, amount: float, invoice_number: str) -> str:
    """Check if invoice was already paid (duplicate detection)."""
    return json.dumps(lookup_duplicate(vendor_name, amount, invoice_number))


@mcp.tool()
def check_vendor_fraud_signals(vendor_name: str, bank_details: str = "") -> str:
    """Check vendor registry and bank account for fraud signals."""
    return json.dumps(lookup_vendor(vendor_name, bank_details or None))


@mcp.tool()
def submit_payment(invoice_id: int, amount: float, vendor_name: str) -> str:
    """Submit AP payment — L3. Aditya: BLOCK without human approval token."""
    return json.dumps(
        {
            "status": "blocked_pending_approval",
            "message": "Payment requires CFO approval via TrueFoundry MCP policy",
            "invoice_id": invoice_id,
            "amount": amount,
            "vendor": vendor_name,
        }
    )


@mcp.tool()
def write_audit_log(invoice_id: int, agent_name: str, message: str) -> str:
    """Write audit log entry (approval_router only)."""
    from database.db import get_conn

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO audit_log (invoice_id, agent_name, input_summary, output_summary)
            VALUES (?, ?, 'mcp', ?)
            """,
            (invoice_id, agent_name, message),
        )
        conn.commit()
    return json.dumps({"ok": True})


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8001)
    args = p.parse_args()
    mcp.settings.port = args.port
    mcp.run(transport="sse")
