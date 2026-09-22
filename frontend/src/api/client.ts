/**
 * Centralized API client for OpsOS.
 *
 * Handles base URL, auth token attachment, automated demo authentication
 * for local development, JSON parsing, and friendly error reporting.
 */

const API_BASE = '/api/v1';

let authToken: string | null = localStorage.getItem('opsos_access_token');

export async function ensureAuthToken(): Promise<string> {
  if (authToken) {
    return authToken;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: 'demo@opsos.local',
        password: 'DemoPassword123',
      }),
    });
  } catch (netErr) {
    console.error('Network failure during authentication:', netErr);
    throw new Error('Unable to connect to OpsOS backend. Ensure backend is running on port 8000.');
  }

  if (!response.ok) {
    // Try registering demo user first if login failed
    let regRes: Response;
    try {
      regRes = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'demo@opsos.local',
          password: 'DemoPassword123',
        }),
      });
    } catch (netErr) {
      console.error('Network failure during demo registration:', netErr);
      throw new Error('Unable to connect to OpsOS backend. Ensure backend is running on port 8000.');
    }

    if (regRes.ok || regRes.status === 409 || regRes.status === 422) {
      let retryLogin: Response;
      try {
        retryLogin = await fetch(`${API_BASE}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: 'demo@opsos.local',
            password: 'DemoPassword123',
          }),
        });
      } catch (netErr) {
        console.error('Network failure during login retry:', netErr);
        throw new Error('Unable to connect to OpsOS backend. Ensure backend is running on port 8000.');
      }

      if (retryLogin.ok) {
        const data = await retryLogin.json();
        authToken = data.access_token;
        localStorage.setItem('opsos_access_token', authToken!);
        return authToken!;
      }

      let errorDetail = '';
      try {
        const errJson = await retryLogin.json();
        errorDetail = typeof errJson.detail === 'string' ? `: ${errJson.detail}` : '';
      } catch {
        // body not json
      }
      throw new Error(`Authentication failed (${retryLogin.status})${errorDetail}`);
    }

    let regErrorDetail = '';
    try {
      const errJson = await regRes.json();
      regErrorDetail = typeof errJson.detail === 'string' ? `: ${errJson.detail}` : '';
    } catch {
      // body not json
    }
    throw new Error(`Authentication failed during registration (${regRes.status})${regErrorDetail}`);
  }

  const data = await response.json();
  authToken = data.access_token;
  localStorage.setItem('opsos_access_token', authToken!);
  return authToken!;
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await ensureAuthToken();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
    ...((options.headers as Record<string, string>) || {}),
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMessage = `Request failed (${response.status})`;
    try {
      const errBody = await response.json();
      if (errBody?.detail) {
        if (typeof errBody.detail === 'string') {
          errorMessage = errBody.detail;
        } else if (Array.isArray(errBody.detail) && errBody.detail[0]?.msg) {
          errorMessage = errBody.detail[0].msg;
        }
      }
    } catch {
      // response was not json
    }
    const error = new Error(errorMessage);
    (error as unknown as { status: number }).status = response.status;
    throw error;
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}
