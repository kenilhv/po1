"""InvoiceOS — Kenil (P1): backend + CrewAI. Aditya (P2): TrueFoundry. Shresth (P3): frontend."""

# InvoiceOS

Governed finance AP crew: 6 agents process invoices → risk score → route (auto / human / CFO).

## Run

```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
python -m database.seed
uvicorn main:app --reload --port 8000
```

## Team

| Person | Role |
|--------|------|
| Kenil | Backend + CrewAI |
| Aditya | TrueFoundry gateway |
| Shresth | Frontend |

See `docs/KENIL.md` and `docs/HANDOFF.md`.
