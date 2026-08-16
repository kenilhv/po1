"""PO1 — the ledger floor.

One server-rendered page, no build step, served by the same process as the
API. Designed as an operations ledger rather than a SaaS dashboard: footed
totals, tabular numerals, rubber-stamp statuses — the artifacts of accounts
payable itself. All data arrives client-side from the existing endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PO1 — The Ledger Floor</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:ital,wght@0,500;0,600;1,500&display=swap" rel="stylesheet">
<style>
:root{
  --ground:#101613; --panel:#151D18; --panel2:#19231D;
  --rule:#2A382F; --rule-soft:#202B24;
  --ink:#E9E4D4; --dim:#98A498; --faint:#5F6C60;
  --brass:#D9A441; --settle:#63C384; --carbon:#E4685F; --wire:#7FA8C9;
  --serif:"IBM Plex Serif",Georgia,serif;
  --mono:"IBM Plex Mono",Consolas,ui-monospace,monospace;
  --sans:"IBM Plex Sans",-apple-system,"Segoe UI",sans-serif;
}
*{box-sizing:border-box}
html{background:var(--ground)}
body{margin:0;background:var(--ground);color:var(--ink);font:14px/1.5 var(--sans)}
::selection{background:var(--brass);color:#141414}

/* ---------- masthead ---------- */
.mast{display:flex;align-items:baseline;gap:18px;flex-wrap:wrap;
  padding:20px 26px 16px;border-bottom:1px solid var(--rule);
  position:sticky;top:0;background:var(--ground);z-index:20}
.wordmark{font:600 26px/1 var(--serif);letter-spacing:-.01em}
.wordmark i{font-style:italic;color:var(--brass)}
.mast .dept{font:500 11px/1 var(--mono);letter-spacing:.22em;text-transform:uppercase;color:var(--dim)}
.lamps{margin-left:auto;display:flex;gap:14px;flex-wrap:wrap}
.lamp{display:flex;align-items:center;gap:6px;font:500 10px/1 var(--mono);
  letter-spacing:.12em;text-transform:uppercase;color:var(--faint)}
.lamp em{width:8px;height:8px;border-radius:1px;background:var(--faint);
  box-shadow:inset 0 0 0 1px rgba(0,0,0,.4);font-style:normal}
.lamp.on{color:var(--dim)}
.lamp.on em{background:var(--settle);box-shadow:0 0 6px rgba(99,195,132,.55)}

/* ---------- footed totals ---------- */
.footing{display:grid;grid-template-columns:repeat(5,1fr);gap:0;
  margin:22px 26px 20px;border-top:1px solid var(--rule)}
@media(max-width:900px){.footing{grid-template-columns:repeat(2,1fr)}}
.foot{padding:14px 16px 12px;border-right:1px solid var(--rule-soft)}
.foot:last-child{border-right:0}
.foot .lbl{font:500 10px/1.4 var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--faint)}
.foot .sum{font:600 30px/1.15 var(--mono);font-variant-numeric:tabular-nums;
  letter-spacing:-.02em;margin-top:6px;
  border-bottom:3px double var(--rule);display:inline-block;padding-bottom:4px}
.foot .sub{font:12px/1.4 var(--sans);color:var(--dim);margin-top:5px}
.foot.settle .sum{color:var(--settle)}
.foot.carbon .sum{color:var(--carbon)}
.foot.brass .sum{color:var(--brass)}

/* ---------- layout ---------- */
.floor{display:grid;grid-template-columns:minmax(0,7fr) minmax(0,5fr);
  gap:0 26px;padding:0 26px 80px;max-width:1560px;margin:0 auto}
@media(max-width:1080px){.floor{grid-template-columns:1fr}}
section{margin-bottom:26px}
.sec-h{display:flex;align-items:baseline;gap:12px;
  border-bottom:1px solid var(--rule);padding-bottom:8px;margin-bottom:0}
.sec-h h2{margin:0;font:600 15px/1.2 var(--serif);letter-spacing:.01em}
.sec-h .cnt{font:500 11px/1 var(--mono);color:var(--faint);letter-spacing:.08em}
.sec-h .act{margin-left:auto}

/* ---------- the ledger ---------- */
.ledger{width:100%;border-collapse:collapse;font:13px/1.45 var(--mono)}
.ledger th{font:500 10px/1.4 var(--mono);letter-spacing:.14em;text-transform:uppercase;
  color:var(--faint);text-align:left;padding:10px 10px 8px;border-bottom:1px solid var(--rule)}
.ledger th.r{text-align:right}
.ledger td{padding:11px 10px;border-bottom:1px solid var(--rule-soft);
  vertical-align:middle;font-variant-numeric:tabular-nums}
.ledger td.r{text-align:right}
.ledger tr.line{cursor:pointer}
.ledger tr.line:hover td{background:var(--panel)}
.ledger tr.line.sel td{background:var(--panel2);box-shadow:inset 3px 0 0 var(--brass)}
.ledger .vendor{font:500 13.5px/1.3 var(--sans);color:var(--ink)}
.ledger .meta{font:11px/1.4 var(--mono);color:var(--faint)}
.ledger .exc{font:11px/1.3 var(--mono);color:var(--carbon)}
.ledger .exc.none{color:var(--faint)}

/* the stamp — PO1's signature mark */
.stamp{display:inline-block;font:600 10px/1 var(--mono);letter-spacing:.14em;
  padding:5px 8px 4px;border:2px solid currentColor;border-radius:3px;
  transform:rotate(-5deg);text-transform:uppercase;white-space:nowrap;
  opacity:.92;mask-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='60' height='24'%3E%3Crect width='60' height='24' fill='white'/%3E%3C/svg%3E")}
.stamp.paid{color:var(--settle)}
.stamp.blocked{color:var(--carbon)}
.stamp.held{color:var(--brass)}
.stamp.run{color:var(--wire);transform:rotate(0);border-style:dashed;animation:tick 1.2s ease-in-out infinite}
@keyframes tick{50%{opacity:.45}}
@media(prefers-reduced-motion:reduce){.stamp.run{animation:none}}
tr.line .stamp{animation:thunk .18s ease-out 1}
@keyframes thunk{from{transform:rotate(-5deg) scale(1.25);opacity:.2}}
@media(prefers-reduced-motion:reduce){tr.line .stamp{animation:none}}

/* ---------- right rail panels ---------- */
.panel{border:1px solid var(--rule-soft);background:var(--panel);margin-top:14px}
.panel .bd{max-height:340px;overflow-y:auto}
.feed{list-style:none;margin:0;padding:0}
.feed li{display:flex;gap:12px;padding:9px 14px;border-bottom:1px solid var(--rule-soft);
  font:12.5px/1.5 var(--sans)}
.feed li:last-child{border-bottom:0}
.feed .who{font:500 11px/1.6 var(--mono);color:var(--brass);min-width:138px;flex-shrink:0}
.feed li.human{background:rgba(99,195,132,.07)}
.feed li.human .who{color:var(--settle)}
.feed li.orch .who{color:var(--wire)}
.feed .what{color:var(--dim)}
.feed .what b{color:var(--ink);font-weight:500}

.trace{list-style:none;margin:0;padding:0;counter-reset:step}
.trace li{display:flex;gap:10px;padding:8px 14px;border-bottom:1px solid var(--rule-soft);
  font:12px/1.5 var(--mono)}
.trace li:last-child{border-bottom:0}
.trace .tick{color:var(--settle);flex-shrink:0}
.trace li.hold .tick{color:var(--brass)}
.trace .nm{min-width:150px;color:var(--ink);flex-shrink:0}
.trace .dt{color:var(--dim);font-family:var(--sans);font-size:12.5px}

/* carbon-copy exception slips */
.slips{display:flex;flex-direction:column;gap:10px;padding:12px 14px}
.slip{border:1px solid var(--carbon);border-left-width:4px;padding:10px 12px;
  background:rgba(228,104,95,.05)}
.slip .t{display:flex;justify-content:space-between;gap:10px;
  font:500 12.5px/1.4 var(--sans)}
.slip .t b{font-variant-numeric:tabular-nums;font-family:var(--mono);font-weight:600}
.slip .m{font:11px/1.5 var(--mono);color:var(--dim);margin-top:3px}
.slip .m u{color:var(--carbon);text-decoration:none}

/* human input ledger */
.ba{display:flex;align-items:center;justify-content:center;gap:22px;padding:18px 14px}
.ba .col{text-align:center}
.ba .lbl{font:500 10px/1.4 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--faint)}
.ba .big{font:600 30px/1.2 var(--mono);font-variant-numeric:tabular-nums;margin-top:4px}
.ba .to{color:var(--brass);font-size:20px}
.ba .after .big{color:var(--settle)}
.panel .note{padding:10px 14px;border-top:1px solid var(--rule-soft);
  font:12px/1.5 var(--sans);color:var(--dim)}

/* wires (messages) */
.wires{list-style:none;margin:0;padding:0}
.wires li{padding:9px 14px;border-bottom:1px solid var(--rule-soft)}
.wires li:last-child{border-bottom:0}
.wires .to{font:500 11px/1.5 var(--mono);color:var(--wire)}
.wires .tx{font:12.5px/1.5 var(--sans);color:var(--dim)}

/* ---------- empty state / intake ---------- */
.quiet{padding:44px 20px;text-align:center}
.quiet h3{margin:0 0 6px;font:italic 500 20px/1.3 var(--serif);color:var(--ink)}
.quiet p{margin:0 0 18px;font:13px/1.5 var(--sans);color:var(--dim)}
button.intake{font:600 12px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase;
  color:#141414;background:var(--brass);border:0;border-radius:2px;
  padding:12px 20px;cursor:pointer}
button.intake:hover{filter:brightness(1.08)}
button.intake:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
button.intake[disabled]{opacity:.55;cursor:wait}
.sec-h button.intake{padding:7px 12px;font-size:10px}
.mini-quiet{padding:22px 14px;text-align:center;font:12.5px/1.5 var(--sans);color:var(--faint)}

.colophon{padding:26px;text-align:center;font:500 10px/1.8 var(--mono);
  letter-spacing:.18em;text-transform:uppercase;color:var(--faint)}
</style></head><body>

<header class="mast">
  <div class="wordmark">PO<i>1</i></div>
  <div class="dept">Autonomous Accounts Payable — The Ledger Floor</div>
  <div class="lamps" id="lamps" aria-label="Integration status"></div>
</header>

<div class="footing" id="footing"></div>

<main class="floor">
  <div>
    <section aria-label="Invoice ledger">
      <div class="sec-h">
        <h2>Day ledger</h2><span class="cnt" id="led-cnt"></span>
        <span class="act"><button class="intake" id="intake2" onclick="intake(this)" hidden>Run intake</button></span>
      </div>
      <div id="ledger"></div>
    </section>

    <section aria-label="Agent floor">
      <div class="sec-h"><h2>Agent floor <span style="font:500 10px/1 var(--mono);letter-spacing:.12em;color:var(--faint)">· BAND ROOM</span></h2><span class="cnt" id="room-cnt"></span></div>
      <div class="panel"><div class="bd"><ul class="feed" id="room"><li class="mini-quiet" style="display:block">Select a ledger line to open its thread</li></ul></div></div>
    </section>
  </div>

  <div>
    <section aria-label="Pipeline trace">
      <div class="sec-h"><h2>Processing trace</h2><span class="cnt" id="trace-cnt"></span></div>
      <div class="panel"><div class="bd"><ul class="trace" id="trace"><li class="mini-quiet" style="display:block">Select a ledger line</li></ul></div></div>
    </section>

    <section aria-label="Exceptions">
      <div class="sec-h"><h2>Exception slips</h2><span class="cnt" id="exc-cnt"></span></div>
      <div class="panel"><div class="bd" id="slips"><div class="mini-quiet">Nothing flagged</div></div></div>
    </section>

    <section aria-label="Human input">
      <div class="sec-h"><h2>Human judgment → model</h2></div>
      <div class="panel" id="finetune"><div class="mini-quiet">No fine-tune run yet</div></div>
    </section>

    <section aria-label="Messages">
      <div class="sec-h"><h2>Wires sent</h2><span class="cnt" id="wire-cnt"></span></div>
      <div class="panel"><div class="bd"><ul class="wires" id="wires"><li class="mini-quiet" style="display:block">Nothing sent yet</li></ul></div></div>
    </section>
  </div>
</main>

<footer class="colophon">PO1 · The finance hire a startup never makes · settled autonomously · zero-human company hackathon</footer>

<script>
let sel=null;
const $=id=>document.getElementById(id);
const esc=s=>String(s==null?"":s).replace(/[<>&]/g,c=>({"<":"&lt;",">":"&gt;","&":"&amp;"}[c]));
const usd=n=>"$"+Number(n||0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
async function j(u,opt){try{const r=await fetch(u,opt);return await r.json()}catch(e){return null}}

function stampFor(inv){
  const d=String(inv.decision||inv.status||"").toUpperCase();
  if(d==="PAID")return '<span class="stamp paid">Paid</span>';
  if(d==="AUTO_APPROVED")return '<span class="stamp paid">Cleared</span>';
  if(d==="BLOCKED")return '<span class="stamp blocked">Blocked</span>';
  if(d==="REJECTED")return '<span class="stamp blocked">Rejected</span>';
  if(d==="PENDING_TERAC")return '<span class="stamp held">To expert</span>';
  if(d==="PENDING_FOUNDER")return '<span class="stamp held">To founder</span>';
  if(d==="SCHEDULED")return '<span class="stamp held">Scheduled</span>';
  return '<span class="stamp run">Working</span>';
}

async function intake(btn){
  if(btn){btn.disabled=true;btn.textContent="Running…"}
  await j("/po1/demo",{method:"POST"});
  setTimeout(tick,1200);
  if(btn)setTimeout(()=>{btn.disabled=false;btn.textContent="Run intake"},4000);
}

async function tick(){
  const [health,invs,rev,excs,msgs,ft]=await Promise.all([
    j("/health"),j("/po1/invoices"),j("/po1/revenue"),j("/po1/exceptions"),j("/po1/messages"),j("/po1/finetune")]);

  if(health)$("lamps").innerHTML=["terac","band","linq","stripe","pioneer"]
    .map(k=>`<span class="lamp ${health[k]?"on":""}"><em></em>${k}</span>`).join("");

  const list=invs||[];
  const paid=list.filter(i=>["PAID","AUTO_APPROVED"].includes(String(i.status||i.decision||"").toUpperCase()));
  const held=list.filter(i=>["BLOCKED","PENDING_TERAC","PENDING_FOUNDER"].includes(String(i.decision||"").toUpperCase()));
  const paidT=paid.reduce((s,i)=>s+Number(i.amount||0),0);
  const heldT=held.reduce((s,i)=>s+Number(i.amount||0),0);
  const revT=(rev&&rev.internal&&rev.internal.total)||0;
  const stripeT=(rev&&rev.stripe&&rev.stripe.total)||0;

  $("footing").innerHTML=`
    <div class="foot"><div class="lbl">Invoices processed</div><div class="sum">${list.length}</div>
      <div class="sub">${paid.length} settled autonomously</div></div>
    <div class="foot settle"><div class="lbl">Settled, no human</div><div class="sum">${usd(paidT)}</div>
      <div class="sub">${list.length?Math.round(paid.length/list.length*100):0}% of volume</div></div>
    <div class="foot carbon"><div class="lbl">Held for judgment</div><div class="sum">${usd(heldT)}</div>
      <div class="sub">${held.length} stopped by control</div></div>
    <div class="foot brass"><div class="lbl">PO1 revenue</div><div class="sum">${usd(revT)}</div>
      <div class="sub">Stripe confirms ${usd(stripeT)}</div></div>
    <div class="foot"><div class="lbl">Human labels</div><div class="sum">${(ft&&ft.labels_collected)||0}</div>
      <div class="sub">via Terac panel</div></div>`;

  $("led-cnt").textContent=list.length?list.length+" lines":"";
  $("intake2").hidden=!list.length;
  if(list.length){
    $("ledger").innerHTML=`<table class="ledger">
      <thead><tr><th>Payee</th><th>Coding</th><th>Exception</th><th class="r">Amount</th><th class="r">Disposition</th></tr></thead>
      <tbody>${list.map(i=>`
        <tr class="line ${sel===i.id?"sel":""}" onclick="pick(${i.id})" tabindex="0" onkeydown="if(event.key==='Enter')pick(${i.id})">
          <td><div class="vendor">${esc(i.vendor_name)||"Parsing…"}</div>
              <div class="meta">${esc(i.invoice_number)||"—"}</div></td>
          <td class="meta">${esc(i.gl_code)||"—"} ${esc(i.cost_center)||""}</td>
          <td class="exc ${i.exception_type&&i.exception_type!=="clean"?"":"none"}">${
            i.exception_type&&i.exception_type!=="clean"
              ?esc(i.exception_type).replace(/_/g," ")+(i.owner&&i.owner!=="none"?" → "+esc(i.owner):"")
              :"—"}</td>
          <td class="r">${usd(i.amount)}</td>
          <td class="r">${stampFor(i)}</td>
        </tr>`).join("")}</tbody></table>`;
  }else{
    $("ledger").innerHTML=`<div class="quiet">
      <h3>The floor is quiet.</h3>
      <p>No invoices in today's ledger yet. Run the day's intake to put four real invoices through all ten agents.</p>
      <button class="intake" onclick="intake(this)">Run the day's intake</button></div>`;
  }

  const ex=excs||[];
  $("exc-cnt").textContent=ex.length?ex.length+" open":"";
  $("slips").innerHTML=ex.length?`<div class="slips">${ex.slice(0,10).map(e=>`
    <div class="slip"><div class="t"><span>${esc(e.vendor_name)}</span><b>${usd(e.amount)}</b></div>
      <div class="m"><u>${esc(e.exception_type).replace(/_/g," ")}</u> · severity ${esc(e.severity)} · owner ${esc(e.owner)}</div>
    </div>`).join("")}</div>`:'<div class="mini-quiet">Nothing flagged</div>';

  const m=msgs||[];
  $("wire-cnt").textContent=m.length?m.length+" sent":"";
  if(m.length)$("wires").innerHTML=m.slice(-8).reverse().map(x=>`
    <li><div class="to">${esc(x.to)||"—"}</div>
        <div class="tx">${esc(String(x.text||"").split("\\n")[0])}</div></li>`).join("");

  const runs=(ft&&ft.runs)||[];
  $("finetune").innerHTML=runs.length?(r=>`
    <div class="ba">
      <div class="col"><div class="lbl">Before</div><div class="big">${Math.round((r.metric_before||0)*100)}%</div></div>
      <div class="to">→</div>
      <div class="col after"><div class="lbl">After</div><div class="big">${Math.round((r.metric_after||0)*100)}%</div></div>
    </div>
    <div class="note">${r.label_count||0} human labels from the Terac panel, fine-tuned on ${esc(r.base_model||"")} via Pioneer — same fixed batch, scored twice.</div>`)(runs[0])
    :`<div class="mini-quiet">Fine-tune pending — ${(ft&&ft.labels_collected)||0} labels banked. The loop fires when the panel's labels land.</div>`;

  if(sel)loadLine(sel);
}

async function loadLine(id){
  const d=await j("/po1/invoices/"+id);
  if(!d||d.error)return;
  const room=d.room||[];
  $("room-cnt").textContent=room.length?room.length+" messages":"";
  if(room.length)$("room").innerHTML=room.map(p=>{
    const f=p.finding||{};
    const cls=p.agent==="human_reviewer"?"human":(p.agent==="orchestrator"?"orch":"");
    return `<li class="${cls}"><span class="who">${esc(p.agent)}</span>
      <span class="what">${esc(f.detail||JSON.stringify(f).slice(0,140))}</span></li>`;}).join("");

  const order=["vendor_onboarder","invoice_parser","three_way_matcher","duplicate_detector",
    "fraud_signal","gl_coder","exception_classifier","risk_scorer","approval_router",
    "terac_escalation","human_reviewer","payment_scheduler"];
  const by={};room.forEach(p=>by[p.agent]=p.finding||{});
  const done=order.filter(a=>by[a]);
  $("trace-cnt").textContent=done.length?done.length+" steps":"";
  if(done.length)$("trace").innerHTML=done.map(a=>`
    <li class="${a==="human_reviewer"?"hold":""}"><span class="tick">●</span>
      <span class="nm">${esc(a)}</span>
      <span class="dt">${esc(by[a].detail||by[a].result||"")}</span></li>`).join("");
}

function pick(id){sel=id;tick()}
tick();setInterval(tick,2500);
</script></body></html>"""


@router.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return PAGE
