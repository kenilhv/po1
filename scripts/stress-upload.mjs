import fs from 'fs';
import { execSync } from 'child_process';

const BASE = 'http://localhost:8000/v1';
const WS_BASE = 'ws://localhost:8000/v1/ws';
const H = { 'ngrok-skip-browser-warning': 'true' };

function makePdf(name, text) {
  const dir = '/tmp/paycrew-test';
  fs.mkdirSync(dir, { recursive: true });
  const path = `${dir}/${name}.pdf`;
  execSync(
    `/Users/apple/Desktop/Frontend_nice/backend/.venv/bin/python3 -c "
import fitz
doc = fitz.open()
page = doc.new_page()
page.insert_text((72, 72), '''${text.replace(/'/g, "\\'")}''', fontsize=11)
doc.save('${path}')
doc.close()
"`,
    { stdio: 'pipe' },
  );
  return path;
}

async function login(code) {
  const r = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { ...H, 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  });
  return r.json();
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
  return { status: r.status, body: await r.json() };
}

function traceJob(token, jobId) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(`${WS_BASE}?token=${token}`);
    const events = [];
    const t = setTimeout(() => {
      ws.close();
      reject(new Error(`Timeout. Events: ${events.map((e) => e.type).join(' -> ')}`));
    }, 15000);

    ws.onopen = () => ws.send(JSON.stringify({ jobId }));
    ws.onmessage = (m) => {
      const e = JSON.parse(m.data);
      events.push(e);
      if (e.type === 'job_complete') {
        clearTimeout(t);
        ws.close();
        resolve({ events, invoice: e.invoice });
      }
      if (e.type === 'job_failed') {
        clearTimeout(t);
        ws.close();
        reject(new Error(e.error || 'failed'));
      }
    };
    ws.onerror = () => reject(new Error('ws error'));
  });
}

async function jobPoll(token, jobId) {
  const r = await fetch(`${BASE}/ap/invoices/jobs/${jobId}`, {
    headers: { ...H, Authorization: `Bearer ${token}` },
  });
  return r.json();
}

const scenarios = [
  {
    name: 'clean-auto-approve',
    text: 'Vendor: CleanVendor Inc\\nInvoice Number: INV-2024-300\\nAmount: $500\\nPO Reference: PO-9901\\nBank Account: ACC-003-VALID',
    expect: { risk: 'LOW', decision: 'AUTO_APPROVED', agents: 6 },
  },
  {
    name: 'empty-pdf',
    text: '',
    expect: { risk: 'CRITICAL', decision: 'BLOCKED', agents: 6 },
  },
  {
    name: 'fraud-vendor',
    text: 'Vendor: FastConsult LLC\\nInvoice Number: INV-F-0042\\nAmount: $45000\\nBank Account: ACC-999-SUSPICIOUS',
    expect: { risk: 'CRITICAL', decision: 'BLOCKED', agents: 6 },
  },
];

const { token } = await login('AP2024');
let passed = 0;
let failed = 0;

for (const s of scenarios) {
  process.stdout.write(`\n=== ${s.name} ===\n`);
  const pdf = makePdf(s.name, s.text);
  const up = await upload(token, pdf);
  if (!up.body.jobId) {
    console.log('FAIL upload', up);
    failed++;
    continue;
  }

  let invoice;
  try {
    const { events, invoice: inv } = await traceJob(token, up.body.jobId);
    invoice = inv;
    const agentCompletes = events.filter((e) => e.type === 'agent_complete').length;
    console.log(`  WS events: ${events.length}, agent_complete: ${agentCompletes}`);
    if (agentCompletes < 6) {
      console.log('  FAIL: expected 6 agent_complete events');
      failed++;
      continue;
    }
  } catch (err) {
    console.log('  WS failed:', err.message);
    const poll = await jobPoll(token, up.body.jobId);
    if (!poll.invoice) {
      console.log('  FAIL poll missing invoice', poll);
      failed++;
      continue;
    }
    invoice = poll.invoice;
    console.log('  Poll fallback OK');
  }

  const poll = await jobPoll(token, up.body.jobId);
  if (!poll.invoice) {
    console.log('  FAIL job poll has no invoice');
    failed++;
    continue;
  }

  const risk = (invoice.risk || '').toUpperCase();
  const decision = (invoice.decision || poll.invoice.decision || '').toUpperCase();
  const status = invoice.status;
  const agents = invoice.agents?.length || 0;

  console.log(`  risk=${risk} decision=${decision} status=${status} agents=${agents} amount=${invoice.amount}`);

  const ok =
    risk === s.expect.risk &&
    (decision === s.expect.decision || status.includes(s.expect.decision.toLowerCase())) &&
    agents >= s.expect.agents;

  if (ok) {
    console.log('  PASS');
    passed++;
  } else {
    console.log(`  FAIL expected risk=${s.expect.risk} decision=${s.expect.decision}`);
    failed++;
  }
}

console.log(`\n${passed}/${passed + failed} scenarios passed`);
process.exit(failed ? 1 : 0);
