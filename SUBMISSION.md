# PO1 — submission

**Name:** PO1 (Purchase Order One)
**One-liner:** The finance hire a startup never makes — an autonomous accounts-payable department that pays what it can defend and buys real human judgment when it can't.

**Live:** https://po1-api.onrender.com
**Repo:** https://github.com/kenilhv/po1
**Demo flow:** open the site → "Run the day's intake" → watch the ledger settle itself.

## What it is

Startups make their first finance hire around employee 8 — not when the work starts, but when they can afford $1,400+/mo for a fractional CFO. PO1 is that hire from day one: ten agents that run real AP the way real AP departments work — vendor master gating (W-9/tax ID, banking-change detection: the #1 real AP fraud vector), 3-way match against PO *and* goods receipt, GL coding, typed exceptions with named owners (not a blended risk score), amount-tiered delegation of authority, and payment runs timed to capture early-payment discounts (2/10 net 30 ≈ 37% annualized).

The thesis: autonomy isn't doing everything alone — it's knowing the exact moment to buy human judgment. PO1 never self-approves a vendor banking change; it hires a verified human through Terac, mid-pipeline, and blocks until the verdict returns.

**Privacy by construction:** outside reviewers never see real data. Vendors become stable pseudonyms, amounts scale proportionally (a 54% overbill still reads as 54%), bank details never leave. Real judgment, zero leakage.

**Business model:** $299/mo (5–10× under a fractional CFO) + $1 per human judgment consumed. The agent mints its own Stripe checkout per sale. Sandbox per organizer approval (F1 visa).

## Sponsor integrations — all load-bearing

- **Terac (required):** Live paid study (launched 4:30 PM, real $) recruiting a general-population panel to label pseudonymized invoices → training data for the fraud model. Plus realtime escalation: flagged invoices open a Terac opportunity and the pipeline blocks on the reviewer's verdict.
- **Band:** All 11 agents hold their own registered Band identities and post to a shared room. Load-bearing: the exception classifier reads upstream findings *from the room*, a controller agent is recruited at runtime on banking changes, and the human verdict posted to the room is what unblocks the approval router. Remove the room, the pipeline stops.
- **Pioneer:** Every agent thinks on open-weight models (Qwen3-4B mechanical / Qwen3-8B judgment) via Pioneer inference. The invoice parser is **Fastino GLiNER2** — schema extraction in one encoder pass (bonus criterion). Fine-tune loop (Terac labels → JSONL → training job → fixed-batch before/after) is built and fires when labels land.
- **Linq:** Real iMessages — remittance advice to vendors (the actual post-payment document), variance queries where a tapback is the answer, and payment-held alerts to the founder's phone.
- **Render:** Deployed web service + cron Workflow running the hourly payment batch unattended all day.
- **Stripe:** Dynamic per-transaction checkout created by the agent; restricted read-only key feeds live revenue to the dashboard.

## Tracks

Best Overall Project · Best Overall Agent-Run Company · Best use of Linq · Best use of Band · Best use of Pioneer · Best use of Render · Best use of Replay
