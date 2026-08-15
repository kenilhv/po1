#!/usr/bin/env node
/**
 * PayCrew backend endpoint test suite
 * Run: node scripts/test-api.mjs
 */

const BASE = 'http://localhost:8000/v1';
const WS_BASE = 'ws://localhost:8000/v1/ws';
const HEADERS = {
  'Content-Type': 'application/json',
  'ngrok-skip-browser-warning': 'true',
};

const results = [];

function record(num, name, pass, detail = '') {
  results.push({ num, name, pass, detail });
  const icon = pass ? 'PASS' : 'FAIL';
  console.log(`TEST ${num}: ${icon} — ${name}${detail ? `\n       ${detail}` : ''}`);
}

async function jsonFetch(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: { ...HEADERS, ...options.headers },
  });
  const text = await res.text();
  let body;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text.slice(0, 200);
  }
  return { res, body };
}

async function runTests() {
  let AP_TOKEN = '';
  let CFO_TOKEN = '';
  let TEST_JOB_ID = '';
  let pendingHighId = null;
  let pendingCriticalId = null;

  // TEST 1
  try {
    const { res, body } = await jsonFetch(`${BASE}/auth/login`, {
      method: 'POST',
      body: JSON.stringify({ code: 'AP2024' }),
    });
    if (res.ok && body.token && body.role === 'ap') {
      AP_TOKEN = body.token;
      record(1, 'Login with AP code', true);
    } else {
      record(1, 'Login with AP code', false, `${res.status} ${JSON.stringify(body)}`);
    }
  } catch (e) {
    record(1, 'Login with AP code', false, e.message);
  }

  // TEST 2
  try {
    const { res, body } = await jsonFetch(`${BASE}/auth/login`, {
      method: 'POST',
      body: JSON.stringify({ code: 'CFO2024' }),
    });
    if (res.ok && body.token && body.role === 'cfo') {
      CFO_TOKEN = body.token;
      record(2, 'Login with CFO code', true);
    } else {
      record(2, 'Login with CFO code', false, `${res.status} ${JSON.stringify(body)}`);
    }
  } catch (e) {
    record(2, 'Login with CFO code', false, e.message);
  }

  // TEST 3
  try {
    const { res, body } = await jsonFetch(`${BASE}/auth/login`, {
      method: 'POST',
      body: JSON.stringify({ code: 'WRONG' }),
    });
    const ok = res.status === 401 && (body.detail === 'Invalid code' || body.message?.includes('Invalid'));
    record(3, 'Login with wrong code', ok, ok ? '' : `${res.status} ${JSON.stringify(body)}`);
  } catch (e) {
    record(3, 'Login with wrong code', false, e.message);
  }

  // TEST 4
  try {
    const { res, body } = await jsonFetch(`${BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${AP_TOKEN}` },
    });
    record(4, 'Auth me with AP token', res.ok && body.role === 'ap', res.ok ? '' : `${res.status} ${JSON.stringify(body)}`);
  } catch (e) {
    record(4, 'Auth me with AP token', false, e.message);
  }

  // TEST 5
  try {
    const { res } = await jsonFetch(`${BASE}/auth/me`);
    record(5, 'Auth me with no token', res.status === 401, `status ${res.status}`);
  } catch (e) {
    record(5, 'Auth me with no token', false, e.message);
  }

  const auth = (token) => ({ Authorization: `Bearer ${token}` });

  // TEST 6
  try {
    const { res, body } = await jsonFetch(`${BASE}/ap/stats`, { headers: auth(AP_TOKEN) });
    const ok = res.ok && typeof body.total === 'number' && typeof body.autoApproved === 'number';
    record(6, 'AP Stats', ok, ok ? '' : `${res.status} ${JSON.stringify(body)}`);
  } catch (e) {
    record(6, 'AP Stats', false, e.message);
  }

  // TEST 7
  try {
    const { res, body } = await jsonFetch(`${BASE}/ap/invoices`, { headers: auth(AP_TOKEN) });
    const list = body.invoices ?? body;
    const ok = res.ok && Array.isArray(list) && list.every((i) => Array.isArray(i.agents) && i.agents.length === 0);
    record(7, 'AP Invoice list (no filter)', ok, ok ? `${list.length} invoices` : `${res.status} ${JSON.stringify(body).slice(0, 150)}`);
  } catch (e) {
    record(7, 'AP Invoice list (no filter)', false, e.message);
  }

  // TEST 8
  try {
    const { res, body } = await jsonFetch(`${BASE}/ap/invoices?risk=LOW`, { headers: auth(AP_TOKEN) });
    const list = body.invoices ?? body;
    const ok = res.ok && Array.isArray(list) && list.every((i) => i.risk === 'LOW');
    record(8, 'AP Invoice list (risk filter)', ok, ok ? `${list.length} LOW invoices` : `${res.status} ${JSON.stringify(body).slice(0, 150)}`);
  } catch (e) {
    record(8, 'AP Invoice list (risk filter)', false, e.message);
  }

  // TEST 9
  try {
    const { res, body } = await jsonFetch(`${BASE}/ap/invoices/1`, { headers: auth(AP_TOKEN) });
    const inv = body.invoice ?? body;
    const ok = res.ok && Array.isArray(inv.agents) && inv.agents.length === 6;
    record(9, 'AP Invoice detail', ok, ok ? '6 agents' : `${res.status} ${JSON.stringify(body).slice(0, 150)}`);
  } catch (e) {
    record(9, 'AP Invoice detail', false, e.message);
  }

  // TEST 10
  try {
    const { res, body } = await jsonFetch(`${BASE}/ap/decisions`, { headers: auth(AP_TOKEN) });
    const ok = res.ok && (body.LOW !== undefined || body.low !== undefined);
    record(10, 'AP Decisions', ok, ok ? JSON.stringify(Object.keys(body)) : `${res.status} ${JSON.stringify(body).slice(0, 150)}`);
  } catch (e) {
    record(10, 'AP Decisions', false, e.message);
  }

  // TEST 11 - PDF upload
  try {
    const pdfContent = '%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 1\ntrailer\n<< /Root 1 0 R >>\nstartxref\n0\n%%EOF';
    const blob = new Blob([pdfContent], { type: 'application/pdf' });
    const form = new FormData();
    form.append('file', blob, 'test-invoice.pdf');

    const res = await fetch(`${BASE}/ap/invoices/upload`, {
      method: 'POST',
      headers: {
        'ngrok-skip-browser-warning': 'true',
        Authorization: `Bearer ${AP_TOKEN}`,
      },
      body: form,
    });
    const body = await res.json();
    if (res.ok && body.jobId && body.status === 'processing') {
      TEST_JOB_ID = body.jobId;
      record(11, 'AP Upload (PDF)', true, `jobId=${TEST_JOB_ID}`);
    } else {
      record(11, 'AP Upload (PDF)', false, `${res.status} ${JSON.stringify(body)}`);
    }
  } catch (e) {
    record(11, 'AP Upload (PDF)', false, e.message);
  }

  // TEST 12
  try {
    const blob = new Blob(['not a pdf'], { type: 'text/plain' });
    const form = new FormData();
    form.append('file', blob, 'test.txt');

    const res = await fetch(`${BASE}/ap/invoices/upload`, {
      method: 'POST',
      headers: {
        'ngrok-skip-browser-warning': 'true',
        Authorization: `Bearer ${AP_TOKEN}`,
      },
      body: form,
    });
    const body = await res.json();
    const ok = res.status === 400 && (body.error?.includes('PDF') || body.detail?.includes('PDF') || body.message?.includes('PDF'));
    record(12, 'AP Upload (non-PDF)', ok, ok ? '' : `${res.status} ${JSON.stringify(body)}`);
  } catch (e) {
    record(12, 'AP Upload (non-PDF)', false, e.message);
  }

  // TEST 13
  try {
    if (!TEST_JOB_ID) {
      record(13, 'Job status', false, 'No TEST_JOB_ID from test 11');
    } else {
      const { res, body } = await jsonFetch(`${BASE}/ap/invoices/jobs/${TEST_JOB_ID}`, { headers: auth(AP_TOKEN) });
      const ok = res.ok && body.jobId && (body.status === 'processing' || body.status === 'complete' || body.status === 'failed');
      record(13, 'Job status', ok, ok ? `status=${body.status}` : `${res.status} ${JSON.stringify(body)}`);
    }
  } catch (e) {
    record(13, 'Job status', false, e.message);
  }

  // TEST 14
  try {
    const { res, body } = await jsonFetch(`${BASE}/cfo/stats`, { headers: auth(CFO_TOKEN) });
    const ok = res.ok && typeof body.totalProcessed === 'number';
    record(14, 'CFO Stats', ok, ok ? '' : `${res.status} ${JSON.stringify(body)}`);
  } catch (e) {
    record(14, 'CFO Stats', false, e.message);
  }

  // TEST 15
  try {
    const { res, body } = await jsonFetch(`${BASE}/cfo/invoices`, { headers: auth(CFO_TOKEN) });
    const list = body.invoices ?? body;
    record(15, 'CFO Invoice list', res.ok && Array.isArray(list), res.ok ? `${list.length} invoices` : `${res.status} ${JSON.stringify(body).slice(0, 150)}`);
  } catch (e) {
    record(15, 'CFO Invoice list', false, e.message);
  }

  // TEST 16
  try {
    const { res, body } = await jsonFetch(`${BASE}/cfo/invoices/1`, { headers: auth(CFO_TOKEN) });
    const inv = body.invoice ?? body;
    record(16, 'CFO Invoice detail', res.ok && Array.isArray(inv.agents), res.ok ? `${inv.agents?.length} agents` : `${res.status} ${JSON.stringify(body).slice(0, 150)}`);
  } catch (e) {
    record(16, 'CFO Invoice detail', false, e.message);
  }

  // TEST 17
  try {
    const { res, body } = await jsonFetch(`${BASE}/cfo/pending-approvals`, { headers: auth(CFO_TOKEN) });
    const list = body.pending ?? body;
    const arr = Array.isArray(list) ? list : list?.pending ?? [];
    if (res.ok && Array.isArray(arr)) {
      arr.forEach((inv) => {
        if (inv.risk === 'HIGH') pendingHighId = inv.id;
        if (inv.risk === 'CRITICAL') pendingCriticalId = inv.id;
      });
      const ok = arr.every((i) => ['HIGH', 'CRITICAL'].includes(i.risk));
      record(17, 'CFO Pending approvals', ok, `${arr.length} pending, HIGH id=${pendingHighId}, CRITICAL id=${pendingCriticalId}`);
    } else {
      record(17, 'CFO Pending approvals', false, `${res.status} ${JSON.stringify(body).slice(0, 150)}`);
    }
  } catch (e) {
    record(17, 'CFO Pending approvals', false, e.message);
  }

  // TEST 18
  try {
    const approveId = pendingHighId || pendingCriticalId;
    if (!approveId) {
      record(18, 'CFO Approve', false, 'No pending HIGH/CRITICAL invoice');
    } else {
      const { res, body } = await jsonFetch(`${BASE}/cfo/invoices/${approveId}/approve`, {
        method: 'POST',
        headers: auth(CFO_TOKEN),
        body: JSON.stringify({}),
      });
      const inv = body.invoice ?? body;
      const status = (inv.status || '').toLowerCase();
      record(18, 'CFO Approve', res.ok && status === 'approved', res.ok ? `status=${inv.status}` : `${res.status} ${JSON.stringify(body).slice(0, 150)}`);
    }
  } catch (e) {
    record(18, 'CFO Approve', false, e.message);
  }

  // TEST 19
  try {
    // Re-fetch pending for another id
    const { body: pendingBody } = await jsonFetch(`${BASE}/cfo/pending-approvals`, { headers: auth(CFO_TOKEN) });
    const arr = pendingBody.pending ?? pendingBody;
    const rejectId = Array.isArray(arr) ? arr.find((i) => i.id !== pendingHighId && i.id !== pendingCriticalId)?.id ?? arr[0]?.id : null;
    if (!rejectId) {
      record(19, 'CFO Reject', false, 'No pending invoice to reject');
    } else {
      const { res, body } = await jsonFetch(`${BASE}/cfo/invoices/${rejectId}/reject`, {
        method: 'POST',
        headers: auth(CFO_TOKEN),
        body: JSON.stringify({ reason: 'Test rejection' }),
      });
      const inv = body.invoice ?? body;
      const status = (inv.status || '').toLowerCase();
      record(19, 'CFO Reject', res.ok && status === 'rejected', res.ok ? `status=${inv.status}` : `${res.status} ${JSON.stringify(body).slice(0, 150)}`);
    }
  } catch (e) {
    record(19, 'CFO Reject', false, e.message);
  }

  // TEST 20
  try {
    const { res, body } = await jsonFetch(`${BASE}/cfo/audit-log`, { headers: auth(CFO_TOKEN) });
    const entries = body.entries ?? body;
    const ok = res.ok && Array.isArray(entries) && entries[0]?.timestamp;
    record(20, 'Audit log', ok, ok ? `${entries.length} entries, total=${body.total}` : `${res.status} ${JSON.stringify(body).slice(0, 150)}`);
  } catch (e) {
    record(20, 'Audit log', false, e.message);
  }

  // TEST 21
  try {
    const { res, body } = await jsonFetch(`${BASE}/cfo/audit-log?page=1&limit=5`, { headers: auth(CFO_TOKEN) });
    const entries = body.entries ?? [];
    record(21, 'Audit log pagination', res.ok && entries.length <= 5, res.ok ? `${entries.length} entries` : `${res.status} ${JSON.stringify(body).slice(0, 150)}`);
  } catch (e) {
    record(21, 'Audit log pagination', false, e.message);
  }

  // TEST 22
  try {
    const res = await fetch(`${BASE}/cfo/audit-log/export`, {
      headers: {
        'ngrok-skip-browser-warning': 'true',
        Authorization: `Bearer ${CFO_TOKEN}`,
      },
    });
    const ct = res.headers.get('content-type') || '';
    const text = await res.text();
    const ok = res.ok && (ct.includes('csv') || ct.includes('text') || text.includes('Timestamp'));
    record(22, 'Audit log export', ok, ok ? `content-type=${ct}, ${text.length} bytes` : `${res.status} ${text.slice(0, 100)}`);
  } catch (e) {
    record(22, 'Audit log export', false, e.message);
  }

  // TEST 23
  try {
    const { res } = await jsonFetch(`${BASE}/cfo/stats`, { headers: auth(AP_TOKEN) });
    record(23, 'AP token on CFO route', res.status === 403, `status ${res.status}`);
  } catch (e) {
    record(23, 'AP token on CFO route', false, e.message);
  }

  // TEST 24
  try {
    const { res } = await jsonFetch(`${BASE}/ap/stats`, { headers: auth(CFO_TOKEN) });
    record(24, 'CFO token on AP route', res.status === 403, `status ${res.status}`);
  } catch (e) {
    record(24, 'CFO token on AP route', false, e.message);
  }

  // TEST 25 - WebSocket
  try {
    if (!TEST_JOB_ID || !AP_TOKEN) {
      record(25, 'WebSocket connection', false, 'Missing TEST_JOB_ID or AP_TOKEN');
    } else {
      await new Promise((resolve, reject) => {
        const events = [];
        const ws = new WebSocket(`${WS_BASE}?token=${AP_TOKEN}`);
        const timeout = setTimeout(() => {
          ws.close();
          reject(new Error(`Timeout. Events: ${events.map((e) => e.type).join(', ')}`));
        }, 30000);

        ws.onopen = () => {
          ws.send(JSON.stringify({ jobId: TEST_JOB_ID }));
        };

        ws.onmessage = (msg) => {
          const event = JSON.parse(msg.data);
          events.push(event);
          if (event.type === 'job_complete' || event.type === 'job_failed') {
            clearTimeout(timeout);
            ws.close();
            const starts = events.filter((e) => e.type === 'agent_start').length;
            const completes = events.filter((e) => e.type === 'agent_complete').length;
            const hasComplete = events.some((e) => e.type === 'job_complete');
            const ok = starts >= 1 && completes >= 1 && (hasComplete || events.some((e) => e.type === 'job_failed'));
            record(25, 'WebSocket connection', ok, `events: ${events.map((e) => e.type).join(' → ')}`);
            resolve();
          }
        };

        ws.onerror = (err) => {
          clearTimeout(timeout);
          reject(new Error('WebSocket error'));
        };
      });
    }
  } catch (e) {
    record(25, 'WebSocket connection', false, e.message);
  }

  console.log('\n========== SUMMARY ==========');
  const passed = results.filter((r) => r.pass).length;
  const failed = results.filter((r) => !r.pass).length;
  console.log(`PASS: ${passed}/25  FAIL: ${failed}/25`);
  if (failed > 0) {
    console.log('\nFailed tests:');
    results.filter((r) => !r.pass).forEach((r) => {
      console.log(`  TEST ${r.num}: ${r.detail}`);
    });
  }
}

runTests().catch(console.error);
