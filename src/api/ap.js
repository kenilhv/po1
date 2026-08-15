import { apiFetch, uploadFile } from './client';
import { normalizeInvoice, normalizeInvoiceList } from '../utils/normalize';

export async function getStats() {
  const result = await apiFetch('/ap/stats');
  return result;
}

export async function getInvoices(risk) {
  const query = risk && risk !== 'All' ? `?risk=${encodeURIComponent(risk)}` : '';
  const result = await apiFetch(`/ap/invoices${query}`);
  if (result.data) {
    return { ...result, data: normalizeInvoiceList(result.data) };
  }
  return result;
}

export async function getInvoice(id) {
  const result = await apiFetch(`/ap/invoices/${id}`);
  if (result.data) {
    const inv = result.data.invoice ?? result.data;
    return { ...result, data: normalizeInvoice(inv) };
  }
  return result;
}

export async function getDecisions() {
  return apiFetch('/ap/decisions');
}

export async function uploadInvoice(file) {
  return uploadFile('/ap/invoices/upload', file);
}

export async function getJobStatus(jobId) {
  const result = await apiFetch(`/ap/invoices/jobs/${jobId}`);
  if (result.data?.invoice) {
    return {
      ...result,
      data: {
        ...result.data,
        invoice: normalizeInvoice(result.data.invoice),
      },
    };
  }
  return result;
}
