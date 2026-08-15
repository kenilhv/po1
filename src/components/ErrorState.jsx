export default function ErrorState({ message, onRetry }) {
  const isServer = message?.includes('Server') || message?.includes('500');
  const isNetwork = message?.includes('Connection') || message?.includes('network');

  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-border bg-surface px-6 py-12 text-center">
      <svg className="mb-3 h-10 w-10 text-danger" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p className="text-sm text-text-secondary">
        {message || (isServer ? 'Server error. Try again in a moment.' : isNetwork ? 'Connection error. Check your network.' : 'Something went wrong.')}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 rounded-lg border border-primary px-4 py-2 text-sm text-primary transition-default hover:bg-primary/10"
        >
          Retry
        </button>
      )}
    </div>
  );
}

function SkeletonBlock({ className = '' }) {
  return <div className={`animate-pulse rounded-lg bg-surface-elevated ${className}`} />;
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <SkeletonBlock key={i} className="h-20" />
        ))}
      </div>
      <SkeletonBlock className="h-64" />
    </div>
  );
}
