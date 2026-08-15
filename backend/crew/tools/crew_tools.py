from __future__ import annotations

import json

from crewai.tools import tool

from crew.tools.po_tool import lookup_duplicate, lookup_po, lookup_vendor


@tool("lookup_purchase_order")
def lookup_purchase_order(vendor_name: str, po_reference: str = "") -> str:
    """Look up a purchase order by vendor name and optional PO number."""
    result = lookup_po(vendor_name, po_reference or None)
    return json.dumps(result)


@tool("check_duplicate_payment")
def check_duplicate_payment(vendor_name: str, amount: float, invoice_number: str) -> str:
    """Check payment history for duplicate invoices."""
    result = lookup_duplicate(vendor_name, amount, invoice_number)
    return json.dumps(result)


@tool("check_vendor_fraud_signals")
def check_vendor_fraud_signals(vendor_name: str, bank_details: str = "") -> str:
    """Check vendor registry and bank account for fraud signals."""
    result = lookup_vendor(vendor_name, bank_details or None)
    return json.dumps(result)
