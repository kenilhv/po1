export default function LoadingScreen() {
  return (
    <div className="ambient-bg flex min-h-screen items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="flex items-center gap-2">
          <svg className="h-8 w-8 text-primary" fill="currentColor" viewBox="0 0 24 24">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
          </svg>
          <span className="text-2xl font-bold text-primary">PayCrew</span>
        </div>
        <svg className="spinner h-6 w-6 text-primary" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
    </div>
  );
}
