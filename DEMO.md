# PO1 — demo script (3 minutes)

**Setup before your slot:** dashboard open at https://po1-api.onrender.com · Band room open in a second tab · phone in hand, iMessage visible · Terac submissions page in a third tab.

---

## 0:00 — The problem (one breath)

> "Startups make their first finance hire around employee 8 — not because the work starts then, but because that's when they can afford $1,400+ a month for a fractional CFO. PO1 is that hire, from day one. It's an accounts-payable department that runs itself — and knows exactly when to buy human judgment instead of guessing."

## 0:20 — Fire the pipeline, live

Click nothing fancy — hit the demo trigger (or upload one invoice):

```bash
curl -X POST https://po1-api.onrender.com/po1/demo
```

> "Four real invoices just hit the system. Ten agents are processing them — every handoff you see in this Band room is a real message between real registered agents, not a log we styled."

**Point at the Band room tab:** vendor_onboarder → three_way_matcher → fraud_signal → exception_classifier, each posting under its own name.

## 0:50 — The clean one pays itself

Click the OfficeSupplyCo invoice on the dashboard.

> "Clean three-way match — purchase order, goods receipt, invoice all agree. Under the $2,000 authority limit, so PO1 pays it, and it noticed the 2/10 net 30 terms — it paid early to capture the discount. That's a 37% annualized return on timing alone. A junior AP clerk misses that; this doesn't."

**Hold up the phone:** the vendor's remittance advice just arrived as an iMessage. Real message, real Linq number.

## 1:30 — The dangerous one gets stopped

Click the CleanVendor invoice (banking change).

> "This vendor has been paid before — but the bank account on this invoice is different. That's the #1 real-world AP fraud pattern: not fake invoices, hijacked vendor accounts. PO1 will never self-approve a banking change. Watch what it does instead."

**Band room:** exception_classifier names the exception, the **controller agent joins the thread at runtime** — recruited because of what a different agent found.

## 2:00 — It hires a real human

Click the escalated invoice (unknown vendor, $3,200).

> "No tax ID on file — paying this isn't even 1099-reportable. PO1 won't guess. It opened a study on Terac and is paying a real, verified human $6 to rule on it. And here's the part I'm proudest of —"

**Show the review page** (open /review/{id} on the laptop):

> "— the reviewer sees *this*. 'Marlow & Finch, $2,656.' The real vendor is someone else; the real amount is different. Names are stable pseudonyms, amounts are proportionally scaled — a 54% overbill still reads as 54% — and bank details never leave the building. Real judgment, zero data leakage."

**Submit a verdict on the phone** (as stand-in reviewer — say so): *"Four recruited reviewers are in Terac's funnel right now — I'm standing in so you don't have to wait. Watch the pipeline unblock."* The invoice resolves on the dashboard; the founder gets the resolution text.

## 2:40 — The business

> "PO1 charges $299 a month — five to ten times under the cheapest human alternative — plus $1 per human judgment actually consumed. The agent mints its own Stripe checkout per sale. The whole thing runs on open-weight Qwen models on Pioneer; the parser is Fastino's GLiNER2 — one encoder pass, no prompts. It's deployed on Render with an hourly payment run, and it's been running unattended all day. This isn't a demo of an idea. It's a company that was operating while I was talking to you."

---

## Likely judge questions — honest answers

- **"Is the revenue real?"** — Stripe sandbox, organizer-approved: I'm on an F1 visa and can't legally accept payments. The pipeline is identical to live mode; only the key changes.
- **"Did humans actually respond?"** — Study launched at 4:30 with real money ($24). Terac's funnel includes an AI screening interview, so completions may land after judging — the loop is live, not staged. [Show the Terac dashboard.]
- **"What did the LLM decide vs. rules?"** — Classification and severity are deliberately deterministic — auditability is the point in finance. The LLMs do extraction and judgment-adjacent reasoning; every decision lands in the audit log with the model that made it.
- **"Why not fine-tune?"** — The loop is built (labels → JSONL → Pioneer training job → swap → re-eval on a fixed batch); it fires when the labels land. We chose not to fake the before/after with our own labels.
- **"Multi-tenant?"** — Schema carries org boundaries and a vendor master; signup UI is the unglamorous week, not the interesting part.

## Track checklist (say these words near judges)

- **Terac (required):** live paid study + realtime escalation, pseudonymized
- **Band:** room is load-bearing — classifier reads upstream findings from it, controller recruited at runtime, human verdict unblocks the router
- **Linq:** remittance advice + variance queries + founder alerts, real iMessages
- **Pioneer:** all agents on open-weight Qwen; parser is Fastino GLiNER2 (bonus criterion)
- **Render:** Workflows cron = the hourly payment run
- **Stripe:** agent-minted checkout per transaction
