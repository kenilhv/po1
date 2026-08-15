import { useState, useEffect, useCallback } from 'react';
import Navbar from '../components/Navbar';
import StatCard from '../components/StatCard';
import InvoiceCard from '../components/InvoiceCard';
import AuditLog from '../components/AuditLog';
import ApprovalModal from '../components/ApprovalModal';
import RiskBadge from '../components/RiskBadge';
import ErrorState, { DashboardSkeleton } from '../components/ErrorState';
import * as cfo from '../api/cfo';
import { formatCurrency } from '../utils/formatters';

const FILTERS = ['All', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];

function PendingApprovalCard({ invoice, onApprove, onReject, resolved, actionLoading }) {
  if (resolved) {
    return (
      <div className={`rounded-xl border p-5 ${resolved === 'approved' ? 'border-success/30 bg-[#14532d]/10' : 'border-danger/30 bg-[#450a0a]/10'}`}>
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm">{invoice.number}</span>
          <span className={`text-xs font-medium ${resolved === 'approved' ? 'text-success' : 'text-danger'}`}>
            {resolved === 'approved' ? '✓ Approved' : '✗ Rejected'}
          </span>
        </div>
        <p className="mt-1 text-sm text-text-secondary">{invoice.vendor} — {formatCurrency(invoice.amount)}</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-sm text-text-primary">{invoice.number}</span>
        <RiskBadge risk={invoice.risk} size="lg" />
      </div>

      <h3 className="mt-3 text-xl font-bold text-text-primary">{invoice.vendor}</h3>
      <p className="mt-1 font-mono text-3xl font-bold text-primary">{formatCurrency(invoice.amount)}</p>

      {invoice.riskReasons?.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {invoice.riskReasons.map((reason) => (
            <span key={reason} className="rounded-full border border-border bg-surface-elevated px-2.5 py-0.5 text-xs text-text-secondary">
              {reason}
            </span>
          ))}
        </div>
      )}

      {invoice.evidence && (
        <p className="mt-4 text-sm leading-relaxed text-text-secondary">{invoice.evidence}</p>
      )}

      <div className="mt-5 flex gap-3">
        <button
          type="button"
          onClick={() => onApprove(invoice)}
          disabled={actionLoading}
          className="flex-1 rounded-lg border border-success py-2.5 text-sm font-medium text-success transition-default hover:bg-success/10 disabled:opacity-50"
        >
          ✓ Approve
        </button>
        <button
          type="button"
          onClick={() => onReject(invoice)}
          disabled={actionLoading}
          className="flex-1 rounded-lg border border-danger py-2.5 text-sm font-medium text-danger transition-default hover:bg-danger/10 disabled:opacity-50"
        >
          ✗ Reject
        </button>
      </div>
    </div>
  );
}

export default function CFODashboard() {
  const [stats, setStats] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [pending, setPending] = useState([]);
  const [auditLog, setAuditLog] = useState([]);
  const [filter, setFilter] = useState('All');
  const [modal, setModal] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [resolved, setResolved] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [loadingDetailId, setLoadingDetailId] = useState(null);
  const [exporting, setExporting] = useState(false);

  const refreshDashboard = useCallback(async ({ resetFilter = false } = {}) => {
    if (resetFilter) setFilter('All');

    const [statsRes, invRes, pendingRes, auditRes] = await Promise.all([
      cfo.getStats(),
      cfo.getInvoices(resetFilter ? null : (filter === 'All' ? null : filter)),
      cfo.getPendingApprovals(),
      cfo.getAuditLog(1, 15),
    ]);

    if (statsRes.data) setStats(statsRes.data);
    if (invRes.data) setInvoices(invRes.data);
    if (pendingRes.data) setPending(pendingRes.data);
    if (auditRes.data?.entries) setAuditLog(auditRes.data.entries);

    const err = statsRes.error || invRes.error || pendingRes.error || auditRes.error;
    if (err) setError(err.includes('500') ? 'Server error. Try again in a moment.' : err);
  }, [filter]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    await refreshDashboard({ resetFilter: true });
    setLoading(false);
  }, [refreshDashboard]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  // Poll so invoices uploaded on AP appear here without a manual refresh.
  useEffect(() => {
    const interval = setInterval(() => {
      refreshDashboard();
    }, 5000);
    return () => clearInterval(interval);
  }, [refreshDashboard]);

  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === 'visible') refreshDashboard();
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, [refreshDashboard]);

  const pendingCount = pending.filter((i) => !resolved[i.id]).length;

  const handleFilter = async (f) => {
    setFilter(f);
    const { data, error: err } = await cfo.getInvoices(f === 'All' ? null : f);
    if (data) setInvoices(data);
    if (err) setError(err);
  };

  const handleExpand = async (invoice, expanded) => {
    if (!expanded || (invoice.agents && invoice.agents.length > 0)) return;
    setLoadingDetailId(invoice.id);
    const { data } = await cfo.getInvoice(invoice.id);
    setLoadingDetailId(null);
    if (data) {
      setInvoices((prev) => prev.map((i) => (i.id === invoice.id ? data : i)));
    }
  };

  const handleApproveConfirm = async () => {
    const inv = modal.invoice;
    setActionLoading(true);
    const { error: err } = await cfo.approveInvoice(inv.id);
    setActionLoading(false);

    if (err) {
      setError(err);
      setModal(null);
      return;
    }

    setResolved((prev) => ({ ...prev, [inv.id]: 'approved' }));
    setPending((prev) => prev.filter((i) => i.id !== inv.id));
    await refreshDashboard({ resetFilter: true });
    setModal(null);
  };

  const handleRejectConfirm = async () => {
    const inv = modal.invoice;
    setActionLoading(true);
    const { error: err } = await cfo.rejectInvoice(inv.id, rejectReason);
    setActionLoading(false);

    if (err) {
      setError(err);
      setModal(null);
      return;
    }

    setResolved((prev) => ({ ...prev, [inv.id]: 'rejected' }));
    setPending((prev) => prev.filter((i) => i.id !== inv.id));
    setRejectReason('');
    await refreshDashboard({ resetFilter: true });
    setModal(null);
  };

  const handleExport = async () => {
    setExporting(true);
    const { error: err } = await cfo.exportAuditLog();
    setExporting(false);
    if (err) setError(err);
  };

  if (loading && !stats) {
    return (
      <div className="ambient-bg min-h-screen">
        <Navbar title="CFO Dashboard" showChangeUser />
        <div className="mx-auto max-w-7xl px-6 py-6">
          <DashboardSkeleton />
        </div>
      </div>
    );
  }

  return (
    <div className="ambient-bg page-enter min-h-screen">
      <Navbar title="CFO Dashboard" showChangeUser />

      <div className="mx-auto max-w-7xl px-6 py-6">
        {error && (
          <div className="mb-4">
            <ErrorState message={error} onRetry={loadAll} />
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Total Processed" value={stats?.totalProcessed ?? '—'} />
          <StatCard label="Auto Approved" value={stats?.autoApproved ?? '—'} accent="green" />
          <StatCard label="Pending Approval" value={pendingCount} accent="amber" />
          <StatCard label="Total Saved" value={stats ? formatCurrency(stats.totalSaved) : '—'} accent="indigo" />
        </div>

        {pendingCount > 0 && (
          <div className="pulse-border mt-6 rounded-lg border-l-4 border-l-warning bg-[#451a03]/20 px-5 py-4">
            <p className="text-sm font-medium text-warning">
              {pendingCount} invoice{pendingCount !== 1 ? 's' : ''} require your approval
            </p>
          </div>
        )}

        <div className="mt-8 flex flex-col gap-6 lg:flex-row">
          <div className="lg:w-[55%]">
            <div className="mb-4 flex flex-wrap items-center gap-3">
              <h2 className="text-sm font-semibold text-text-primary">
                Invoices
                <span className="ml-2 rounded-full bg-surface-elevated px-2 py-0.5 text-xs font-mono text-text-muted">
                  {invoices.length}
                </span>
              </h2>
              <div className="flex flex-wrap gap-1">
                {FILTERS.map((f) => (
                  <button
                    key={f}
                    type="button"
                    onClick={() => handleFilter(f)}
                    className={`rounded-lg px-3 py-1 text-xs transition-default ${
                      filter === f ? 'bg-primary/15 text-primary' : 'text-text-muted hover:text-text-secondary'
                    }`}
                  >
                    {f}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-3">
              {invoices.map((inv, i) => (
                <InvoiceCard
                  key={inv.id}
                  invoice={inv}
                  index={i}
                  onExpand={handleExpand}
                  loadingDetail={loadingDetailId === inv.id}
                />
              ))}
            </div>
          </div>

          <div className="space-y-6 lg:w-[45%]">
            <div>
              <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-text-primary">
                Pending Your Approval
                {pendingCount > 0 && (
                  <span className="rounded-full bg-danger/20 px-2 py-0.5 text-xs font-mono text-danger">
                    {pendingCount}
                  </span>
                )}
              </h2>

              {pending.length === 0 ? (
                <div className="flex flex-col items-center justify-center rounded-xl border border-border bg-surface py-12 text-center">
                  <svg className="mb-3 h-10 w-10 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <p className="text-sm text-text-secondary">All clear. No approvals needed.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {pending.map((inv) => (
                    <PendingApprovalCard
                      key={inv.id}
                      invoice={inv}
                      resolved={resolved[inv.id]}
                      actionLoading={actionLoading}
                      onApprove={(i) => setModal({ type: 'approve', invoice: i })}
                      onReject={(i) => setModal({ type: 'reject', invoice: i })}
                    />
                  ))}
                </div>
              )}
            </div>

            <AuditLog entries={auditLog} onExport={handleExport} exporting={exporting} />
          </div>
        </div>
      </div>

      {modal && (
        <ApprovalModal
          type={modal.type}
          invoice={modal.invoice}
          reason={rejectReason}
          onReasonChange={setRejectReason}
          onConfirm={modal.type === 'approve' ? handleApproveConfirm : handleRejectConfirm}
          onCancel={() => { setModal(null); setRejectReason(''); }}
          loading={actionLoading}
        />
      )}
    </div>
  );
}
