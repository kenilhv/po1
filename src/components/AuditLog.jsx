import { formatAuditTimestamp } from '../utils/formatters';

const decisionColors = {
  'Auto Approved': 'text-success',
  Approved: 'text-success',
  Flagged: 'text-warning',
  Escalated: 'text-orange-400',
  'Escalated to CFO': 'text-orange-400',
  CRITICAL: 'text-danger',
  HIGH: 'text-orange-400',
  LOW: 'text-success',
  MEDIUM: 'text-warning',
  DUPLICATE: 'text-danger',
  FLAGGED: 'text-danger',
  'No PO found': 'text-warning',
  Rejected: 'text-danger',
};

export default function AuditLog({ entries, onExport, exporting = false }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text-primary">Audit Trail</h3>
        <button
          type="button"
          onClick={onExport}
          disabled={exporting}
          className="rounded-lg border border-border px-3 py-1 text-xs text-text-secondary transition-default hover:border-primary hover:text-primary disabled:opacity-50"
        >
          {exporting ? 'Exporting...' : 'Export CSV'}
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-border text-text-muted">
              <th className="pb-2 pr-3 font-medium">Timestamp</th>
              <th className="pb-2 pr-3 font-medium">Invoice #</th>
              <th className="pb-2 pr-3 font-medium">Agent</th>
              <th className="pb-2 pr-3 font-medium">Decision</th>
              <th className="pb-2 pr-3 font-medium">Model</th>
              <th className="pb-2 pr-3 font-medium">Confidence</th>
              <th className="pb-2 font-medium">Approved By</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry, i) => (
              <tr
                key={entry.id}
                className={`border-b border-border/50 ${i % 2 === 0 ? 'bg-surface' : 'bg-surface-elevated/30'}`}
              >
                <td className="py-2.5 pr-3 font-mono text-text-secondary">{formatAuditTimestamp(entry.timestamp)}</td>
                <td className="py-2.5 pr-3 font-mono text-text-primary">{entry.invoice}</td>
                <td className="py-2.5 pr-3 text-text-secondary">{entry.agent}</td>
                <td className={`py-2.5 pr-3 font-medium ${decisionColors[entry.decision] || 'text-text-secondary'}`}>
                  {entry.decision}
                </td>
                <td className="py-2.5 pr-3 font-mono text-[10px] text-text-muted">{entry.model}</td>
                <td className="py-2.5 pr-3 text-text-secondary">{entry.confidence != null ? `${entry.confidence}%` : '—'}</td>
                <td className="py-2.5 text-text-secondary">{entry.approvedBy}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
