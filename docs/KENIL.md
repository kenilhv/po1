# Kenil (Person 1) — Backend + CrewAI

## What we're building

**InvoiceOS** — upload PDF → 6 CrewAI agents run → WebSocket streams each step → risk decision → human approves if needed.

| Agent | Job |
|-------|-----|
| invoice_parser | PDF → structured fields |
| po_matcher | Match PO in SQLite |
| duplicate_detector | Check payment history |
| fraud_signal | Vendor/bank signals |
| risk_scorer | LOW/MEDIUM/HIGH/CRITICAL |
| approval_router | Route decision (never pays) |

## Config (.env)

```
OPENAI_API_BASE=<Aditya gives TrueFoundry gateway /v1 URL>
OPENAI_API_KEY=<Aditya gives key>
CHEAP_MODEL=gpt-3.5-turbo
EXPENSIVE_MODEL=gpt-4o
```

## Your timeline

### Now → +30 min (before Shresth needs schema)

1. `cd backend` → venv → `pip install -r requirements.txt`
2. `python -m database.seed`
3. **Send Shresth now:** WebSocket schema in `models/schemas.py` + `POST /invoice/upload`, `GET /invoice/list`, `WS /ws/trace/{id}`
4. Build `main.py` endpoints + WebSocket manager (scaffold exists — extend)

### +30 → +45 min (Aditya handoff)

5. Give Aditya exact agent names: `invoice_parser`, `po_matcher`, `duplicate_detector`, `fraud_signal`, `risk_scorer`, `approval_router`
6. Plug Aditya's `.env` → test one LLM call through gateway
7. Wire `crew/orchestrator.py` — Parser first, then 2/3/4 parallel, then 5, then 6
8. **Emit WebSocket message after each agent** — do not batch

### +45 → +75 min (Shresth handoff)

9. Finish all 6 agents + end-to-end on 3 demo PDFs
10. Test: clean → AUTO_APPROVED, duplicate → FLAGGED, fraud → CRITICAL
11. **Hand Shresth:** server at `http://localhost:8000`, upload works, WS trace live

### +75 min → demo

12. E2E with Shresth UI + Aditya audit trail

## Integration with Aditya (+45 min)

- You: env vars only, no hardcoded OpenAI URL
- Aditya: registers 6 agents in TrueFoundry, gives you gateway URL/key
- Test together: upload invoice → see trace in TrueFoundry dashboard

## Integration with Shresth (+75 min)

Share:
- `WebSocketTraceMessage` JSON (models/schemas.py)
- Agent order list above
- `POST /invoice/{id}/approve` body: `{"action":"approve","approver":"CFO"}`

## Demo PDFs (create in demo_invoices/)

| File | Vendor | Amount | Expected |
|------|--------|--------|----------|
| invoice_good.pdf | OfficeSupplyCo | $800 | AUTO_APPROVED |
| invoice_duplicate.pdf | TechSoftware Inc | $1,200 | DUPLICATE |
| invoice_fraud.pdf | FastConsult LLC | $45,000 | CRITICAL |

## Don't

- Wait to stream WS until all agents done
- Hardcode OpenAI URL
- Let agents "send payment" — router only routes
