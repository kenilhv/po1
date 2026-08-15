// Full upload -> WS trace -> final decision flow, per PDF. Then approve/reject checks.
import fs from 'fs';
import path from 'path';

const BASE = 'http://localhost:8000/v1';
const WS_BASE = 'ws://localhost:8000/v1/ws';
const PDF_DIR = '/tmp/paycrew_pdfs';
const H = { 'ngrok-skip-browser-warning': 'true' };

const log = (...a) => console.log(...a);
const j = (r) => r.json();

async function loginAs(code) {
  const r = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { ...H, 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  });
  return (await j(r)).token;
}

function runTrace(token, jobId, timeoutMs = 15000) {
  return new Promise((resolve) => {
    const ws = new WebSocket(`${WS_BASE}?token=${token}`);
    const events = [];
    let done = false;
    const finish = (status) => {
      if (done) return;
      done = true;
      clearTimeout(t);
      try { ws.close(); } catch {}
      resolve({ status, events });
    };
    const t = setTimeout(() => finish('TIMEOUT'), timeoutMs);
    ws.onopen = () => ws.send(JSON.stringify({ jobId }));
    ws.onmessage = (m) => {
      const e = JSON.parse(m.data);
      events.push(e);
      if (e.type === 'job_complete') finish('complete');
      if (e.type === 'job_failed') finish('failed');
    };
    ws.onerror = () => finish('ws_error');
  });
}

async function uploadAndTrace(token, file) {
  const buf = fs.readFileSync(path.join(PDF_DIR, file));
  const form = new FormData();
  form.append('file', new Blob([buf], { type: 'application/pdf' }), file);
  const res = await fetch(`${BASE}/ap/invoices/upload`, {
    method: 'POST',
    headers: { ...H, Authorization: `Bearer ${token}` },
    body: form,
  });
  const body = await j(res);
  if (res.status !== 200 || !body.jobId) {
    return { file, uploadStatus: res.status, body, trace: null };
  }
  const trace = await runTrace(token, body.jobId);
  return { file, uploadStatus: res.status, body, trace };
}

function summarize(r) {
  log(`\n=== ${r.file} ===`);
  log(`  upload: ${r.uploadStatus} ${JSON.stringify(r.body)}`);
  if (!r.trace) { log('  (no trace — upload rejected)'); return; }
  const { status, events } = r.trace;
  const agentCompletes = events.filter((e) => e.type === 'agent_complete');
  log(`  trace status: ${status} | events: ${events.length} | agent_completes: ${agentCompletes.length}/6`);
  for (const e of agentCompletes) {
    log(`    - ${String(e.agent).padEnd(20)} status=${e.status} result="${e.result}" conf=${e.confidence ?? '-'} model=${e.model || '-'}`);
  }
  const jc = events.find((e) => e.type === 'job_complete');
  const jf = events.find((e) => e.type === 'job_failed');
  if (jc) {
    const inv = jc.invoice;
    log(`  FINAL: vendor="${inv.vendor}" number="${inv.number}" amount=${inv.amount} risk=${inv.risk} status=${inv.status}`);
  }
  if (jf) log(`  FAILED: ${jf.error}`);
  // sanity flags
  const missing = 6 - agentCompletes.length;
  if (status === 'TIMEOUT') log('  *** TIMEOUT — frontend would hang ***');
  if (missing > 0 && status === 'complete') log(`  *** ${missing} agent(s) never completed ***`);
}

async function main() {
  const apToken = await loginAs('AP2024');
  log('AP token:', !!apToken);

  const files = fs.readdirSync(PDF_DIR).filter((f) => f.endsWith('.pdf')).sort();
  const results = [];
  for (const f of files) {
    results.push(await uploadAndTrace(apToken, f));
  }
  results.forEach(summarize);

  // Check resulting invoice list for duplicate numbers / blank vendors
  log('\n========== POST-UPLOAD INVOICE LIST CHECK ==========');
  const invs = await fetch(`${BASE}/ap/invoices`, { headers: { ...H, Authorization: `Bearer ${apToken}` } }).then(j);
  const numbers = invs.map((i) => i.number);
  const dupNums = numbers.filter((n, i) => numbers.indexOf(n) !== i);
  const blankVendors = invs.filter((i) => !i.vendor || !i.vendor.trim());
  log(`  total invoices: ${invs.length}`);
  log(`  duplicate numbers: ${dupNums.length ? [...new Set(dupNums)].join(', ') : 'none'}`);
  log(`  blank-vendor invoices: ${blankVendors.length}`, blankVendors.map((i) => `${i.number}(id ${i.id})`).join(', '));

  // CFO approve/reject flow on a pending invoice
  log('\n========== CFO APPROVE / REJECT CHECK ==========');
  const cfoToken = await loginAs('CFO2024');
  const pending = await fetch(`${BASE}/cfo/pending-approvals`, { headers: { ...H, Authorization: `Bearer ${cfoToken}` } }).then(j).catch(() => null);
  log('  pending-approvals raw:', JSON.stringify(pending).slice(0, 300));
}

main().catch((e) => { console.error('FATAL', e); process.exit(1); });
