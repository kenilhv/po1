"""PO1 — API surface for the AP pipeline, the human-facing task pages, and revenue.

The two HTML pages here are what Terac participants actually land on. They are
server-rendered on purpose: the study's task_url has to work the moment the
opportunity launches, with no separate frontend deploy in the way.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from crew.privacy import redact_invoice, redaction_summary
from crew.tools.ap_tools import revenue_summary
from database.db import get_conn
from integrations import band_client as band
from integrations import linq_client as linq
from integrations import payments

router = APIRouter()


class VerdictBody(BaseModel):
    verdict: str
    reasoning: str = ""
    reviewer: str = "terac-panel"


class LabelBody(BaseModel):
    labels: list[dict[str, Any]]
    participant: str = "anonymous"


# ------------------------------------------------------------------- reading

@router.get("/po1/invoices")
def list_invoices() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT i.id, i.vendor_name, i.invoice_number, i.amount, i.status,
                   i.risk_score, i.decision, i.gl_code, i.cost_center, i.created_at,
                   e.exception_type, e.severity, e.owner
            FROM invoices i
            LEFT JOIN exceptions e ON e.invoice_id = i.id
            ORDER BY i.id DESC LIMIT 100
            """
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/po1/invoices/{invoice_id}")
def get_invoice(invoice_id: int) -> dict[str, Any]:
    with get_conn() as conn:
        inv = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        exc = conn.execute(
            "SELECT * FROM exceptions WHERE invoice_id = ? ORDER BY id DESC LIMIT 1", (invoice_id,)
        ).fetchone()
        esc = conn.execute(
            "SELECT * FROM terac_escalations WHERE invoice_id = ? ORDER BY id DESC LIMIT 1",
            (invoice_id,),
        ).fetchone()
    if not inv:
        return {"error": "not found"}
    return {
        "invoice": dict(inv),
        "exception": dict(exc) if exc else None,
        "escalation": dict(esc) if esc else None,
        "room": band.room_transcript(invoice_id),
    }


@router.get("/po1/room/{invoice_id}")
def get_room(invoice_id: int) -> dict[str, Any]:
    """The Band agent room for one invoice — every handoff, in order."""
    return {"invoice_id": invoice_id, "messages": band.room_transcript(invoice_id)}


@router.get("/po1/privacy")
def get_privacy() -> dict[str, Any]:
    """What outside reviewers never saw — a control, shown on the dashboard."""
    return redaction_summary()


@router.get("/po1/revenue")
def get_revenue() -> dict[str, Any]:
    return {"internal": revenue_summary(), "stripe": payments.fetch_charges()}


@router.get("/po1/messages")
def get_messages() -> list[dict[str, Any]]:
    return linq.transcript()


@router.get("/po1/exceptions")
def list_exceptions() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT e.*, i.vendor_name, i.amount, i.invoice_number
            FROM exceptions e JOIN invoices i ON i.id = e.invoice_id
            ORDER BY e.id DESC LIMIT 100
            """
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/po1/finetune")
def get_finetune() -> dict[str, Any]:
    from integrations import pioneer_client

    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM finetune_runs ORDER BY id DESC").fetchall()
        labels = conn.execute(
            "SELECT COUNT(*) AS n FROM terac_escalations WHERE verdict IS NOT NULL"
        ).fetchone()
    return {
        "runs": [dict(r) for r in rows],
        "labels_collected": labels["n"],
        "configured": pioneer_client.is_configured(),
    }


# ------------------------------------------------------------------ pipeline

@router.post("/po1/process")
async def process(background_tasks: BackgroundTasks, file: UploadFile = File(...)) -> dict[str, Any]:
    from pathlib import Path

    from main import UPLOAD_DIR, run_po1_pipeline

    path = Path(UPLOAD_DIR) / file.filename
    path.write_bytes(await file.read())
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO invoices (filename, status) VALUES (?, 'processing')", (file.filename,)
        )
        conn.commit()
        invoice_id = int(cur.lastrowid)
    background_tasks.add_task(run_po1_pipeline, invoice_id, str(path))
    return {"invoice_id": invoice_id, "status": "processing"}


# ----------------------------------------------------- human verdict (Terac)

@router.post("/po1/review/{invoice_id}")
def submit_verdict(invoice_id: int, body: VerdictBody) -> dict[str, Any]:
    """A Terac reviewer's ruling. Posting it to the Band room is what unblocks
    approval_router — the pipeline is genuinely waiting on this message."""
    band.post_verdict(invoice_id, body.verdict.upper(), body.reasoning, body.reviewer)

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE terac_escalations
            SET verdict = ?, reasoning = ?, resolved_at = datetime('now')
            WHERE invoice_id = ? AND verdict IS NULL
            """,
            (body.verdict.upper(), body.reasoning, invoice_id),
        )
        conn.execute(
            """
            INSERT INTO audit_log (invoice_id, agent_name, input_summary, output_summary, confidence, approved_by)
            VALUES (?, 'human_reviewer', ?, ?, 1.0, ?)
            """,
            (invoice_id, body.reasoning[:200], body.verdict.upper(), body.reviewer),
        )
        conn.commit()

    return {"invoice_id": invoice_id, "verdict": body.verdict.upper(), "recorded": True}


@router.post("/po1/labels")
def submit_labels(body: LabelBody) -> dict[str, Any]:
    """Batch labels from the Terac study — the Pioneer fine-tune training set."""
    with get_conn() as conn:
        for lab in body.labels:
            conn.execute(
                """
                INSERT INTO terac_escalations
                    (kind, exception_type, question, payload, verdict, reasoning, reviewer_ref, resolved_at)
                VALUES ('study_label', ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    lab.get("exception_type", "label"),
                    lab.get("invoice_summary", "")[:500],
                    json.dumps(lab),
                    str(lab.get("verdict", "")).upper(),
                    lab.get("reasoning", ""),
                    body.participant,
                ),
            )
        conn.commit()
    return {"recorded": len(body.labels), "participant": body.participant}


# --------------------------------------------------- pages participants see

_PAGE_CSS = """
:root{color-scheme:light dark;--bg:#0d0f13;--card:#161a21;--bd:#272d37;--tx:#e8e6df;
--dim:#98a0aa;--acc:#f2a73b;--go:#3ecf8e;--no:#e8664a}
@media(prefers-color-scheme:light){:root{--bg:#f6f3ec;--card:#fff;--bd:#ded6c6;
--tx:#1e1e1b;--dim:#5f594c;--acc:#a96a0d;--go:#157a4f;--no:#b8402a}}
*{box-sizing:border-box}body{margin:0;padding:24px 16px 64px;background:var(--bg);color:var(--tx);
font:15px/1.55 -apple-system,Segoe UI,Inter,system-ui,sans-serif}
.w{max-width:640px;margin:0 auto}
h1{font-size:23px;margin:0 0 6px;letter-spacing:-.02em}
.sub{color:var(--dim);margin:0 0 22px;font-size:14.5px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:11px;padding:18px;margin-bottom:14px}
.row{display:flex;justify-content:space-between;gap:12px;padding:7px 0;border-bottom:1px solid var(--bd);font-size:14px}
.row:last-child{border:0}.row .k{color:var(--dim)}.row .v{font-weight:600;text-align:right}
.flag{background:rgba(232,102,74,.12);border:1px solid var(--no);color:var(--tx);
border-radius:8px;padding:12px 14px;margin:14px 0;font-size:14px}
.flag b{color:var(--no);display:block;font-size:11px;letter-spacing:.09em;text-transform:uppercase;margin-bottom:5px}
.btns{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0 10px}
button{flex:1;min-width:130px;padding:13px 16px;border-radius:9px;border:1px solid var(--bd);
background:var(--card);color:var(--tx);font-size:14.5px;font-weight:600;cursor:pointer;font-family:inherit}
button:hover{border-color:var(--acc)}
button.yes{border-color:var(--go);color:var(--go)}button.no{border-color:var(--no);color:var(--no)}
button.sel{background:var(--acc);border-color:var(--acc);color:#141414}
textarea{width:100%;min-height:74px;padding:11px;border-radius:9px;border:1px solid var(--bd);
background:var(--bg);color:var(--tx);font:inherit;font-size:14px;resize:vertical}
.go{width:100%;margin-top:14px;background:var(--acc);border-color:var(--acc);color:#141414;padding:14px}
.ok{text-align:center;padding:48px 20px}.ok h2{color:var(--go);margin:0 0 8px}
.pill{display:inline-block;font-size:11px;letter-spacing:.08em;text-transform:uppercase;
color:var(--acc);border:1px solid var(--acc);border-radius:5px;padding:3px 8px;margin-bottom:12px}
.prog{color:var(--dim);font-size:13px;margin-bottom:14px}
"""


@router.get("/review/{invoice_id}", response_class=HTMLResponse)
def review_page(invoice_id: int) -> str:
    """What a Terac reviewer sees. Real evidence from the pipeline, one decision."""
    with get_conn() as conn:
        inv = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        exc = conn.execute(
            "SELECT * FROM exceptions WHERE invoice_id = ? ORDER BY id DESC LIMIT 1", (invoice_id,)
        ).fetchone()

    if not inv:
        return f"<!doctype html><style>{_PAGE_CSS}</style><div class=w><h1>Invoice not found</h1></div>"

    inv, exc = dict(inv), dict(exc) if exc else {}

    # Reviewers are outside the company: they get a pseudonymised invoice with
    # proportionally accurate figures, never the real commercial data.
    safe = redact_invoice(inv, exc)

    po_line = (
        f"${safe['po_amount']:,.2f} agreed" if safe.get("po_amount") else "None on file"
    )

    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Review a payment — PO1</title><style>{_PAGE_CSS}</style></head><body><div class="w">
<span class="pill">Payment review</span>
<h1>Should this bill be paid?</h1>
<p class="sub">An automated system flagged this payment and stopped. It needs a person to decide.
No accounting knowledge required — use your judgment.</p>

<div class="card">
  <div class="row"><span class="k">Supplier</span><span class="v">{safe['vendor']}</span></div>
  <div class="row"><span class="k">They are billing</span><span class="v">${safe['amount']:,.2f}</span></div>
  <div class="row"><span class="k">Amount agreed upfront</span><span class="v">{po_line}</span></div>
  <div class="row"><span class="k">Category</span><span class="v">{safe['category']}</span></div>
  <div class="row"><span class="k">Reference</span><span class="v">{safe['reference']}</span></div>
</div>

<div class="flag"><b>Why it was stopped</b>{safe.get('concern') or 'This payment needs a second opinion.'}</div>

<p class="sub" style="font-size:12.5px;margin:-4px 0 14px">
Supplier names are replaced with consistent stand-ins and amounts are scaled, so you see a
true picture of the problem without any real company's private financial data.</p>

<div class="card">
  <p style="margin:0 0 4px;font-weight:600">Your decision</p>
  <p class="sub" style="margin:0 0 4px">Would you pay this?</p>
  <div class="btns">
    <button class="yes" onclick="pick('APPROVE',this)">Yes, pay it</button>
    <button class="no" onclick="pick('REJECT',this)">No, don't pay</button>
    <button onclick="pick('INVESTIGATE',this)">Needs more checking</button>
  </div>
  <textarea id="why" placeholder="In a sentence — what made you decide that?"></textarea>
  <button class="go" onclick="send()">Submit decision</button>
</div>
</div>
<script>
let v=null;
function pick(x,el){{v=x;document.querySelectorAll('.btns button').forEach(b=>b.classList.remove('sel'));el.classList.add('sel');}}
async function send(){{
  if(!v){{alert('Pick one of the three options first.');return;}}
  await fetch('/po1/review/{invoice_id}',{{method:'POST',headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify({{verdict:v,reasoning:document.getElementById('why').value||'No reason given',reviewer:'terac-panel'}})}});
  document.querySelector('.w').innerHTML=
    '<div class=ok><h2>Thank you</h2><p class=sub>Your decision was sent to the system and it has resumed. You can close this page.</p></div>';
}}
</script></body></html>"""


@router.get("/label", response_class=HTMLResponse)
def label_page() -> str:
    """The general-population labeling task that trains the fraud model."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, vendor_name, invoice_number, amount, po_reference, bank_details, cost_center
            FROM invoices WHERE vendor_name IS NOT NULL ORDER BY id DESC LIMIT 8
            """
        ).fetchall()
    items = [dict(r) for r in rows]

    if not items:
        items = [
            {"id": 0, "vendor_name": "OfficeSupplyCo", "invoice_number": "INV-2024-441",
             "amount": 800, "po_reference": "PO-8821", "cost_center": "G&A"},
            {"id": 0, "vendor_name": "CleanVendor Inc", "invoice_number": "INV-2024-910",
             "amount": 480, "po_reference": "PO-9901", "cost_center": "G&A",
             "bank_details": "changed since last payment"},
            {"id": 0, "vendor_name": "FastConsult LLC", "invoice_number": "INV-F-0042",
             "amount": 45000, "po_reference": None, "cost_center": "Operations"},
        ]

    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Which invoices look risky? — PO1</title><style>{_PAGE_CSS}</style></head><body><div class="w">
<span class="pill">Quick judgment task</span>
<h1>Which of these bills look risky to pay?</h1>
<p class="sub">You'll see a few real business invoices. For each one, say whether a company
should pay it or check it first. No accounting background needed — we want ordinary judgment
about what looks off. Takes about three minutes.</p>
<div id="app"></div></div>
<script>
const items = {json.dumps(items)};
let i = 0; const out = [];
function summary(x){{
  let s = x.vendor_name + ' billed $' + Number(x.amount||0).toLocaleString() +
          ' on invoice ' + (x.invoice_number||'n/a') + '. ';
  s += x.po_reference ? ('It matches purchase order ' + x.po_reference + '.')
                      : 'There is no purchase order authorizing it.';
  if (x.bank_details && String(x.bank_details).toLowerCase().includes('chang'))
    s += ' The vendor recently changed their bank account.';
  return s;
}}
function render(){{
  if (i >= items.length) return finish();
  const x = items[i];
  document.getElementById('app').innerHTML = `
    <p class="prog">Invoice ${{i+1}} of ${{items.length}}</p>
    <div class="card">
      <div class="row"><span class="k">Vendor</span><span class="v">${{x.vendor_name||'—'}}</span></div>
      <div class="row"><span class="k">Amount</span><span class="v">$${{Number(x.amount||0).toLocaleString()}}</span></div>
      <div class="row"><span class="k">Invoice</span><span class="v">${{x.invoice_number||'—'}}</span></div>
      <div class="row"><span class="k">Purchase order</span><span class="v">${{x.po_reference||'None on file'}}</span></div>
      ${{x.bank_details ? `<div class="row"><span class="k">Bank details</span><span class="v">${{x.bank_details}}</span></div>` : ''}}
    </div>
    <div class="btns">
      <button class="no" onclick="mark('risky')">Looks risky</button>
      <button class="yes" onclick="mark('safe')">Looks fine</button>
    </div>
    <textarea id="why" placeholder="Why? A few words is plenty."></textarea>`;
}}
function mark(v){{
  out.push({{invoice_summary: summary(items[i]), verdict: v,
             reasoning: (document.getElementById('why')||{{}}).value || '',
             exception_type: 'label'}});
  i++; render();
}}
async function finish(){{
  await fetch('/po1/labels',{{method:'POST',headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify({{labels: out, participant: 'terac-' + Math.random().toString(36).slice(2,8)}})}});
  document.querySelector('.w').innerHTML =
    '<div class=ok><h2>All done — thank you</h2><p class=sub>Your answers are training a system that flags risky business payments. You can close this page.</p></div>';
}}
render();
</script></body></html>"""
