import { useState, useEffect, useCallback } from 'react';
import Navbar from '../components/Navbar';
import StatCard from '../components/StatCard';
import InvoiceCard from '../components/InvoiceCard';
import UploadInvoice from '../components/UploadInvoice';
import ErrorState, { DashboardSkeleton } from '../components/ErrorState';
import * as ap from '../api/ap';
import { normalizeDecisions } from '../utils/normalize';

const FILTERS = ['All', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];

function DecisionsPanel({ sections }) {
  return (
    <div className="space-y-4">
      <h2 className="text-sm font-semibold text-text-primary">Agent Decisions</h2>
      {sections.map((section) => (
        <div key={section.title} className={`rounded-xl border p-4 ${section.color}`}>
          <div className={`flex items-center justify-between ${section.title === 'CRITICAL DECISIONS' ? 'pulse-critical' : ''}`}>
            <span className="text-xs font-semibold tracking-wide">{section.title}</span>
            <span className="rounded-full bg-black/20 px-2 py-0.5 text-xs font-mono">{section.count}</span>
          </div>
          {section.subtitle && (
            <p className="mt-1 text-[10px] uppercase tracking-wide opacity-70">{section.subtitle}</p>
          )}
          <div className="mt-3 space-y-2">
            {section.items.length === 0 ? (
              <p className="text-xs opacity-60">None</p>
            ) : (
              section.items.map((num, idx) => (
                <div key={`${num}-${idx}`} className="flex items-center justify-between">
                  <span className="font-mono text-xs">{num}</span>
                  {section.action && (
                    <button type="button" className="rounded border border-current/30 px-2 py-0.5 text-[10px] transition-default hover:bg-white/5">
                      {section.action}
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function APDashboard() {
  const [stats, setStats] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [decisions, setDecisions] = useState([]);
  const [filter, setFilter] = useState('All');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [loadingDetailId, setLoadingDetailId] = useState(null);

  const loadStats = useCallback(async () => {
    const { data, error: err } = await ap.getStats();
    if (data) setStats(data);
    return { data, error: err };
  }, []);

  const loadInvoices = useCallback(async (risk = filter) => {
    const { data, error: err } = await ap.getInvoices(risk === 'All' ? null : risk);
    if (data) setInvoices(data);
    return { data, error: err };
  }, [filter]);

  const loadDecisions = useCallback(async () => {
    const { data, error: err } = await ap.getDecisions();
    if (data) setDecisions(normalizeDecisions(data));
    return { data, error: err };
  }, []);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    const results = await Promise.all([loadStats(), loadInvoices(), loadDecisions()]);
    const err = results.find((r) => r.error)?.error;
    if (err) {
      setError(err.includes('500') ? 'Server error. Try again in a moment.' : err);
    }
    setLoading(false);
  }, [loadStats, loadInvoices, loadDecisions]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const handleFilter = async (f) => {
    setFilter(f);
    setLoading(true);
    const { data, error: err } = await ap.getInvoices(f === 'All' ? null : f);
    if (data) setInvoices(data);
    setError(err || null);
    setLoading(false);
  };

  const handleExpand = async (invoice, expanded) => {
    if (!expanded || (invoice.agents && invoice.agents.length > 0)) return;

    setLoadingDetailId(invoice.id);
    const { data, error: err } = await ap.getInvoice(invoice.id);
    setLoadingDetailId(null);

    if (data) {
      setInvoices((prev) => prev.map((i) => (i.id === invoice.id ? data : i)));
    } else if (err) {
      setError(err);
    }
  };

  const handleUploadComplete = useCallback(async () => {
    setFilter('All');
    const [statsRes, invRes, decRes] = await Promise.all([
      ap.getStats(),
      ap.getInvoices(null),
      ap.getDecisions(),
    ]);
    if (statsRes.data) setStats(statsRes.data);
    if (invRes.data) setInvoices(invRes.data);
    if (decRes.data) setDecisions(normalizeDecisions(decRes.data));
  }, []);

  if (loading && !stats) {
    return (
      <div className="ambient-bg min-h-screen">
        <Navbar title="AP Team Dashboard" showChangeUser />
        <div className="mx-auto max-w-7xl px-6 py-6">
          <DashboardSkeleton />
        </div>
      </div>
    );
  }

  return (
    <div className="ambient-bg page-enter min-h-screen">
      <Navbar title="AP Team Dashboard" showChangeUser />

      <div className="mx-auto max-w-7xl px-6 py-6">
        <UploadInvoice onUploadComplete={handleUploadComplete} />

        {error && (
          <div className="mt-4">
            <ErrorState message={error} onRetry={loadAll} />
          </div>
        )}

        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Total Invoices" value={stats?.total ?? '—'} />
          <StatCard label="Auto Approved" value={stats?.autoApproved ?? '—'} accent="green" />
          <StatCard label="Flagged" value={stats?.flagged ?? '—'} accent="amber" />
          <StatCard label="Blocked" value={stats?.blocked ?? '—'} accent="red" />
        </div>

        <div className="mt-8 flex flex-col gap-6 lg:flex-row">
          <div className="lg:w-[60%]">
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
                      filter === f
                        ? 'bg-primary/15 text-primary'
                        : 'text-text-muted hover:text-text-secondary'
                    }`}
                  >
                    {f}
                  </button>
                ))}
              </div>
            </div>

            {invoices.length === 0 ? (
              <div className="flex flex-col items-center justify-center rounded-xl border border-border bg-surface py-16 text-center">
                <svg className="mb-3 h-10 w-10 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <p className="text-sm text-text-secondary">No invoices yet. Upload one above.</p>
              </div>
            ) : (
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
            )}
          </div>

          <div className="lg:w-[40%]">
            <DecisionsPanel sections={decisions} />
          </div>
        </div>
      </div>
    </div>
  );
}
