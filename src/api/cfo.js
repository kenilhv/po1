import { apiFetch } from './client';
import { normalizeAuditEntry, normalizeInvoice, normalizeInvoiceList } from '../utils/normalize';

export async function getStats() {
  return apiFetch('/cfo/stats');
}

export async function getInvoices(risk) {
  const query = risk && risk !== 'All' ? `?risk=${encodeURIComponent(risk)}` : '';
  const result = await apiFetch(`/cfo/invoices${query}`);
  if (result.data) {
    return { ...result, data: normalizeInvoiceList(result.data) };
  }
  return result;
}

export async function getInvoice(id) {
  const result = await apiFetch(`/cfo/invoices/${id}`);
  if (result.data) {
    const inv = result.data.invoice ?? result.data;
    return { ...result, data: normalizeInvoice(inv) };
  }
  return result;
}

export async function getPendingApprovals() {
  const result = await apiFetch('/cfo/pending-approvals');
  if (result.data) {
    const list = result.data.pending ?? result.data;
    const arr = Array.isArray(list) ? list : [];
    return { ...result, data: arr.map(normalizeInvoice) };
  }
  return result;
}

export async function approveInvoice(id) {
  const result = await apiFetch(`/cfo/invoices/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
  if (result.data) {
    const inv = result.data.invoice ?? result.data;
    return { ...result, data: normalizeInvoice(inv) };
  }
  return result;
}

export async function rejectInvoice(id, reason) {
  const body = reason ? { reason } : {};
  const result = await apiFetch(`/cfo/invoices/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
  if (result.data) {
    const inv = result.data.invoice ?? result.data;
    return { ...result, data: normalizeInvoice(inv) };
  }
  return result;
}

export async function getAuditLog(page = 1, limit = 15) {
  const result = await apiFetch(`/cfo/audit-log?page=${page}&limit=${limit}`);
  if (result.data?.entries) {
    return {
      ...result,
      data: {
        ...result.data,
        entries: result.data.entries.map(normalizeAuditEntry),
      },
    };
  }
  return result;
}

export async function exportAuditLog() {
  const result = await apiFetch('/cfo/audit-log/export', { responseType: 'blob' });
  if (result.data) {
    const url = URL.createObjectURL(result.data);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'paycrew-audit-trail.csv';
    a.click();
    URL.revokeObjectURL(url);
  }
  return result;
}
