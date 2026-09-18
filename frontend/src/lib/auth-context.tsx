'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { User, TokenResponse, LoginRequest } from '@/types/auth';
import { fetchApi, getStoredToken, setStoredToken, removeStoredToken } from '@/lib/api';
import { useRouter } from 'next/navigation';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
  loadCurrentUser: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const loadCurrentUser = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const currentUser = await fetchApi<User>('/auth/me', { token });
      setUser(currentUser);
    } catch (err: any) {
      // If 401 Unauthorized or invalid token, clear token
      removeStoredToken();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCurrentUser();
  }, [loadCurrentUser]);

  const login = async (credentials: LoginRequest) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchApi<TokenResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(credentials),
      });

      setStoredToken(res.access_token);
      setUser(res.user);
      setIsLoading(false);
      router.push('/dashboard');
    } catch (err: any) {
      setIsLoading(false);
      const msg = err?.message || 'Đăng nhập thất bại. Vui lòng kiểm tra lại thông tin.';
      setError(msg);
      throw err;
    }
  };

  const logout = () => {
    removeStoredToken();
    setUser(null);
    setError(null);
    router.push('/login');
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
