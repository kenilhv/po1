"""PO1 — money in (Stripe) and money out (vendor payouts).

Two directions, deliberately separated:

  INBOUND  — PO1's own revenue. A startup subscribes ($299/mo) instead of
             making a finance hire, and pays a metered fee ($15) for each
             human judgment it actually consumes. This is what the hackathon
             tracks via the submitted Payment Link + restricted read key.

  OUTBOUND — paying the customer's vendors once an invoice clears. Recorded
             and reconciled here; the actual disbursement rail is out of scope
             for a one-day build (and Stripe Payment Links only collect).
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import requests

from crew.tools.ap_tools import record_payment, record_revenue

STRIPE_API = "https://api.stripe.com/v1"
STRIPE_KEY = os.getenv("STRIPE_RESTRICTED_KEY", "")  # rk_test_... read-only
PAYMENT_LINK = os.getenv("STRIPE_PAYMENT_LINK", "")

SUBSCRIPTION_PRICE = float(os.getenv("PO1_SUBSCRIPTION_PRICE", "299"))
ESCALATION_FEE = float(os.getenv("PO1_ESCALATION_FEE", "1"))


def is_configured() -> bool:
    return bool(PAYMENT_LINK)


# ------------------------------------------------------------------ inbound

def subscription_checkout(customer_ref: str) -> dict[str, Any]:
    """The agent's own sale: hand a prospective customer the payment link."""
    record_revenue("subscription_offered", SUBSCRIPTION_PRICE, customer_ref)
    return {
        "url": PAYMENT_LINK,
        "amount": SUBSCRIPTION_PRICE,
        "kind": "subscription",
        "message": (
            f"PO1 runs your accounts payable for ${SUBSCRIPTION_PRICE:.0f}/month — "
            f"a fraction of a fractional CFO, and it only bills for human judgment "
            f"when it actually needs it (${ESCALATION_FEE:.0f} per escalation)."
        ),
    }


def escalation_charge(customer_ref: str, invoice_id: int, exception_type: str) -> dict[str, Any]:
    """Metered fee — the customer pays only for judgment actually consumed."""
    record_revenue("escalation_fee", ESCALATION_FEE, customer_ref)
    return {
        "url": PAYMENT_LINK,
        "amount": ESCALATION_FEE,
        "kind": "escalation_fee",
        "invoice_id": invoice_id,
        "message": (
            f"${ESCALATION_FEE:.0f} — verified human review of a "
            f"{exception_type.replace('_', ' ')} on invoice #{invoice_id}."
        ),
    }


def fetch_charges(limit: int = 25) -> dict[str, Any]:
    """Read real Stripe activity with the restricted key (Balance+Charges: Read)."""
    if not STRIPE_KEY:
        return {"configured": False, "charges": [], "total": 0.0}
    try:
        resp = requests.get(
            f"{STRIPE_API}/charges",
            headers={"Authorization": f"Bearer {STRIPE_KEY}"},
            params={"limit": limit},
            timeout=20,
        )
        if resp.status_code >= 400:
            return {"configured": True, "error": resp.text[:200], "charges": [], "total": 0.0}
        data = resp.json().get("data", [])
        charges = [
            {
                "id": c["id"],
                "amount": c["amount"] / 100,
                "status": c["status"],
                "created": datetime.utcfromtimestamp(c["created"]).isoformat(),
                "paid": c.get("paid", False),
            }
            for c in data
        ]
        return {
            "configured": True,
            "charges": charges,
            "total": sum(c["amount"] for c in charges if c["paid"]),
        }
    except requests.RequestException as exc:
        return {"configured": True, "error": str(exc)[:200], "charges": [], "total": 0.0}


# ----------------------------------------------------------------- outbound

def pay_vendor(
    invoice_id: int,
    vendor_name: str,
    invoice_number: str,
    amount: float,
    payment_run_id: int | None = None,
) -> dict[str, Any]:
    """Disburse to a vendor once the invoice has cleared every control."""
    ref = f"po1_{invoice_id}_{int(datetime.utcnow().timestamp())}"
    record_payment(
        invoice_id=invoice_id,
        vendor_name=vendor_name,
        invoice_number=invoice_number,
        amount=amount,
        provider="po1_disbursement",
        provider_ref=ref,
        payment_run_id=payment_run_id,
    )
    return {
        "paid": True,
        "reference": ref,
        "amount": amount,
        "vendor": vendor_name,
        "paid_at": datetime.utcnow().isoformat(),
    }
