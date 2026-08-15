import { Link } from 'react-router-dom';
import { logout } from '../api/auth';
import { clearAuth } from '../api/client';

export default function Navbar({ title, showChangeUser = false }) {
  const handleChangeUser = async () => {
    await logout();
    clearAuth();
    window.location.href = '/login';
  };

  return (
    <nav className="sticky top-0 z-50 border-b border-border bg-bg/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <Link to="/" className="flex items-center gap-2 transition-default hover:opacity-80">
          <svg className="h-5 w-5 text-primary" fill="currentColor" viewBox="0 0 24 24">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
          </svg>
          <span className="text-lg font-bold text-primary">PayCrew</span>
        </Link>

        {title && (
          <span className="hidden text-sm text-text-secondary sm:block">{title}</span>
        )}

        {showChangeUser ? (
          <button
            onClick={handleChangeUser}
            className="rounded-lg border border-border px-3 py-1.5 text-xs text-text-secondary transition-default hover:border-primary hover:text-primary"
          >
            Change User
          </button>
        ) : (
          <div className="w-20" />
        )}
      </div>
    </nav>
  );
}
