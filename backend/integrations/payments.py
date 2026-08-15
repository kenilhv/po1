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
SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")      # sk_test_... can create
PAYMENT_LINK = os.getenv("STRIPE_PAYMENT_LINK", "")  # static fallback

SUBSCRIPTION_PRICE = float(os.getenv("PO1_SUBSCRIPTION_PRICE", "299"))
ESCALATION_FEE = float(os.getenv("PO1_ESCALATION_FEE", "1"))


def is_configured() -> bool:
    return bool(PAYMENT_LINK or SECRET_KEY)


def can_create_links() -> bool:
    """Whether the agent can mint its own checkout, rather than reusing one link."""
    return bool(SECRET_KEY)


def create_payment_link(amount: float, description: str) -> dict[str, Any]:
    """Mint a Stripe Payment Link for one specific charge.

    A single fixed link cannot represent both a $299 subscription and a $1
    metered fee, so the agent creates the exact charge it decided on. Falls
    back to the static link when no secret key is configured.
    """
    if not SECRET_KEY:
        return {"url": PAYMENT_LINK, "amount": amount, "dynamic": False}

    auth = {"Authorization": f"Bearer {SECRET_KEY}"}
    try:
        price = requests.post(
            f"{STRIPE_API}/prices",
            headers=auth,
            data={
                "unit_amount": int(round(amount * 100)),
                "currency": "usd",
                "product_data[name]": description[:250],
            },
            timeout=25,
        )
        if price.status_code >= 400:
            return {"url": PAYMENT_LINK, "amount": amount, "dynamic": False,
                    "error": price.text[:200]}

        link = requests.post(
            f"{STRIPE_API}/payment_links",
            headers=auth,
            data={
                "line_items[0][price]": price.json()["id"],
                "line_items[0][quantity]": 1,
            },
            timeout=25,
        )
        if link.status_code >= 400:
            return {"url": PAYMENT_LINK, "amount": amount, "dynamic": False,
                    "error": link.text[:200]}

        return {"url": link.json()["url"], "amount": amount, "dynamic": True,
                "link_id": link.json()["id"]}
    except requests.RequestException as exc:
        return {"url": PAYMENT_LINK, "amount": amount, "dynamic": False,
                "error": str(exc)[:200]}


# ------------------------------------------------------------------ inbound

def subscription_checkout(customer_ref: str) -> dict[str, Any]:
    """The agent's own sale: mint a checkout for the monthly subscription."""
    record_revenue("subscription_offered", SUBSCRIPTION_PRICE, customer_ref)
    link = create_payment_link(SUBSCRIPTION_PRICE, "PO1 — autonomous accounts payable, monthly")
    return {
        "url": link["url"],
        "dynamic": link.get("dynamic", False),
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
    link = create_payment_link(
        ESCALATION_FEE,
        f"PO1 — expert review of a {exception_type.replace('_', ' ')} on invoice #{invoice_id}",
    )
    return {
        "url": link["url"],
        "dynamic": link.get("dynamic", False),
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
