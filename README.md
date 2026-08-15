# InvoiceOS

Governed finance AP crew: 6 agents process invoices → risk score → route (auto / human / CFO).

## Run

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m database.seed
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
npm install
npm run dev
```

## Team

| Person | Role |
|--------|------|
| Kenil | Backend + CrewAI |
| Aditya | TrueFoundry gateway |
| Shresth | Frontend |

See `docs/KENIL.md` and `docs/HANDOFF.md`.
