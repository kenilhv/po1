const riskStyles = {
  LOW: 'bg-[#14532d] text-success',
  MEDIUM: 'bg-[#451a03] text-warning',
  HIGH: 'bg-[#431407] text-orange-400',
  CRITICAL: 'bg-[#450a0a] text-danger pulse-critical',
};

export default function RiskBadge({ risk, size = 'sm' }) {
  const sizeClasses = size === 'lg'
    ? 'px-3 py-1 text-sm font-semibold'
    : 'px-2 py-0.5 text-xs font-medium';

  return (
    <span
      className={`inline-flex items-center rounded-md font-mono uppercase tracking-wide ${sizeClasses} ${riskStyles[risk] || riskStyles.LOW}`}
    >
      {risk}
    </span>
  );
}
