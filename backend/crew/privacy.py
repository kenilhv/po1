"""PO1 — pseudonymization for anything a human outside the company sees.

Terac reviewers are strangers on the internet. They need enough of an invoice
to make a real judgment, and none of the company's actual commercial data.

The naive approach — hashing names into gibberish — protects the data but
destroys the task: nobody can reason about whether "a7f3c9" looks trustworthy.
So this module does what data vendors actually do:

  * Vendor names map to a STABLE fake name. The same real vendor always becomes
    the same alias, so "we've paid them 20 times before" still reads true, and
    a reviewer comparing two invoices from one supplier sees one supplier.
  * Amounts are scaled by a single per-company factor, not randomised. A 54%
    overbill stays a 54% overbill; ratios, variances and discount maths all
    survive, while the real figures never leave.
  * Bank accounts, tax IDs and invoice numbers are dropped entirely. A reviewer
    judging "should this be paid" never needs them, so they are not sent.

The mapping lives only in this process, so the reviewer's answer can be applied
back to the real invoice while the reviewer never holds anything real.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any

# Scaling factor for money. Stable per deployment so every invoice a reviewer
# sees is on the same scale as every other.
_SCALE = float(os.getenv("PO1_AMOUNT_SCALE", "0.83"))

# Plausible business names. Picked deterministically, so one real vendor always
# maps to one alias for the lifetime of the salt.
_ALIASES = [
    "Northgate Supply", "Bellweather Trading", "Kestrel Logistics", "Ironwood Partners",
    "Marlow & Finch", "Cedarline Services", "Halcyon Systems", "Foxglove Industrial",
    "Redstone Provisioning", "Quillon Group", "Ashford Materials", "Verity Works",
    "Brightmoor Freight", "Copperfield Labs", "Sablewood Contracting", "Thornbury Tech",
]

_SALT = os.getenv("PO1_PSEUDONYM_SALT", "po1-default-salt")

# Reverse map so a reviewer's verdict can be applied to the real invoice.
_alias_to_real: dict[str, str] = {}


def alias_for(vendor_name: str) -> str:
    """Stable pseudonym for a vendor. Same input always yields the same alias."""
    if not vendor_name:
        return "Unnamed Vendor"
    digest = hashlib.sha256(f"{_SALT}:{vendor_name}".encode()).hexdigest()
    alias = _ALIASES[int(digest[:8], 16) % len(_ALIASES)]
    # Disambiguate collisions with a short stable suffix.
    if _alias_to_real.get(alias, vendor_name) != vendor_name:
        alias = f"{alias} ({digest[:3].upper()})"
    _alias_to_real[alias] = vendor_name
    return alias


def real_vendor(alias: str) -> str | None:
    """Resolve an alias back to the real vendor, for applying a verdict."""
    return _alias_to_real.get(alias)


def scale_amount(amount: float | None) -> float:
    """Scale money by a fixed factor so ratios and variances stay truthful."""
    return round(float(amount or 0) * _SCALE, 2)


def redact_invoice(invoice: dict[str, Any], exception: dict[str, Any] | None = None) -> dict[str, Any]:
    """The version of an invoice safe to show an outside reviewer.

    Keeps everything needed to judge "should this be paid" — the vendor's
    identity as a consistent alias, proportionally accurate amounts, whether a
    PO and goods receipt exist, and what was flagged. Drops bank details, tax
    IDs and real invoice numbers, which a reviewer never needs.
    """
    amount = scale_amount(invoice.get("amount"))
    po_amount = scale_amount(invoice.get("po_amount")) if invoice.get("po_amount") else None

    safe: dict[str, Any] = {
        "vendor": alias_for(str(invoice.get("vendor_name") or "")),
        "amount": amount,
        "has_purchase_order": bool(invoice.get("po_reference")),
        "po_amount": po_amount,
        "category": invoice.get("cost_center") or "General",
        "reference": f"REF-{abs(hash(str(invoice.get('id')))) % 9000 + 1000}",
    }

    if exception:
        etype = exception.get("exception_type") or ""
        safe["flagged_as"] = etype.replace("_", " ")
        # Describe the concern without leaking the underlying figures.
        safe["concern"] = _describe(etype, invoice, exception)

    return safe


def _describe(etype: str, invoice: dict[str, Any], exception: dict[str, Any]) -> str:
    """Plain-language reason, scaled and stripped of identifying detail."""
    ev = exception.get("evidence") or {}

    if etype == "price_variance":
        pct = ev.get("pct")
        return (
            f"The bill is {abs(pct):.0f}% {'higher' if (pct or 0) > 0 else 'lower'} than "
            f"the amount that was originally agreed."
            if pct is not None
            else "The bill does not match the amount originally agreed."
        )
    if etype == "vendor_bank_change":
        return (
            "This supplier has been paid before, but the bank account on this "
            "invoice is different from the one used previously."
        )
    if etype == "unknown_vendor":
        return "There are no tax records on file for this supplier."
    if etype == "missing_po":
        return "Nobody authorised this purchase in advance."
    if etype == "missing_receipt":
        return "There is no record confirming the goods or services actually arrived."
    if etype == "duplicate":
        return "An invoice with this reference appears to have been paid already."
    if etype == "quantity_mismatch":
        return "The bill is for more than what was recorded as delivered."
    return exception.get("detail") or "Something about this invoice needs a second opinion."


def redaction_summary() -> dict[str, Any]:
    """What the reviewer never saw — shown on the dashboard as a real control."""
    return {
        "vendors_pseudonymised": len(_alias_to_real),
        "amount_scaling": "proportional (ratios preserved)",
        "fields_withheld": ["bank_account", "tax_id", "invoice_number", "real_vendor_name"],
    }
