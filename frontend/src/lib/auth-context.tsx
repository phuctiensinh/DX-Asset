'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { User, TokenResponse, LoginRequest } from '@/types/auth';
import { fetchApi, getStoredToken, setStoredToken, setStoredRefreshToken, clearStoredTokens } from '@/lib/api';
import { loginWithKeycloak, logoutKeycloak } from '@/lib/oidc';
import { useRouter } from 'next/navigation';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
  login: (credentials?: LoginRequest) => Promise<void>;
  register: () => Promise<void>;
  logout: () => void;
  loadCurrentUser: (tokenOverride?: string) => Promise<User | null>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const loadCurrentUser = useCallback(async (tokenOverride?: string): Promise<User | null> => {
    const token = tokenOverride || getStoredToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return null;
    }

    try {
      const currentUser = await fetchApi<User>('/auth/me', { token });
      setUser(currentUser);
      setIsLoading(false);
      return currentUser;
    } catch (err: any) {
      // If 401 Unauthorized or invalid token, clear session completely
      clearStoredTokens();
      setUser(null);
      setIsLoading(false);
      return null;
    }
  }, []);

  useEffect(() => {
    // If currently on the authorization callback route, defer loadCurrentUser execution
    // because AuthCallbackPage will handle code exchange and invoke loadCurrentUser explicitly.
    if (typeof window !== 'undefined' && window.location.pathname.startsWith('/auth/callback')) {
      setIsLoading(false);
      return;
    }
    loadCurrentUser();
  }, [loadCurrentUser]);

  const login = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Keycloak OIDC PKCE Authorization Code Flow is the exclusive official authentication method
      await loginWithKeycloak();
    } catch (err: any) {
      setIsLoading(false);
      const msg = err?.message || 'Không thể mở trang Đăng nhập Keycloak SSO.';
      setError(msg);
      throw err;
    }
  };

  const register = async () => {
    setIsLoading(true);
    setError(null);
    try {
      await loginWithKeycloak({ promptRegister: true });
    } catch (err: any) {
      setIsLoading(false);
      setError('Không thể mở trang Đăng ký Keycloak.');
    }
  };

  const logout = () => {
    clearStoredTokens();
    setUser(null);
    setError(null);
    logoutKeycloak();
  };

  const clearError = () => {
    setError(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        error,
        login,
        register,
        logout,
        loadCurrentUser,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
