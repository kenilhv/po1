/**
 * End-to-end WebSocket tests — mirrors the frontend upload flow.
 */
import fs from 'fs';
import { execSync } from 'child_process';

const BASE = 'http://localhost:8000/v1';
const WS_BASE = 'ws://localhost:8000/v1/ws';
const H = { 'ngrok-skip-browser-warning': 'true' };
const PY = '/Users/apple/Desktop/Frontend_nice/backend/.venv/bin/python3';

let passed = 0;
let failed = 0;

function ok(name, detail = '') {
  console.log(`PASS — ${name}${detail ? ` (${detail})` : ''}`);
  passed++;
}
function fail(name, detail = '') {
  console.log(`FAIL — ${name}${detail ? ` (${detail})` : ''}`);
  failed++;
}

async function login() {
  const r = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { ...H, 'Content-Type': 'application/json' },
    body: JSON.stringify({ code: 'AP2024' }),
  });
  return (await r.json()).token;
}

function makePdf(name, text) {
  const dir = '/tmp/paycrew-e2e';
  fs.mkdirSync(dir, { recursive: true });
  const path = `${dir}/${name}.pdf`;
  execSync(
    `${PY} -c "import fitz; d=fitz.open(); p=d.new_page(); p.insert_text((72,72), '''${text.replace(/'/g, "\\'")}''', fontsize=11); d.save('${path}'); d.close()"`,
    { stdio: 'pipe' },
  );
  return path;
}

async function upload(token, pdfPath) {
  const buf = fs.readFileSync(pdfPath);
  const form = new FormData();
  form.append('file', new Blob([buf], { type: 'application/pdf' }), pdfPath.split('/').pop());
  const r = await fetch(`${BASE}/ap/invoices/upload`, {
    method: 'POST',
    headers: { ...H, Authorization: `Bearer ${token}` },
    body: form,
  });
  return r.json();
}

function wsTrace(token, jobId, { delayMs = 0 } = {}) {
  return new Promise((resolve, reject) => {
    const events = [];
    const t = setTimeout(() => {
      ws?.close();
      reject(new Error(`Timeout after ${delayMs}ms delay. Got: ${events.map((e) => e.type).join(' → ')}`));
    }, 20000);

    let ws;
    const connect = () => {
      ws = new WebSocket(`${WS_BASE}?token=${token}`);
      ws.onopen = () => ws.send(JSON.stringify({ jobId }));
      ws.onmessage = (m) => {
        const e = JSON.parse(m.data);
        events.push(e);
        if (e.type === 'job_complete' || e.type === 'job_failed') {
          clearTimeout(t);
          ws.close();
          resolve(events);
        }
      };
      ws.onerror = () => reject(new Error('WebSocket error'));
    };

    if (delayMs > 0) setTimeout(connect, delayMs);
    else connect();
  });
}

const token = await login();
if (!token) { console.log('FAIL — could not login'); process.exit(1); }
ok('Login');

// ── TEST 1: Immediate WS connect (frontend flow) ──
console.log('\n--- WS Test 1: Immediate connect ---');
const pdf1 = makePdf('ws-immediate', 'Vendor: PaperWorks Ltd\nInvoice Number: INV-2024-400\nAmount: $350\nPO Reference: PO-4412\nBank Account: ACC-004-VALID');
const up1 = await upload(token, pdf1);
if (!up1.jobId) { fail('Upload for WS immediate', JSON.stringify(up1)); }
else {
  try {
    const events = await wsTrace(token, up1.jobId);
    const starts = events.filter((e) => e.type === 'agent_start').length;
    const completes = events.filter((e) => e.type === 'agent_complete').length;
    const final = events.find((e) => e.type === 'job_complete');
    if (starts === 6 && completes === 6 && final?.invoice) {
      ok('Immediate WS — 6 agents + job_complete', `invoice risk=${final.invoice.risk}`);
    } else {
      fail('Immediate WS', `starts=${starts} completes=${completes} hasInvoice=${!!final?.invoice}`);
    }
  } catch (e) { fail('Immediate WS', e.message); }
}

// ── TEST 2: Late WS connect (replay after job done) ──
console.log('\n--- WS Test 2: Late connect (replay) ---');
const pdf2 = makePdf('ws-late', 'Vendor: TechSoftware Inc\nInvoice Number: INV-9921\nAmount: $1200\nPO Reference: PO-7743\nBank Account: ACC-002-VALID');
const up2 = await upload(token, pdf2);
if (!up2.jobId) { fail('Upload for WS late'); }
else {
  // Wait 2s so job definitely finishes before WS connects
  try {
    const events = await wsTrace(token, up2.jobId, { delayMs: 2000 });
    const completes = events.filter((e) => e.type === 'agent_complete').length;
    const final = events.find((e) => e.type === 'job_complete');
    if (completes === 6 && final?.invoice) {
      ok('Late WS replay — 6 agents + job_complete', `status=${final.invoice.status}`);
    } else {
      fail('Late WS replay', `completes=${completes} hasInvoice=${!!final?.invoice}`);
    }
  } catch (e) { fail('Late WS replay', e.message); }
}

// ── TEST 3: Polling fallback (job status includes invoice) ──
console.log('\n--- WS Test 3: Polling fallback ---');
const pdf3 = makePdf('ws-poll', 'Vendor: OfficeSupplyCo\nInvoice Number: INV-2024-441\nAmount: $800\nPO Reference: PO-8821\nBank Account: ACC-001-VALID');
const up3 = await upload(token, pdf3);
if (!up3.jobId) { fail('Upload for polling'); }
else {
  await new Promise((r) => setTimeout(r, 1500));
  const r = await fetch(`${BASE}/ap/invoices/jobs/${up3.jobId}`, {
    headers: { ...H, Authorization: `Bearer ${token}` },
  });
  const job = await r.json();
  if (job.status === 'complete' && job.invoice && job.invoice.agents?.length === 6) {
    ok('Polling fallback — invoice with 6 agents', `risk=${job.invoice.risk}`);
  } else {
    fail('Polling fallback', `status=${job.status} agents=${job.invoice?.agents?.length ?? 0}`);
  }
}

// ── TEST 4: Invalid WS token ──
console.log('\n--- WS Test 4: Invalid token ---');
await new Promise((resolve) => {
  let done = false;
  const finish = (pass, detail) => {
    if (done) return;
    done = true;
    if (pass) ok('Invalid WS token rejected', detail);
    else fail('Invalid WS token', detail);
    resolve();
  };
  const ws = new WebSocket(`${WS_BASE}?token=invalid-token-xyz`);
  ws.onclose = (ev) => finish(ev.code === 4001 || ev.code === 1006, `code=${ev.code}`);
  ws.onerror = () => finish(true, 'connection rejected');
  setTimeout(() => finish(false, 'no rejection within 3s'), 3000);
});

// ── TEST 5: CFO approve/reject flow ──
console.log('\n--- WS Test 5: CFO approve/reject ---');
const cfoToken = (await fetch(`${BASE}/auth/login`, {
  method: 'POST',
  headers: { ...H, 'Content-Type': 'application/json' },
  body: JSON.stringify({ code: 'CFO2024' }),
}).then((r) => r.json())).token;

const pending = await fetch(`${BASE}/cfo/pending-approvals`, {
  headers: { ...H, Authorization: `Bearer ${cfoToken}` },
}).then((r) => r.json());

const toApprove = pending.find((i) => i.risk === 'HIGH');
const toReject = pending.find((i) => i.risk === 'CRITICAL' && i.id !== toApprove?.id);

if (toApprove) {
  const ar = await fetch(`${BASE}/cfo/invoices/${toApprove.id}/approve`, {
    method: 'POST',
    headers: { ...H, Authorization: `Bearer ${cfoToken}` },
  });
  const approved = await ar.json();
  if (approved.status === 'approved') ok('CFO approve HIGH invoice', `id=${toApprove.id}`);
  else fail('CFO approve', JSON.stringify(approved));
} else {
  fail('CFO approve', 'no pending HIGH invoice');
}

if (toReject) {
  const rr = await fetch(`${BASE}/cfo/invoices/${toReject.id}/reject`, {
    method: 'POST',
    headers: { ...H, Authorization: `Bearer ${cfoToken}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason: 'E2E test rejection' }),
  });
  const rejected = await rr.json();
  if (rejected.status === 'rejected') ok('CFO reject CRITICAL invoice', `id=${toReject.id}`);
  else fail('CFO reject', JSON.stringify(rejected));
} else {
  fail('CFO reject', 'no pending CRITICAL invoice');
}

console.log(`\n========== E2E SUMMARY ==========`);
console.log(`PASS: ${passed}  FAIL: ${failed}`);
process.exit(failed ? 1 : 0);
