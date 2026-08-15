import { formatConfidence } from '../utils/normalize';

function StatusIcon({ status, state }) {
  if (state === 'running' || status === 'running') {
    return (
      <span className="flex h-6 w-6 shrink-0 items-center justify-center">
        <svg className="spinner h-4 w-4 text-primary" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </span>
    );
  }

  if (state === 'pending' || status === 'pending') {
    return (
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface-elevated">
        <span className="h-1.5 w-1.5 rounded-full bg-text-muted" />
      </span>
    );
  }

  if (status === 'pass') {
    return (
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#14532d] text-success">
        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
        </svg>
      </span>
    );
  }
  if (status === 'fail') {
    return (
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#450a0a] text-danger">
        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </span>
    );
  }
  if (status === 'warn') {
    return (
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#451a03] text-warning">
        <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 2L1 21h22L12 2zm0 4l7.53 13H4.47L12 6zm-1 5v4h2v-4h-2zm0 6v2h2v-2h-2z" />
        </svg>
      </span>
    );
  }
  if (status === 'route') {
    return (
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/20 text-primary">
        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 7l5 5m0 0l-5 5m5-5H6" />
        </svg>
      </span>
    );
  }
  return (
    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface-elevated">
      <span className="h-1.5 w-1.5 rounded-full bg-text-muted" />
    </span>
  );
}

function rowStatus(agent) {
  if (agent.state === 'running') return 'running';
  if (agent.state === 'pending') return 'pending';
  return agent.status || agent.outcome;
}

function rowResult(agent) {
  if (agent.result) return agent.result;
  if (agent.state === 'running') return 'Processing...';
  if (agent.state === 'pending') return 'Waiting...';
  return '—';
}

export default function AgentTrace({ agents, animated = false, loading = false }) {
  if (loading) {
    return (
      <div className="mt-4 border-t border-border pt-4">
        <p className="text-sm text-text-muted">Loading agent trace...</p>
      </div>
    );
  }

  return (
    <div className="mt-4 space-y-2 border-t border-border pt-4">
      {agents.map((agent, index) => (
        <div
          key={agent.agent || agent.name || index}
          className={`flex items-center gap-3 rounded-lg px-2 py-2 text-sm ${animated ? 'stagger-in' : ''}`}
          style={animated ? { animationDelay: `${index * 50}ms` } : undefined}
        >
          <StatusIcon status={rowStatus(agent)} state={agent.state} />
          <span className="w-36 shrink-0 font-medium text-text-primary">{agent.agent || agent.name}</span>
          <span className="flex-1 truncate text-text-secondary">{rowResult(agent)}</span>
          {agent.confidence != null && (
            <span className="w-10 shrink-0 text-right text-xs text-text-secondary">{formatConfidence(agent.confidence)}%</span>
          )}
          {agent.confidence == null && agent.state === 'complete' && (
            <span className="w-10 shrink-0 text-right text-xs text-text-muted">—</span>
          )}
          {agent.model && (
            <span className="hidden w-24 shrink-0 truncate font-mono text-[10px] text-text-muted sm:block">
              {agent.model.replace('-turbo', '').replace('gpt-', 'gpt-')}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
