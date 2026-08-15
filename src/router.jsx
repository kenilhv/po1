import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { me } from './api/auth';
import LoadingScreen from './components/LoadingScreen';

export function ProtectedRoute({ children, requiredRole }) {
  const [status, setStatus] = useState('loading');

  useEffect(() => {
    let cancelled = false;

    async function verify() {
      const token = localStorage.getItem('paycrew_token');
      if (!token) {
        if (!cancelled) setStatus('denied');
        return;
      }

      const { data, error } = await me();
      if (cancelled) return;

      if (error || !data?.role) {
        setStatus('denied');
        return;
      }

      if (requiredRole && data.role !== requiredRole) {
        setStatus('denied');
        return;
      }

      setStatus('ok');
    }

    verify();
    return () => { cancelled = true; };
  }, [requiredRole]);

  if (status === 'loading') return <LoadingScreen />;
  if (status === 'denied') return <Navigate to="/login" replace />;
  return children;
}

export default ProtectedRoute;
