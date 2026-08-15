# Handoff schedule

| Time | Who | What |
|------|-----|------|
| **T+0** | Kenil → Shresth | WebSocket schema + endpoint list |
| **T+45 min** | Kenil ↔ Aditya | `.env` gateway URL, test LLM call, register 6 agents |
| **T+75 min** | Kenil → Shresth | Server live, upload + WS trace working |
| **T+90 min** | All | E2E test |

## Aditya (P2) — needs from Kenil at +45 min

Agent names to register in TrueFoundry:
1. `invoice_parser` — cheap model
2. `po_matcher` — cheap
3. `duplicate_detector` — cheap
4. `fraud_signal` — expensive
5. `risk_scorer` — expensive
6. `approval_router` — cheap

Give Aditya: `backend/.env.example` + running `POST /invoice/upload`

## Shresth (P3) — needs from Kenil at T+0 and T+75

**T+0:** `models/schemas.py` → `WebSocketTraceMessage`

**Endpoints:**
- `POST /invoice/upload` → `{invoice_id, status}`
- `GET /invoice/list`
- `GET /invoice/{id}`
- `POST /invoice/{id}/approve` → body `{"action":"approve"|"reject","approver":"CFO"}`
- `GET /audit/log`
- `WS /ws/trace/{invoice_id}`

**T+75:** `http://localhost:8000` + upload demo PDF + watch WS messages
