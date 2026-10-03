import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { authApi, clearToken, getToken, setToken } from '../services/auth';
import { TokenResponse, User } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';

interface AuthContextValue {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  /** True while a stored token is being validated via GET /me. */
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(() => getToken());
  const [isLoading, setIsLoading] = useState(true);

  // Hydrate the session: a stored token is only trusted once the
  // backend confirms it via GET /me.
  useEffect(() => {
    let cancelled = false;

    if (!getToken()) {
      setIsLoading(false);
      return;
    }

    authApi
      .me()
      .then((response) => {
        if (!cancelled) {
          setUser(response.data);
        }
      })
      .catch(() => {
        if (!cancelled) {
          clearToken();
          setTokenState(null);
          setUser(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const applyTokenResponse = useCallback((data: TokenResponse) => {
    setToken(data.token);
    setTokenState(data.token);
    setUser(data.user);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await authApi.login(email, password);
      applyTokenResponse(response.data);
    },
    [applyTokenResponse]
  );

  const register = useCallback(
    async (email: string, password: string, fullName?: string) => {
      const response = await authApi.register(email, password, fullName);
      applyTokenResponse(response.data);
    },
    [applyTokenResponse]
  );

  const logout = useCallback(async () => {
    try {
      // Revoke the server-side session before clearing the local
      // token, otherwise revocation silently becomes a no-op.
      await authApi.logout();
    } catch {
      // The session may already be invalid; clear local state anyway.
    } finally {
      clearToken();
      setTokenState(null);
      setUser(null);
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      isAuthenticated: Boolean(user && token),
      isLoading,
      login,
      register,
      logout,
    }),
    [user, token, isLoading, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

/**
 * Route guard for protected routes: renders the wrapped routes
 * (via <Outlet />) only for authenticated users, otherwise
 * redirects to /login.
 */
export const RequireAuth: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
};
