"""PO1 — deterministic AP logic grounded in how real AP departments operate.

Real-world sourcing for these rules:
  * 3-way match (PO + goods receipt + invoice) is the standard control that
    prevents overpayment and payment for goods never received.
  * Vendor banking-detail *changes* are the highest-signal real fraud vector,
    far more than a novel-looking invoice.
  * Real AP classifies the *type* of exception first (each type has a named
    owner and an SLA); severity scoring comes after, not instead.
  * Payment is a scheduled batch decision that weighs early-payment discount
    terms (2/10 net 30 annualizes to ~36.7%), not an instant reflex.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

# ---------------------------------------------------------------- exceptions

EXCEPTION_TYPES = frozenset(
    {
        "clean",
        "price_variance",
        "quantity_mismatch",
        "missing_receipt",
        "missing_po",
        "duplicate",
        "vendor_bank_change",
        "unknown_vendor",
        "budget_violation",
    }
)

# Who owns resolution for each exception type, mirroring a real AP exception policy.
EXCEPTION_OWNERS: dict[str, str] = {
    "price_variance": "buyer",           # buyer updates the PO or vendor issues credit
    "quantity_mismatch": "receiving",    # receiving confirms what actually arrived
    "missing_receipt": "receiving",      # goods not yet logged
    "missing_po": "buyer",               # unauthorized spend — buyer must back it
    "duplicate": "ap",                   # AP voids the second invoice
    "vendor_bank_change": "controller",  # never self-approve a banking change
    "unknown_vendor": "ap",              # vendor onboarding incomplete
    "budget_violation": "controller",
    "clean": "none",
}

# Tolerances before a variance is treated as an exception at all.
PRICE_TOLERANCE_PCT = 0.02   # 2% price drift is normal (freight, rounding, FX)
PRICE_TOLERANCE_ABS = 25.0   # ...or $25, whichever is greater
QTY_TOLERANCE_PCT = 0.01


def three_way_match(
    invoice_amount: float,
    po: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    """Compare invoice against BOTH the purchase order and the goods receipt.

    Returns a structured verdict rather than a boolean, because *which* leg
    fails determines who has to fix it.
    """
    result: dict[str, Any] = {
        "po_match": bool(po.get("match")),
        "receipt_match": False,
        "price_variance": None,
        "quantity_variance": None,
        "legs_matched": 0,
    }

    if not po.get("match"):
        result["detail"] = po.get("detail", "No purchase order on file")
        return result

    result["legs_matched"] = 1
    po_amount = float(po.get("amount") or 0)

    # Leg 2: invoice price vs. PO price
    if po_amount > 0:
        delta = invoice_amount - po_amount
        tolerance = max(po_amount * PRICE_TOLERANCE_PCT, PRICE_TOLERANCE_ABS)
        if abs(delta) > tolerance:
            result["price_variance"] = {
                "po_amount": po_amount,
                "invoice_amount": invoice_amount,
                "delta": round(delta, 2),
                "pct": round((delta / po_amount) * 100, 2),
            }
        else:
            result["legs_matched"] = 2

    # Leg 3: was it actually received?
    if not receipt or not receipt.get("found"):
        result["detail"] = "No goods receipt — cannot confirm delivery"
        return result

    result["receipt_match"] = True
    received_amount = float(receipt.get("amount_received") or 0)
    if received_amount > 0 and po_amount > 0:
        qty_delta = invoice_amount - received_amount
        if abs(qty_delta) > max(received_amount * QTY_TOLERANCE_PCT, PRICE_TOLERANCE_ABS):
            result["quantity_variance"] = {
                "received": received_amount,
                "billed": invoice_amount,
                "delta": round(qty_delta, 2),
            }
        else:
            result["legs_matched"] = 3

    result["detail"] = f"{result['legs_matched']}/3 legs matched"
    return result


def classify_exception(evidence: dict[str, Any]) -> dict[str, Any]:
    """Turn raw agent signals into ONE typed exception with a named owner.

    This is the structural difference from a generic risk score: real AP names
    the problem first, because the problem type determines who resolves it.
    Ordered by precedence — a banking change outranks a price variance.
    """
    match = evidence.get("match") or {}
    dup = evidence.get("duplicate") or {}
    fraud = evidence.get("fraud") or {}
    vendor = evidence.get("vendor_status") or {}
    amount = float(evidence.get("amount") or 0)
    budget = evidence.get("budget") or {}

    def _mk(etype: str, detail: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "exception_type": etype,
            "owner": EXCEPTION_OWNERS.get(etype, "ap"),
            "detail": detail,
            "evidence": extra or {},
        }

    # 1. Banking change on a known vendor — highest precedence, never auto-clear.
    if vendor.get("bank_details_changed"):
        return _mk(
            "vendor_bank_change",
            "Vendor's bank details changed since last payment — verify out-of-band before paying",
            {
                "previous": vendor.get("previous_bank_account"),
                "current": vendor.get("current_bank_account"),
            },
        )

    # 2. Vendor never properly onboarded. Being *in* the table isn't enough —
    #    without a tax ID on file there's no W-9, so the payment isn't
    #    1099-reportable and shouldn't go out.
    if vendor.get("is_new") or not vendor.get("known", True):
        return _mk("unknown_vendor", "Vendor not in master file — onboarding incomplete")
    if not vendor.get("has_tax_id", True):
        return _mk(
            "unknown_vendor",
            "Vendor has no tax ID on file — W-9 missing, payment is not 1099-reportable",
        )

    # 3. Already paid.
    if dup.get("duplicate"):
        return _mk("duplicate", dup.get("detail", "Duplicate of an already-paid invoice"), dup)

    # 4. Fraud signals from the model / registry.
    if fraud.get("flagged"):
        signals = fraud.get("signals") or ["Vendor flagged in registry"]
        return _mk("vendor_bank_change" if any("bank" in s.lower() for s in signals) else "unknown_vendor",
                   "; ".join(signals), {"signals": signals})

    # 5. Spend with no authorizing PO.
    if not match.get("po_match"):
        return _mk("missing_po", match.get("detail", "No purchase order authorizes this spend"))

    # 6. Billed more than the PO agreed.
    if match.get("price_variance"):
        pv = match["price_variance"]
        return _mk(
            "price_variance",
            f"Billed ${pv['invoice_amount']:,.2f} against a ${pv['po_amount']:,.2f} PO ({pv['pct']:+.1f}%)",
            pv,
        )

    # 7. Nothing confirms delivery.
    if not match.get("receipt_match"):
        return _mk("missing_receipt", "No goods receipt — delivery unconfirmed")

    # 8. Billed more than was received.
    if match.get("quantity_variance"):
        qv = match["quantity_variance"]
        return _mk(
            "quantity_mismatch",
            f"Billed ${qv['billed']:,.2f} but only ${qv['received']:,.2f} was received",
            qv,
        )

    # 9. Over budget for the coded cost center.
    if budget.get("exceeded"):
        return _mk("budget_violation", budget.get("detail", "Exceeds cost-center budget"), budget)

    return _mk("clean", f"3/3 match, known vendor, no duplicates — ${amount:,.2f} clear to pay")


# ------------------------------------------------------------------ severity

def score_severity(
    exception_type: str,
    amount: float,
    vendor_trust: float = 0.5,
    variance_pct: float | None = None,
) -> tuple[str, str]:
    """Severity of a *typed* exception, weighted by amount and vendor history.

    Distinct from classification: the same exception type is more severe on a
    $50k invoice from a new vendor than a $200 one from a 3-year supplier.

    Magnitude outranks reputation. A trusted vendor billing 50% over their own
    PO is a bigger problem than a new vendor billing exactly what was agreed —
    so a large variance floors the severity regardless of trust.
    """
    if exception_type == "clean":
        return "LOW", "No exception"

    base = {
        "vendor_bank_change": 4,
        "duplicate": 3,
        "unknown_vendor": 3,
        "quantity_mismatch": 2,
        "missing_po": 2,
        "price_variance": 2,
        "budget_violation": 2,
        "missing_receipt": 1,
    }.get(exception_type, 2)

    if amount >= 25_000:
        base += 2
    elif amount >= 10_000:
        base += 1
    elif amount < 500:
        base -= 1

    if vendor_trust < 0.3:
        base += 1
    elif vendor_trust > 0.8:
        base -= 1

    # Variance magnitude escalates on its own terms.
    magnitude = abs(variance_pct or 0)
    if magnitude >= 25:
        base = max(base + 2, 3)
    elif magnitude >= 10:
        base = max(base + 1, 3)

    tier = "LOW" if base <= 1 else "MEDIUM" if base == 2 else "HIGH" if base <= 4 else "CRITICAL"
    detail = f"{exception_type} on ${amount:,.2f} (vendor trust {vendor_trust:.0%}"
    detail += f", {magnitude:.0f}% variance)" if magnitude else ")"
    return tier, detail


# ------------------------------------------------------- delegation of authority

def route_decision(
    severity: str,
    amount: float,
    exception_type: str,
    thresholds: dict[str, float] | None = None,
) -> tuple[str, str]:
    """Amount-tiered delegation of authority, the way a real approval matrix works.

    Returns one of:
      AUTO_APPROVED   — agent clears it alone
      PENDING_FOUNDER — customer's own sign-off (cheap, low-stakes judgment)
      PENDING_TERAC   — hire a verified human reviewer through Terac
      BLOCKED         — never auto-pay; requires out-of-band verification
    """
    t = thresholds or {"auto": 2_000.0, "founder": 10_000.0}

    # A banking change is never resolvable by scoring — it needs a human, always.
    if exception_type == "vendor_bank_change":
        return "BLOCKED", "Banking change requires out-of-band verification before any payment"

    if severity == "CRITICAL":
        return "PENDING_TERAC", f"Critical {exception_type} — routing to a verified reviewer"

    if exception_type == "clean":
        if amount <= t["auto"]:
            return "AUTO_APPROVED", f"Clean 3-way match under ${t['auto']:,.0f} — cleared automatically"
        if amount <= t["founder"]:
            return "PENDING_FOUNDER", f"Clean, but ${amount:,.2f} exceeds the auto-approve limit"
        return "PENDING_TERAC", f"Clean, but ${amount:,.2f} exceeds founder authority"

    if severity == "LOW" and amount <= t["auto"]:
        return "AUTO_APPROVED", f"Minor {exception_type} within tolerance on a small amount"

    if severity in ("LOW", "MEDIUM") and amount <= t["founder"]:
        return "PENDING_FOUNDER", f"{exception_type} — founder can resolve this directly"

    return "PENDING_TERAC", f"{exception_type} at ${amount:,.2f} — needs verified expert judgment"


# ----------------------------------------------------------------- GL coding

# Minimal chart of accounts. Real systems learn this per-org; rules are enough today.
GL_RULES: list[tuple[str, str, str, str]] = [
    (r"aws|amazon web|gcp|google cloud|azure|render|vercel|heroku", "6100", "Cloud Infrastructure", "Engineering"),
    (r"software|saas|license|subscription|github|slack|notion|figma", "6110", "Software & Subscriptions", "Engineering"),
    (r"consult|advisory|contractor|freelance|agency", "6200", "Professional Services", "Operations"),
    (r"legal|attorney|law firm|counsel", "6210", "Legal Fees", "G&A"),
    (r"account|bookkeep|audit|tax prep|cpa", "6220", "Accounting Fees", "G&A"),
    (r"office|supply|supplies|paper|furniture|desk", "6300", "Office Supplies", "G&A"),
    (r"travel|flight|hotel|airfare|uber|lyft", "6400", "Travel & Entertainment", "G&A"),
    (r"marketing|advertis|ads|campaign|seo", "6500", "Marketing & Advertising", "Marketing"),
    (r"recruit|staffing|hiring|talent", "6600", "Recruiting", "People"),
    (r"insurance|premium|coverage", "6700", "Insurance", "G&A"),
    (r"rent|lease|workspace|coworking", "6800", "Rent & Facilities", "G&A"),
]

DEFAULT_GL = ("6900", "General Operating Expense", "G&A")


def assign_gl_code(vendor_name: str, line_items: str | None = None) -> dict[str, str]:
    """Assign a GL account and cost center. Nothing can check spend against a
    budget or policy until this step exists — it's not optional bookkeeping."""
    haystack = f"{vendor_name} {line_items or ''}".lower()
    for pattern, code, label, cost_center in GL_RULES:
        if re.search(pattern, haystack):
            return {"gl_code": code, "gl_label": label, "cost_center": cost_center}
    code, label, cost_center = DEFAULT_GL
    return {"gl_code": code, "gl_label": label, "cost_center": cost_center}


# ------------------------------------------------------- payment scheduling

_DISCOUNT_RE = re.compile(r"(\d+)\s*/\s*(\d+)\s*(?:net|n)\s*(\d+)", re.IGNORECASE)


def parse_payment_terms(terms: str | None) -> dict[str, Any]:
    """Parse terms like '2/10 net 30' — 2% off if paid within 10 days, else due in 30."""
    if not terms:
        return {"discount_pct": 0.0, "discount_days": 0, "net_days": 30, "raw": None}
    m = _DISCOUNT_RE.search(terms)
    if m:
        return {
            "discount_pct": float(m.group(1)) / 100,
            "discount_days": int(m.group(2)),
            "net_days": int(m.group(3)),
            "raw": terms,
        }
    net = re.search(r"net\s*(\d+)", terms, re.IGNORECASE)
    return {
        "discount_pct": 0.0,
        "discount_days": 0,
        "net_days": int(net.group(1)) if net else 30,
        "raw": terms,
    }


def schedule_payment(
    amount: float,
    terms: str | None,
    invoice_date: str | None = None,
    today: datetime | None = None,
) -> dict[str, Any]:
    """Decide *when* to pay — the step between 'approved' and 'paid'.

    Capturing 2/10 net 30 is ~36.7% annualized, so an early discount is almost
    always worth taking; otherwise hold cash until the net date.
    """
    now = today or datetime.utcnow()
    parsed = parse_payment_terms(terms)

    try:
        base = datetime.fromisoformat(invoice_date) if invoice_date else now
    except (ValueError, TypeError):
        base = now

    net_due = base + timedelta(days=parsed["net_days"])

    if parsed["discount_pct"] > 0:
        discount_deadline = base + timedelta(days=parsed["discount_days"])
        if now <= discount_deadline:
            savings = round(amount * parsed["discount_pct"], 2)
            annualized = (
                parsed["discount_pct"]
                / (1 - parsed["discount_pct"])
                * (365 / max(parsed["net_days"] - parsed["discount_days"], 1))
            )
            return {
                "action": "pay_now",
                "scheduled_for": now.date().isoformat(),
                "amount_due": round(amount - savings, 2),
                "discount_captured": savings,
                "rationale": (
                    f"Capturing {parsed['discount_pct']:.0%} early-payment discount "
                    f"(${savings:,.2f}) — {annualized:.0%} annualized return on paying "
                    f"{parsed['net_days'] - parsed['discount_days']} days early"
                ),
            }

    return {
        "action": "schedule",
        "scheduled_for": net_due.date().isoformat(),
        "amount_due": round(amount, 2),
        "discount_captured": 0.0,
        "rationale": (
            f"No discount available — holding cash until net-{parsed['net_days']} "
            f"due date {net_due.date().isoformat()}"
        ),
    }


# --------------------------------------------------------- vendor onboarding

def check_vendor_status(
    vendor_name: str,
    provided_bank: str | None,
    record: dict[str, Any] | None,
) -> dict[str, Any]:
    """Gate every invoice on vendor master data before anything else runs.

    Detecting a *changed* bank account on a known vendor is the single highest
    -signal fraud check in real AP — the common attack is a convincing email
    asking to update payment details for a supplier you already trust.
    """
    if not record:
        return {
            "is_new": True,
            "known": False,
            "has_tax_id": False,
            "bank_details_changed": False,
            "detail": f"{vendor_name} is not in the vendor master file",
        }

    stored = (record.get("bank_account") or "").strip()
    provided = (provided_bank or "").strip()
    changed = bool(stored and provided and stored != provided
                   and stored not in provided and provided not in stored)

    return {
        "is_new": False,
        "known": bool(record.get("known", 1)),
        "has_tax_id": bool(record.get("tax_id")),
        "bank_details_changed": changed,
        "previous_bank_account": stored if changed else None,
        "current_bank_account": provided if changed else None,
        "trust_score": float(record.get("trust_score") or 0.5),
        "detail": (
            f"Bank account changed from {stored} to {provided}"
            if changed
            else f"{vendor_name} verified against vendor master"
        ),
    }
