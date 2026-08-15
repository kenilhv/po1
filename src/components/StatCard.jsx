export default function StatCard({ label, value, accent }) {
  const accentColors = {
    green: 'text-success',
    amber: 'text-warning',
    red: 'text-danger',
    indigo: 'text-primary',
    default: 'text-text-primary',
  };

  return (
    <div className="card-hover rounded-xl border border-border bg-surface p-5">
      <p className="text-sm text-text-secondary">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${accentColors[accent] || accentColors.default}`}>
        {value}
      </p>
    </div>
  );
}
