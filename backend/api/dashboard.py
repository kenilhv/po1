"""PO1 — mission control.

One page, no login, served by the same process as the API so there is exactly
one thing to deploy and nothing to build. It shows the four things that prove
the system is real: the agent room carrying every handoff, the typed exception
each invoice produced, what PO1 decided to pay, and the human judgment it
bought when it would not decide alone.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

CSS = """
:root{
  --bg:#0b0d10;--panel:#13171d;--panel2:#171c23;--bd:#242a33;--bd2:#1b2028;
  --tx:#e9e7e0;--dim:#8f97a1;--faint:#5a626c;
  --acc:#f2a73b;--go:#3ecf8e;--no:#e8664a;--info:#5aa9e6;
  --mono:ui-monospace,"SF Mono","Cascadia Code",Consolas,monospace;
}
@media(prefers-color-scheme:light){:root{
  --bg:#f5f2ea;--panel:#fff;--panel2:#faf8f3;--bd:#ddd5c4;--bd2:#e8e2d5;
  --tx:#1d1d1a;--dim:#5e594d;--faint:#8a8474;
  --acc:#a96a0d;--go:#157a4f;--no:#b8402a;--info:#2b6fa8;}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.5 -apple-system,"Segoe UI",Inter,system-ui,sans-serif}
.top{border-bottom:1px solid var(--bd);padding:16px 22px;display:flex;align-items:center;gap:16px;flex-wrap:wrap;position:sticky;top:0;background:var(--bg);z-index:9}
.brand{font-size:20px;font-weight:700;letter-spacing:-.02em}
.brand span{color:var(--acc)}
.tag{font:11px/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--dim)}
.dot{width:7px;height:7px;border-radius:50%;display:inline-block;margin-right:5px}
.on{background:var(--go)}.off{background:var(--faint)}
.pills{display:flex;gap:7px;flex-wrap:wrap;margin-left:auto}
.pill{font:11px/1 var(--mono);padding:5px 9px;border:1px solid var(--bd);border-radius:20px;color:var(--dim);text-transform:uppercase;letter-spacing:.06em}
.wrap{padding:20px 22px 70px;max-width:1500px;margin:0 auto}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:12px;margin-bottom:20px}
.kpi{background:var(--panel);border:1px solid var(--bd2);border-radius:11px;padding:15px 17px}
.kpi .l{font:10.5px/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--faint);margin-bottom:9px}
.kpi .v{font-size:25px;font-weight:700;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.kpi .s{font-size:12px;color:var(--dim);margin-top:3px}
.kpi.acc .v{color:var(--acc)}.kpi.go .v{color:var(--go)}.kpi.no .v{color:var(--no)}
.grid{display:grid;grid-template-columns:1.15fr 1fr;gap:16px}
@media(max-width:1080px){.grid{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--bd2);border-radius:12px;overflow:hidden;margin-bottom:16px}
.hd{padding:13px 17px;border-bottom:1px solid var(--bd2);display:flex;align-items:center;gap:10px;background:var(--panel2)}
.hd h2{margin:0;font:11.5px/1 var(--mono);letter-spacing:.11em;text-transform:uppercase;color:var(--dim);font-weight:600}
.hd .n{margin-left:auto;font:11px/1 var(--mono);color:var(--faint)}
.bd{padding:6px 0;max-height:440px;overflow-y:auto}
.bd.pad{padding:15px 17px}
.empty{padding:30px 18px;text-align:center;color:var(--faint);font-size:13px}
.msg{padding:9px 17px;border-bottom:1px solid var(--bd2);display:flex;gap:11px;align-items:flex-start}
.msg:last-child{border:0}
.msg .who{font:11px/1.4 var(--mono);color:var(--acc);min-width:132px;flex-shrink:0}
.msg .txt{flex:1;font-size:13px;color:var(--tx)}
.msg.human{background:rgba(62,207,142,.07)}
.msg.human .who{color:var(--go)}
.msg.sys .who{color:var(--info)}
.inv{padding:12px 17px;border-bottom:1px solid var(--bd2);cursor:pointer}
.inv:last-child{border:0}
.inv:hover{background:var(--panel2)}
.inv.sel{background:var(--panel2);box-shadow:inset 3px 0 0 var(--acc)}
.inv .r1{display:flex;justify-content:space-between;gap:10px;align-items:baseline}
.inv .v{font-weight:600;font-size:14px}
.inv .a{font-variant-numeric:tabular-nums;font-weight:600}
.inv .r2{display:flex;gap:7px;align-items:center;margin-top:6px;flex-wrap:wrap}
.b{font:10px/1 var(--mono);padding:4px 7px;border-radius:4px;text-transform:uppercase;letter-spacing:.05em;border:1px solid}
.b.clean{color:var(--go);border-color:var(--go)}
.b.warn{color:var(--acc);border-color:var(--acc)}
.b.crit{color:var(--no);border-color:var(--no)}
.b.mut{color:var(--faint);border-color:var(--bd)}
.step{padding:9px 17px;border-bottom:1px solid var(--bd2);display:flex;gap:11px;align-items:flex-start}
.step:last-child{border:0}
.step .i{width:17px;flex-shrink:0;font:11px/1.5 var(--mono)}
.step .nm{font:11.5px/1.5 var(--mono);color:var(--tx);min-width:150px;flex-shrink:0}
.step .dt{flex:1;font-size:12.5px;color:var(--dim)}
.step.ok .i{color:var(--go)}.step.ok .i::before{content:"●"}
.step.hold .i{color:var(--acc)}.step.hold .i::before{content:"◐"}
.step.run .i{color:var(--info)}.step.run .i::before{content:"○"}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{font:10px/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--faint);text-align:left;padding:9px 17px;border-bottom:1px solid var(--bd2)}
td{padding:9px 17px;border-bottom:1px solid var(--bd2)}
tr:last-child td{border:0}
td.num{font-variant-numeric:tabular-nums;text-align:right}
.ba{display:grid;grid-template-columns:1fr auto 1fr;gap:14px;align-items:center;padding:16px}
.ba .col{text-align:center}
.ba .lb{font:10px/1 var(--mono);letter-spacing:.09em;text-transform:uppercase;color:var(--faint);margin-bottom:7px}
.ba .big{font-size:27px;font-weight:700;font-variant-numeric:tabular-nums}
.ba .arrow{color:var(--acc);font-size:19px}
.ba .after .big{color:var(--go)}
.note{padding:11px 17px;font-size:12.5px;color:var(--dim);border-top:1px solid var(--bd2);background:var(--panel2)}
.foot{margin-top:26px;font:11px/1.6 var(--mono);color:var(--faint);text-align:center}
"""


@router.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PO1 — Mission Control</title><style>{CSS}</style></head><body>

<div class="top">
  <div class="brand">PO<span>1</span></div>
  <div class="tag">Autonomous accounts payable</div>
  <div class="pills" id="pills"></div>
</div>

<div class="wrap">
  <div class="kpis" id="kpis"></div>
  <div class="grid">
    <div>
      <div class="card">
        <div class="hd"><h2>Invoices</h2><span class="n" id="invn"></span></div>
        <div class="bd" id="invoices"><div class="empty">No invoices yet</div></div>
      </div>
      <div class="card">
        <div class="hd"><h2>Agent room — Band</h2><span class="n" id="roomn"></span></div>
        <div class="bd" id="room"><div class="empty">Select an invoice to see the agents' handoffs</div></div>
      </div>
    </div>
    <div>
      <div class="card">
        <div class="hd"><h2>Pipeline</h2><span class="n" id="stepn"></span></div>
        <div class="bd" id="steps"><div class="empty">Select an invoice</div></div>
      </div>
      <div class="card">
        <div class="hd"><h2>Exceptions</h2><span class="n" id="excn"></span></div>
        <div class="bd" id="exceptions"><div class="empty">Nothing flagged</div></div>
      </div>
      <div class="card">
        <div class="hd"><h2>Human input → model quality</h2></div>
        <div id="finetune"><div class="empty">No fine-tune run yet</div></div>
      </div>
      <div class="card">
        <div class="hd"><h2>Messages sent</h2><span class="n" id="msgn"></span></div>
        <div class="bd" id="messages"><div class="empty">Nothing sent yet</div></div>
      </div>
    </div>
  </div>
  <div class="foot">PO1 — the finance hire a startup never makes · Zero-Human Company Hackathon</div>
</div>

<script>
let sel = null;
const money = n => '$' + Number(n||0).toLocaleString(undefined,{{minimumFractionDigits:2,maximumFractionDigits:2}});
const esc = s => String(s==null?'':s).replace(/[<>&]/g, c => ({{'<':'&lt;','>':'&gt;','&':'&amp;'}}[c]));

function sevClass(s){{
  s = String(s||'').toUpperCase();
  if (s==='CRITICAL'||s==='HIGH') return 'crit';
  if (s==='MEDIUM') return 'warn';
  if (s==='LOW') return 'clean';
  return 'mut';
}}
function decClass(d){{
  d = String(d||'').toUpperCase();
  if (d==='PAID'||d==='AUTO_APPROVED') return 'clean';
  if (d==='BLOCKED'||d==='REJECTED') return 'crit';
  if (d.startsWith('PENDING')) return 'warn';
  return 'mut';
}}

async function j(u){{ try {{ const r = await fetch(u); return await r.json(); }} catch(e){{ return null; }} }}

async function tick(){{
  const [health, invs, rev, excs, msgs, ft] = await Promise.all([
    j('/health'), j('/po1/invoices'), j('/po1/revenue'),
    j('/po1/exceptions'), j('/po1/messages'), j('/po1/finetune')
  ]);

  if (health) document.getElementById('pills').innerHTML =
    ['terac','band','linq','stripe','pioneer'].map(k =>
      `<span class="pill"><i class="dot ${{health[k]?'on':'off'}}"></i>${{k}}</span>`).join('');

  const list = invs || [];
  const paid = list.filter(i => String(i.status).toUpperCase()==='PAID');
  const held = list.filter(i => ['BLOCKED','PENDING_TERAC','PENDING_FOUNDER'].includes(String(i.decision||'').toUpperCase()));
  const paidTotal = paid.reduce((s,i)=>s+Number(i.amount||0),0);
  const heldTotal = held.reduce((s,i)=>s+Number(i.amount||0),0);
  const revTotal = (rev && rev.internal && rev.internal.total) || 0;
  const stripeTotal = (rev && rev.stripe && rev.stripe.total) || 0;

  document.getElementById('kpis').innerHTML = `
    <div class="kpi"><div class="l">Invoices processed</div><div class="v">${{list.length}}</div>
      <div class="s">${{paid.length}} paid autonomously</div></div>
    <div class="kpi go"><div class="l">Paid without a human</div><div class="v">${{money(paidTotal)}}</div>
      <div class="s">${{list.length ? Math.round(paid.length/list.length*100) : 0}}% of volume</div></div>
    <div class="kpi no"><div class="l">Held for review</div><div class="v">${{money(heldTotal)}}</div>
      <div class="s">${{held.length}} invoice(s) stopped</div></div>
    <div class="kpi acc"><div class="l">PO1 revenue</div><div class="v">${{money(revTotal)}}</div>
      <div class="s">Stripe confirmed ${{money(stripeTotal)}}</div></div>
    <div class="kpi"><div class="l">Human labels</div><div class="v">${{(ft&&ft.labels_collected)||0}}</div>
      <div class="s">via Terac panel</div></div>`;

  document.getElementById('invn').textContent = list.length ? list.length + ' total' : '';
  document.getElementById('invoices').innerHTML = list.length ? list.map(i => `
    <div class="inv ${{sel===i.id?'sel':''}}" onclick="pick(${{i.id}})">
      <div class="r1"><span class="v">${{esc(i.vendor_name)||'Unknown vendor'}}</span>
        <span class="a">${{money(i.amount)}}</span></div>
      <div class="r2">
        <span class="b ${{decClass(i.decision)}}">${{esc(i.decision||i.status||'processing')}}</span>
        ${{i.exception_type && i.exception_type!=='clean'
            ? `<span class="b ${{sevClass(i.severity)}}">${{esc(i.exception_type).replace(/_/g,' ')}}</span>` : ''}}
        ${{i.owner && i.owner!=='none' ? `<span class="b mut">owner: ${{esc(i.owner)}}</span>` : ''}}
        ${{i.gl_code ? `<span class="b mut">${{esc(i.gl_code)}} ${{esc(i.cost_center||'')}}</span>` : ''}}
      </div>
    </div>`).join('') : '<div class="empty">No invoices yet — upload one to start the pipeline</div>';

  const ex = excs || [];
  document.getElementById('excn').textContent = ex.length ? ex.length + ' open' : '';
  document.getElementById('exceptions').innerHTML = ex.length ? `<table>
    <tr><th>Vendor</th><th>Exception</th><th>Owner</th><th class="num">Amount</th></tr>
    ${{ex.slice(0,12).map(e=>`<tr><td>${{esc(e.vendor_name)}}</td>
      <td><span class="b ${{sevClass(e.severity)}}">${{esc(e.exception_type).replace(/_/g,' ')}}</span></td>
      <td style="color:var(--dim)">${{esc(e.owner)}}</td>
      <td class="num">${{money(e.amount)}}</td></tr>`).join('')}}</table>`
    : '<div class="empty">Nothing flagged</div>';

  const m = msgs || [];
  document.getElementById('msgn').textContent = m.length ? m.length + ' sent' : '';
  document.getElementById('messages').innerHTML = m.length ? m.slice(-8).reverse().map(x=>`
    <div class="msg"><span class="who">${{esc(x.to)||'—'}}</span>
      <span class="txt">${{esc(String(x.text||'').split('\\n')[0])}}</span></div>`).join('')
    : '<div class="empty">Nothing sent yet</div>';

  const runs = (ft && ft.runs) || [];
  document.getElementById('finetune').innerHTML = runs.length ? (r => `
    <div class="ba">
      <div class="col"><div class="lb">Before</div><div class="big">${{Math.round((r.metric_before||0)*100)}}%</div></div>
      <div class="arrow">→</div>
      <div class="col after"><div class="lb">After</div><div class="big">${{Math.round((r.metric_after||0)*100)}}%</div></div>
    </div>
    <div class="note">${{r.label_count||0}} human labels from the Terac panel, fine-tuned on
      ${{esc(r.base_model||'')}} via Pioneer. Same fixed test batch, scored before and after.</div>`)(runs[0])
    : `<div class="empty">Fine-tune pending — ${{(ft&&ft.labels_collected)||0}} labels collected so far</div>`;

  if (sel) loadInvoice(sel);
}}

async function loadInvoice(id){{
  const d = await j('/po1/invoices/' + id);
  if (!d || d.error) return;

  const room = d.room || [];
  document.getElementById('roomn').textContent = room.length ? room.length + ' messages' : '';
  document.getElementById('room').innerHTML = room.length ? room.map(p => {{
    const f = p.finding || {{}};
    const cls = p.agent==='human_reviewer' ? 'human' : (p.agent==='orchestrator' ? 'sys' : '');
    return `<div class="msg ${{cls}}"><span class="who">${{esc(p.agent)}}</span>
      <span class="txt">${{esc(f.detail || JSON.stringify(f).slice(0,150))}}</span></div>`;
  }}).join('') : '<div class="empty">No room activity for this invoice</div>';

  const order = ['vendor_onboarder','invoice_parser','three_way_matcher','duplicate_detector',
    'fraud_signal','gl_coder','exception_classifier','risk_scorer','approval_router',
    'terac_escalation','human_reviewer','payment_scheduler'];
  const byAgent = {{}}; room.forEach(p => byAgent[p.agent] = p.finding || {{}});
  const done = order.filter(a => byAgent[a]);
  document.getElementById('stepn').textContent = done.length + '/10 agents';
  document.getElementById('steps').innerHTML = done.length ? done.map(a => {{
    const f = byAgent[a];
    const cls = a==='human_reviewer' ? 'hold' : 'ok';
    return `<div class="step ${{cls}}"><span class="i"></span>
      <span class="nm">${{esc(a)}}</span>
      <span class="dt">${{esc(f.detail || f.result || '')}}</span></div>`;
  }}).join('') : '<div class="empty">Pipeline has not run for this invoice</div>';
}}

function pick(id){{ sel = id; tick(); }}
tick(); setInterval(tick, 2500);
</script></body></html>"""
