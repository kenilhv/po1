import { formatCurrency } from '../utils/formatters';

export default function ApprovalModal({
  type,
  invoice,
  onConfirm,
  onCancel,
  reason,
  onReasonChange,
  loading = false,
}) {
  if (!invoice) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="modal-enter w-full max-w-md rounded-xl border border-border bg-surface p-6 shadow-xl">
        {type === 'approve' ? (
          <>
            <h3 className="text-lg font-semibold text-text-primary">Confirm Approval</h3>
            <p className="mt-3 text-sm leading-relaxed text-text-secondary">
              Are you sure you want to approve this payment of{' '}
              <span className="font-mono font-semibold text-primary">{formatCurrency(invoice.amount)}</span>
              {' '}to <span className="font-semibold text-text-primary">{invoice.vendor}</span>?
            </p>
            <div className="mt-6 flex gap-3">
              <button
                onClick={onConfirm}
                disabled={loading}
                className="flex-1 rounded-lg border border-success bg-success/10 py-2.5 text-sm font-medium text-success transition-default hover:bg-success/20 disabled:opacity-50"
              >
                {loading ? 'Confirming...' : 'Confirm Approval'}
              </button>
              <button
                onClick={onCancel}
                className="flex-1 rounded-lg border border-border py-2.5 text-sm text-text-secondary transition-default hover:border-text-muted"
              >
                Cancel
              </button>
            </div>
          </>
        ) : (
          <>
            <h3 className="text-lg font-semibold text-text-primary">Reject Invoice</h3>
            <p className="mt-2 text-sm text-text-secondary">
              Rejecting <span className="font-mono">{invoice.number}</span> from {invoice.vendor}.
            </p>
            <textarea
              value={reason}
              onChange={(e) => onReasonChange?.(e.target.value)}
              placeholder="Optional rejection reason..."
              rows={3}
              className="mt-4 w-full resize-none rounded-lg border border-border bg-surface-elevated px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-primary focus:outline-none"
            />
            <div className="mt-4 flex gap-3">
              <button
                onClick={onConfirm}
                disabled={loading}
                className="flex-1 rounded-lg border border-danger bg-danger/10 py-2.5 text-sm font-medium text-danger transition-default hover:bg-danger/20 disabled:opacity-50"
              >
                {loading ? 'Confirming...' : 'Confirm Rejection'}
              </button>
              <button
                onClick={onCancel}
                className="flex-1 rounded-lg border border-border py-2.5 text-sm text-text-secondary transition-default hover:border-text-muted"
              >
                Cancel
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
