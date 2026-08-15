const BASE_URL = import.meta.env.VITE_API_BASE_URL;

export function getToken() {
  return localStorage.getItem('paycrew_token');
}

export function clearAuth() {
  localStorage.removeItem('paycrew_token');
  localStorage.removeItem('paycrew_role');
  localStorage.removeItem('paycrew_auth');
}

function handle401() {
  clearAuth();
  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
}

function parseErrorBody(body, status) {
  if (typeof body === 'string') return body.slice(0, 200);
  return body?.detail || body?.message || body?.error || `Request failed (${status})`;
}

export async function apiFetch(path, options = {}) {
  const headers = {
    'ngrok-skip-browser-warning': 'true',
    ...options.headers,
  };

  if (!options.skipJson && !(options.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  }

  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers,
    });

    if (res.status === 401) {
      handle401();
      return { data: null, error: 'Session expired', status: 401 };
    }

    if (res.status === 403) {
      return { data: null, error: "You don't have permission to view this.", status: 403 };
    }

    if (options.responseType === 'blob') {
      if (!res.ok) {
        const text = await res.text();
        let body;
        try { body = JSON.parse(text); } catch { body = text; }
        return { data: null, error: parseErrorBody(body, res.status), status: res.status };
      }
      return { data: await res.blob(), error: null, status: res.status };
    }

    const text = await res.text();
    let body = null;
    try {
      body = text ? JSON.parse(text) : null;
    } catch {
      body = text;
    }

    if (!res.ok) {
      return { data: null, error: parseErrorBody(body, res.status), status: res.status };
    }

    return { data: body, error: null, status: res.status };
  } catch {
    return {
      data: null,
      error: 'Connection error. Check your network.',
      status: 0,
      networkError: true,
    };
  }
}

export async function uploadFile(path, file) {
  const formData = new FormData();
  formData.append('file', file);

  const headers = {
    'ngrok-skip-browser-warning': 'true',
  };

  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (res.status === 401) {
      handle401();
      return { data: null, error: 'Session expired', status: 401 };
    }

    if (res.status === 403) {
      return { data: null, error: "You don't have permission to view this.", status: 403 };
    }

    const text = await res.text();
    let body = null;
    try {
      body = text ? JSON.parse(text) : null;
    } catch {
      body = text;
    }

    if (!res.ok) {
      return { data: null, error: parseErrorBody(body, res.status), status: res.status };
    }

    return { data: body, error: null, status: res.status };
  } catch {
    return {
      data: null,
      error: 'Connection error. Check your network.',
      status: 0,
      networkError: true,
    };
  }
}
