import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login } from '../api/auth';

export default function Login() {
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [shake, setShake] = useState(false);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const { data, error: apiError } = await login(code.trim().toUpperCase());

    setLoading(false);

    if (apiError || !data?.token) {
      setError('Invalid code. Try again.');
      setShake(true);
      setTimeout(() => setShake(false), 500);
      return;
    }

    setSuccess(true);
    setTimeout(() => {
      navigate(data.role === 'ap' ? '/ap' : '/cfo');
    }, 600);
  };

  return (
    <div className="ambient-bg page-enter flex min-h-screen items-center justify-center px-4">
      <div className="relative w-full max-w-md">
        <div className="absolute -inset-4 rounded-2xl bg-primary/5 blur-2xl" />

        <div className="relative rounded-xl border border-border bg-surface p-8">
          <div className="mb-8 flex justify-center">
            <div className="flex items-center gap-2">
              <svg className="h-6 w-6 text-primary" fill="currentColor" viewBox="0 0 24 24">
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
              </svg>
              <span className="text-xl font-bold text-primary">PayCrew</span>
            </div>
          </div>

          <h1 className="text-center text-xl font-semibold text-text-primary">Enter access code</h1>
          <p className="mt-2 text-center text-sm text-text-secondary">
            Your team lead will provide your code.
          </p>

          <form onSubmit={handleSubmit} className="mt-8">
            <input
              type="text"
              value={code}
              onChange={(e) => { setCode(e.target.value.toUpperCase()); setError(''); }}
              placeholder="XXXXXX"
              maxLength={10}
              disabled={loading}
              className={`w-full rounded-lg border bg-surface-elevated px-4 py-4 text-center font-mono text-lg uppercase tracking-widest text-text-primary placeholder:text-text-muted transition-default focus:outline-none disabled:opacity-50 ${
                shake ? 'shake border-danger' : success ? 'border-success' : 'border-border focus:border-primary'
              }`}
            />

            {error && (
              <p className="mt-2 text-center text-sm text-danger">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-primary py-3 text-sm font-medium text-white transition-default hover:bg-primary/90 disabled:opacity-70"
            >
              {loading ? (
                <>
                  <svg className="spinner h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Verifying...
                </>
              ) : (
                'Enter →'
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
