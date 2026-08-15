"""Run every AP scenario through the full 10-agent pipeline, no server needed."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crew.agents.ap_rules import (  # noqa: E402
    assign_gl_code, check_vendor_status, classify_exception,
    route_decision, schedule_payment, score_severity, three_way_match,
)
from crew.tools.ap_tools import check_budget, lookup_goods_receipt, lookup_vendor_record  # noqa: E402
from crew.tools.po_tool import lookup_duplicate, lookup_po, lookup_vendor  # noqa: E402
from database.seed_ap import SCENARIOS, seed  # noqa: E402
from integrations import band_client as band  # noqa: E402

AUTO_LIMIT, FOUNDER_LIMIT = 2000.0, 10000.0


def run_case(idx: int, label: str, vendor: str, amount: float,
             po_ref: str | None, bank: str, expected: str) -> bool:
    inv_num = f"INV-TEST-{idx}"

    vendor_status = check_vendor_status(vendor, bank, lookup_vendor_record(vendor))
    band.post_finding(idx, "vendor_onboarder", vendor_status)

    match = three_way_match(amount, lookup_po(vendor, po_ref), lookup_goods_receipt(vendor, po_ref))
    band.post_finding(idx, "three_way_matcher", match)

    dup = lookup_duplicate(vendor, amount, inv_num)
    fraud = lookup_vendor(vendor, bank)
    gl = assign_gl_code(vendor, "")
    for a, f in (("duplicate_detector", dup), ("fraud_signal", fraud), ("gl_coder", gl)):
        band.post_finding(idx, a, f)

    room = band.read_findings(idx)
    budget = check_budget(gl["cost_center"], amount)

    exc = classify_exception({
        "match": match, "duplicate": dup, "fraud": fraud,
        "vendor_status": vendor_status, "budget": budget, "amount": amount,
    })
    pv = (match.get("price_variance") or {}).get("pct")
    severity, _ = score_severity(
        exc["exception_type"], amount, float(vendor_status.get("trust_score") or 0.5), pv
    )
    decision, detail = route_decision(severity, amount, exc["exception_type"],
                                      {"auto": AUTO_LIMIT, "founder": FOUNDER_LIMIT})

    ok = exc["exception_type"] == expected
    print(f"\n{'✓' if ok else '✗'} {label}")
    print(f"   {vendor} | ${amount:,.2f} | {gl['gl_code']} {gl['cost_center']}")
    print(f"   match      {match['legs_matched']}/3 legs")
    print(f"   room       {len(room)} findings: {', '.join(room)}")
    print(f"   exception  {exc['exception_type']} (expected {expected}) → owner: {exc['owner']}")
    print(f"   severity   {severity}")
    print(f"   decision   {decision} — {detail}")

    if decision == "AUTO_APPROVED":
        s = schedule_payment(amount, "2/10 net 30")
        print(f"   payment    {s['action']} — {s['rationale']}")
    return ok


def main() -> None:
    seed()
    print("=" * 74)
    print("PO1 — 10-agent AP pipeline")
    print("=" * 74)
    results = [run_case(i + 1, *s) for i, s in enumerate(SCENARIOS)]
    print("\n" + "=" * 74)
    print(f"{sum(results)}/{len(results)} scenarios classified as expected")


if __name__ == "__main__":
    main()
