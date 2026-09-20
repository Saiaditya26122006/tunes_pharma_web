import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';

import * as authApi from '../api/auth';
import { setOnAuthFailure } from '../api/client';
import * as tokenStorage from './tokenStorage';
import type { DoctorProfile } from '../api/types';
import { ApiError } from '../api/types';

interface AuthState {
  doctor: DoctorProfile | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [doctor, setDoctor] = useState<DoctorProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const mountedRef = useRef(true);

  const clearAuth = useCallback(async () => {
    await tokenStorage.clearTokens();
    if (mountedRef.current) {
      setDoctor(null);
    }
  }, []);

  useEffect(() => {
    setOnAuthFailure(() => {
      clearAuth();
    });
  }, [clearAuth]);

  useEffect(() => {
    mountedRef.current = true;
    restoreSession();
    return () => {
      mountedRef.current = false;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function restoreSession() {
    try {
      const tokens = await tokenStorage.getTokens();
      if (!tokens) return;

      const profile = await authApi.getMe();
      if (mountedRef.current) {
        setDoctor(profile);
      }
    } catch {
      await tokenStorage.clearTokens();
    } finally {
      if (mountedRef.current) {
        setIsLoading(false);
      }
    }
  }

  const login = useCallback(async (username: string, password: string) => {
    const result = await authApi.login(username, password);
    await tokenStorage.saveTokens(
      result.tokens.access_token,
      result.tokens.refresh_token,
    );
    const profile = await authApi.getMe();
    if (mountedRef.current) {
      setDoctor(profile);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      const refreshToken = await tokenStorage.getRefreshToken();
      if (refreshToken) {
        await authApi.logout(refreshToken).catch(() => {});
      }
    } finally {
      await clearAuth();
    }
  }, [clearAuth]);

  const refreshSession = useCallback(async () => {
    const refreshToken = await tokenStorage.getRefreshToken();
    if (!refreshToken) {
      await clearAuth();
      throw new ApiError('UNAUTHORIZED', 'No refresh token available.', 401);
    }

    const result = await authApi.refresh(refreshToken);
    await tokenStorage.saveTokens(
      result.tokens.access_token,
      result.tokens.refresh_token,
    );

    const profile = await authApi.getMe();
    if (mountedRef.current) {
      setDoctor(profile);
    }
  }, [clearAuth]);

  return (
    <AuthContext.Provider
      value={{
        doctor,
        isLoading,
        isAuthenticated: doctor !== null,
        login,
        logout,
        refreshSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}
