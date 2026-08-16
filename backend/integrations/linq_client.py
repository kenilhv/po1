"""PO1 — Linq messaging.

Three flows, all grounded in documents AP departments genuinely send:

  REMITTANCE ADVICE  — the standard notice a payer sends after paying, so the
                       vendor can reconcile it. Rendered as an iMessage App
                       card whose state flips Pending -> Paid in the thread.

  VENDOR QUERY       — on a price variance, PO1 texts the vendor to confirm the
                       amount before disputing. Their tapback is the answer:
                       thumbs-up confirms, thumbs-down disputes. Messaging
                       primitives as UI, per Linq's own guidance.

  FOUNDER ALERT      — when PO1 blocks a payment, the customer hears why on
                       their phone within seconds, not in a dashboard later.
"""

from __future__ import annotations

import os
from typing import Any

import requests

BASE_URL = os.getenv("LINQ_BASE_URL", "https://api.linqapp.com/api/partner/v3")
API_KEY = os.getenv("LINQ_API_KEY", "")
FROM_NUMBER = os.getenv("LINQ_PHONE_NUMBER", "")
FOUNDER_NUMBER = os.getenv("FOUNDER_PHONE", "")
TIMEOUT = 20

_sent: list[dict[str, Any]] = []  # demo transcript when Linq isn't reachable


def is_configured() -> bool:
    return bool(API_KEY and FROM_NUMBER)


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def _send(to: str, text: str, card: dict[str, Any] | None = None) -> dict[str, Any]:
    entry = {"to": to, "text": text, "card": card}
    _sent.append(entry)

    if not is_configured() or not to:
        return {"sent": False, "reason": "not_configured", **entry}

    def _post(parts: list[dict[str, Any]]):
        return requests.post(
            f"{BASE_URL}/chats",
            headers=_headers(),
            json={"from": FROM_NUMBER, "to": [to], "message": {"parts": parts}},
            timeout=TIMEOUT,
        )

    try:
        resp = _post([{"type": "text", "value": text}])
        ok = resp.status_code < 400
        entry["status"] = resp.status_code
        if not ok:
            # Sandbox is inbound-first: the recipient must text the Linq number
            # before an agent may message them.
            entry["error"] = resp.text[:200]

        # An imessage_app part must be the only part in its message, so the
        # interactive card goes out as a second message right after the text.
        if ok and card:
            try:
                _post([{"type": "imessage_app", "value": card}])
            except requests.RequestException:
                pass

        return {"sent": ok, **entry}
    except requests.RequestException as exc:
        return {"sent": False, "error": str(exc)[:200], **entry}


def send_remittance(
    vendor_phone: str,
    vendor_name: str,
    invoice_number: str,
    amount: float,
    paid_at: str,
    reference: str,
    discount_captured: float = 0.0,
) -> dict[str, Any]:
    """Remittance advice — the real post-payment document, as a live card."""
    lines = [
        f"Payment sent to {vendor_name}",
        f"Invoice {invoice_number}",
        f"Amount ${amount:,.2f}",
    ]
    if discount_captured:
        lines.append(f"Early-payment discount applied: -${discount_captured:,.2f}")
    lines.append(f"Reference {reference}")

    return _send(
        vendor_phone,
        "\n".join(lines),
        card={
            "type": "remittance",
            "title": f"Invoice {invoice_number}",
            "status": "Paid",
            "subtitle": f"${amount:,.2f} · {paid_at[:10]}",
            "fields": [
                {"label": "Vendor", "value": vendor_name},
                {"label": "Amount", "value": f"${amount:,.2f}"},
                {"label": "Reference", "value": reference},
            ],
        },
    )


def query_vendor_variance(
    vendor_phone: str,
    vendor_name: str,
    invoice_number: str,
    billed: float,
    expected: float,
) -> dict[str, Any]:
    """Ask the vendor to confirm a variance. Their tapback is the vote."""
    delta = billed - expected
    return _send(
        vendor_phone,
        (
            f"Hi {vendor_name} — invoice {invoice_number} bills ${billed:,.2f}, "
            f"but the PO we have is ${expected:,.2f} ({delta:+,.2f}). "
            f"👍 to confirm the invoice is correct, 👎 if it needs a revision."
        ),
        card={
            "type": "variance_query",
            "title": f"Invoice {invoice_number}",
            "status": "Awaiting confirmation",
            "subtitle": f"Billed ${billed:,.2f} vs PO ${expected:,.2f}",
            "actions": [
                {"label": "Confirm amount", "value": "confirm"},
                {"label": "Needs revision", "value": "dispute"},
            ],
        },
    )


def alert_founder(
    invoice_id: int,
    vendor_name: str,
    amount: float,
    exception_type: str,
    reasoning: str,
    phone: str | None = None,
) -> dict[str, Any]:
    """Tell the customer why PO1 stopped, the moment it stops."""
    return _send(
        phone or FOUNDER_NUMBER,
        (
            f"PO1 held ${amount:,.2f} to {vendor_name}\n"
            f"Reason: {exception_type.replace('_', ' ')}\n"
            f"{reasoning}\n"
            f"Invoice #{invoice_id} — reviewing now."
        ),
        card={
            "type": "exception_alert",
            "title": f"Payment held — {vendor_name}",
            "status": exception_type.replace("_", " ").title(),
            "subtitle": f"${amount:,.2f}",
        },
    )


def notify_resolution(
    invoice_id: int,
    vendor_name: str,
    amount: float,
    verdict: str,
    reasoning: str,
    phone: str | None = None,
) -> dict[str, Any]:
    """Close the loop after a human reviewer rules."""
    return _send(
        phone or FOUNDER_NUMBER,
        (
            f"Invoice #{invoice_id} ({vendor_name}, ${amount:,.2f}) resolved: {verdict}\n"
            f"{reasoning}"
        ),
        card={
            "type": "resolution",
            "title": f"Invoice #{invoice_id} — {verdict}",
            "status": verdict,
            "subtitle": f"{vendor_name} · ${amount:,.2f}",
        },
    )


def record_inbound(frm: str, text: str) -> None:
    """A vendor's reply, threaded into the same wires feed as outbound."""
    _sent.append({"to": frm, "text": text, "card": None, "direction": "in"})


def transcript() -> list[dict[str, Any]]:
    """Everything PO1 texted today — drives the demo's messaging panel."""
    return list(_sent)
