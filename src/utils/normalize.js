const DECISION_STATUS = {
  AUTO_APPROVED: 'Auto Approved',
  PENDING_AP: 'Flagged',
  PENDING_CFO: 'Pending CFO Approval',
  BLOCKED: 'Escalated',
  APPROVED: 'Approved',
  REJECTED: 'Rejected',
};

const STATUS_MAP = {
  auto_approved: 'Auto Approved',
  'auto approved': 'Auto Approved',
  approved: 'Approved',
  flagged: 'Flagged',
  escalated: 'Escalated',
  blocked: 'Escalated',
  pending_ap: 'Flagged',
  pending_cfo: 'Pending CFO Approval',
  pending_cfo_approval: 'Pending CFO Approval',
  'pending cfo approval': 'Pending CFO Approval',
  rejected: 'Rejected',
  processing: 'Processing',
};

export function formatConfidence(value) {
  if (value == null) return null;
  const n = Number(value);
  if (Number.isNaN(n)) return null;
  return n <= 1 ? Math.round(n * 100) : Math.round(n);
}

export function normalizeStatus(status) {
  if (!status) return status;
  const key = status.toLowerCase().replace(/\s+/g, ' ').trim();
  const snake = key.replace(/\s+/g, '_');
  return STATUS_MAP[snake] || STATUS_MAP[key] || status;
}

export function normalizeAgent(agent) {
  if (!agent) return agent;
  return {
    agent: agent.agent || agent.name,
    result: agent.result || agent.detail || '',
    confidence: formatConfidence(agent.confidence),
    model: agent.model || '',
    status: agent.status,
    detail: agent.detail || '',
    state: agent.state || 'complete',
  };
}

export function normalizeInvoice(invoice) {
  if (!invoice) return null;
  const decisionKey = (invoice.decision || '').toUpperCase();
  const status = DECISION_STATUS[decisionKey] || normalizeStatus(invoice.status);
  return {
    ...invoice,
    id: String(invoice.id),
    number: invoice.number || invoice.invoice_number,
    risk: (invoice.risk || invoice.risk_score || '').toUpperCase(),
    status,
    timestamp: invoice.timestamp || invoice.created_at,
    agents: (invoice.agents || []).map(normalizeAgent),
    riskReasons: invoice.riskReasons || invoice.risk_reasons || [],
    evidence: invoice.evidence || '',
  };
}

export function normalizeInvoiceList(data) {
  const list = data?.invoices ?? data ?? [];
  return Array.isArray(list) ? list.map(normalizeInvoice) : [];
}

export function normalizeDecisions(data) {
  if (!data) return [];
  const levels = [
    { key: 'LOW', title: 'LOW DECISIONS', color: 'text-success border-success/30 bg-[#14532d]/20', action: null },
    { key: 'MEDIUM', title: 'MEDIUM DECISIONS', color: 'text-warning border-warning/30 bg-[#451a03]/20', action: 'Review' },
    { key: 'HIGH', title: 'HIGH DECISIONS', color: 'text-orange-400 border-orange-400/30 bg-[#431407]/20', action: 'View Details' },
    { key: 'CRITICAL', title: 'CRITICAL DECISIONS', color: 'text-danger border-danger/30 bg-[#450a0a]/20', action: 'View Details', subtitle: 'Escalated to CFO' },
  ];

  return levels.map(({ key, title, color, action, subtitle }) => {
    const block = data[key] ?? data[key.toLowerCase()] ?? [];
    const items = Array.isArray(block)
      ? block.map((i) => (typeof i === 'string' ? i : i.number))
      : block.recent || [];
    const count = Array.isArray(block) ? block.length : block.count ?? items.length;

    return { title, color, action, subtitle, count, items };
  });
}

export function normalizeAuditEntry(entry) {
  return {
    id: String(entry.id),
    timestamp: entry.timestamp,
    invoice: entry.invoice || entry.invoice_number,
    agent: entry.agent,
    decision: entry.decision,
    model: entry.model || '—',
    confidence: entry.confidence ?? null,
    approvedBy: entry.approvedBy || entry.approved_by || '—',
  };
}
