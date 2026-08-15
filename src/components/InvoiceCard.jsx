import { useState } from 'react';
import RiskBadge from './RiskBadge';
import AgentTrace from './AgentTrace';
import { formatCurrency, formatTimestamp } from '../utils/formatters';

const statusStyles = {
  'Auto Approved': 'bg-[#14532d]/50 text-success',
  Flagged: 'bg-[#451a03]/50 text-warning',
  Escalated: 'bg-[#450a0a]/50 text-danger',
  'Pending CFO Approval': 'bg-[#450a0a]/50 text-danger',
  Approved: 'bg-[#14532d]/50 text-success',
  Rejected: 'bg-[#450a0a]/50 text-danger',
  Processing: 'bg-primary/20 text-primary',
};

export default function InvoiceCard({ invoice, index = 0, onExpand, loadingDetail = false }) {
  const [expanded, setExpanded] = useState(false);

  const toggle = () => {
    const next = !expanded;
    setExpanded(next);
    onExpand?.(invoice, next);
  };

  return (
    <div
      className="card-hover stagger-in cursor-pointer rounded-xl border border-border bg-surface p-4"
      style={{ animationDelay: `${index * 50}ms` }}
      onClick={toggle}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-sm text-text-primary">{invoice.number}</span>
          <RiskBadge risk={invoice.risk} />
          <span className="text-xs text-text-muted">{formatTimestamp(invoice.timestamp)}</span>
        </div>
        <svg
          className={`h-4 w-4 shrink-0 text-text-muted transition-default ${expanded ? 'rotate-90' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </div>

      <div className="mt-2 flex items-center justify-between">
        <span className="font-semibold text-text-primary">{invoice.vendor}</span>
        <span className="font-mono font-semibold text-primary">{formatCurrency(invoice.amount)}</span>
      </div>

      <div className="mt-3">
        <span className={`inline-flex rounded-md px-2 py-0.5 text-xs font-medium ${statusStyles[invoice.status] || statusStyles.Flagged}`}>
          {invoice.status}
        </span>
      </div>

      {expanded && (
        <AgentTrace
          agents={invoice.agents || []}
          animated
          loading={loadingDetail}
        />
      )}
    </div>
  );
}
