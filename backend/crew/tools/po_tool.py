from __future__ import annotations

from database.db import get_conn


def lookup_po(vendor_name: str, po_reference: str | None) -> dict:
    po_ref = (po_reference or "").strip()
    with get_conn() as conn:
        if po_ref:
            row = conn.execute(
                "SELECT * FROM purchase_orders WHERE po_number = ? AND vendor_name = ?",
                (po_ref, vendor_name),
            ).fetchone()
            if row:
                return {"match": True, "po_number": row["po_number"], "amount": row["amount"]}
            return {"match": False, "detail": f"PO {po_ref} not found for vendor {vendor_name}"}
        if vendor_name:
            row = conn.execute(
                "SELECT * FROM purchase_orders WHERE vendor_name = ?",
                (vendor_name,),
            ).fetchone()
            if row:
                return {"match": True, "po_number": row["po_number"], "amount": row["amount"]}
    return {"match": False, "detail": "No PO found"}


def lookup_duplicate(vendor_name: str, amount: float, invoice_number: str) -> dict:
    """Detect a re-submitted invoice.

    Matching on amount alone produces false positives — recurring vendors bill
    identical amounts every month by design. Only a repeated *invoice number*
    is conclusive; a matching amount is a soft signal that informs severity
    without blocking payment on its own.
    """
    with get_conn() as conn:
        if invoice_number:
            exact = conn.execute(
                "SELECT invoice_number, vendor_name, amount FROM payments "
                "WHERE vendor_name = ? AND invoice_number = ?",
                (vendor_name, invoice_number),
            ).fetchone()
            if exact:
                return {
                    "duplicate": True,
                    "confidence": "exact",
                    "matches": [dict(exact)],
                    "detail": f"Invoice {invoice_number} was already paid to {vendor_name}",
                }

        similar = conn.execute(
            """
            SELECT invoice_number, vendor_name, amount FROM payments
            WHERE vendor_name = ? AND ABS(amount - ?) < 1
            """,
            (vendor_name, amount),
        ).fetchall()

    if similar:
        return {
            "duplicate": False,
            "similar_amount": True,
            "matches": [dict(r) for r in similar],
            "detail": (
                f"${amount:,.2f} matches {len(similar)} prior payment(s) to {vendor_name}, "
                "but under a different invoice number — likely a recurring charge"
            ),
        }
    return {"duplicate": False, "detail": "No prior payment matches this invoice"}


def lookup_vendor(vendor_name: str, bank_details: str | None) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM vendors WHERE vendor_name = ?",
            (vendor_name,),
        ).fetchone()
        if not row:
            return {"known": False, "flagged": True, "signals": ["Unknown vendor"]}
        signals = []
        if row["flagged"]:
            signals.append("Vendor flagged in registry")
        if bank_details and bank_details.strip():
            expected = (row["bank_account"] or "").strip()
            provided = bank_details.strip()
            if expected and expected not in provided and provided not in expected:
                signals.append("Bank account mismatch")
        return {
            "known": bool(row["known"]),
            "flagged": bool(row["flagged"]),
            "expected_bank": row["bank_account"],
            "signals": signals,
        }
