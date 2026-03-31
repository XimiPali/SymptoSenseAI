/**
 * contexts/AuthContext.tsx
 * ------------------------
 * Provides authentication state (user, token) globally.
 * Wrap <App> with <AuthProvider> so every component can
 * call useAuth() to read/set auth state.
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authAPI, UserResponse } from '../api/client';

interface AuthState {
  user: UserResponse | null;
  token: string | null;
  loading: boolean;
  login:  (token: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user,    setUser]    = useState<UserResponse | null>(null);
  const [token,   setToken]   = useState<string | null>(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  // On mount, if there's a stored token fetch the profile
  useEffect(() => {
    if (token) {
      authAPI.me()
        .then((res) => setUser(res.data))
        .catch(() => {
          localStorage.removeItem('token');
          setToken(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [token]);

  const login = async (newToken: string) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
    const res = await authAPI.me();
    setUser(res.data);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
