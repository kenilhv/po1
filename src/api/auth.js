import { apiFetch, clearAuth } from './client';

export async function login(code) {
  const result = await apiFetch('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ code }),
  });

  if (result.data?.token) {
    localStorage.setItem('paycrew_token', result.data.token);
    localStorage.setItem('paycrew_role', result.data.role);
  }

  return result;
}

export async function logout() {
  const result = await apiFetch('/auth/logout', { method: 'POST' });
  clearAuth();
  return result;
}

export async function me() {
  return apiFetch('/auth/me');
}
