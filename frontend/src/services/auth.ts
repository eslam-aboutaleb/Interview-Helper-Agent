import axios from 'axios';
import type { TokenResponse, User } from '../types';

const TOKEN_KEY = 'auth_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

// Dedicated axios instance instead of the shared `api` from ./api:
// api.ts imports the token helpers above for its request interceptor,
// so importing api.ts here would create a circular import. login and
// register are public; logout and me attach the session token manually
// via authHeaders().
const authHttpClient = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

function authHeaders(): { Authorization?: string } {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export const authApi = {
  register: (email: string, password: string, fullName?: string) =>
    authHttpClient.post<TokenResponse>('/api/auth/register', {
      email,
      password,
      full_name: fullName,
    }),

  login: (email: string, password: string) =>
    authHttpClient.post<TokenResponse>('/api/auth/login', {
      email,
      password,
    }),

  // Must be called while the token is still stored so the backend
  // can revoke the session.
  logout: () =>
    authHttpClient.post<void>('/api/auth/logout', undefined, {
      headers: authHeaders(),
    }),

  me: () =>
    authHttpClient.get<User>('/api/auth/me', {
      headers: authHeaders(),
    }),
};
