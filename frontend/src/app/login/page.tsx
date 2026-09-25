'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth-context';
import { useRouter } from 'next/navigation';
import {
  ShieldCheck,
  AlertCircle,
  Loader2,
  KeyRound,
  UserPlus,
  ArrowRight,
  ShieldAlert,
  Server,
  Lock,
} from 'lucide-react';

export default function LoginPage() {
  const { login, register, isAuthenticated, isLoading, error, clearError } = useAuth();
  const router = useRouter();

  const [isKeycloakRedirecting, setIsKeycloakRedirecting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isLoading, isAuthenticated, router]);

  const handleKeycloakLogin = async () => {
    setLocalError(null);
    clearError();
    setIsKeycloakRedirecting(true);
    try {
      await login(); // Triggers Keycloak OIDC PKCE Authorization Code Flow
    } catch (err: any) {
      setIsKeycloakRedirecting(false);
      setLocalError(err?.message || 'Không thể kết nối đến Keycloak SSO IdP.');
    }
  };

  const handleKeycloakRegister = async () => {
    setLocalError(null);
    clearError();
    setIsKeycloakRedirecting(true);
    try {
      await register(); // Triggers Keycloak Self-Registration Flow
    } catch (err: any) {
      setIsKeycloakRedirecting(false);
      setLocalError(err?.message || 'Không thể mở trang Đăng ký Keycloak.');
    }
  };

  const activeError = localError || error;

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 bg-opacity-95 p-4 sm:p-6 lg:p-8 relative overflow-hidden">
      {/* Background decoration gradients */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-sky-500/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-indigo-500/20 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md bg-slate-800/90 backdrop-blur-md border border-slate-700/60 rounded-2xl shadow-2xl p-6 sm:p-8 relative z-10 text-slate-100">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-sky-500/10 border border-sky-500/30 text-sky-400 mb-4 shadow-inner">
            <ShieldCheck className="w-8 h-8" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
            DX-Asset
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Hệ thống Quản lý Vòng đời Tài sản số Doanh nghiệp
          </p>
        </div>

        {/* Error Alert Box */}
        {activeError && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start space-x-3 text-red-400 animate-fadeIn text-sm">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div className="flex-1 font-medium">{activeError}</div>
          </div>
        )}

        {/* Primary Action: Keycloak OIDC Authentication Buttons */}
        <div className="space-y-4">
          <button
            type="button"
            onClick={handleKeycloakLogin}
            disabled={isKeycloakRedirecting}
            className="w-full py-3.5 px-4 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white font-semibold rounded-xl shadow-lg shadow-sky-500/25 transition-all flex items-center justify-center space-x-3 disabled:opacity-60 disabled:cursor-not-allowed group"
          >
            {isKeycloakRedirecting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Đang chuyển hướng sang Keycloak...</span>
              </>
            ) : (
              <>
                <KeyRound className="w-5 h-5 text-sky-200 group-hover:scale-110 transition-transform" />
                <span>Đăng nhập bằng Keycloak SSO (OIDC)</span>
                <ArrowRight className="w-4 h-4 ml-1 opacity-70 group-hover:translate-x-1 transition-transform" />
              </>
            )}
          </button>

          <button
            type="button"
            onClick={handleKeycloakRegister}
            disabled={isKeycloakRedirecting}
            className="w-full py-3 px-4 bg-slate-700/60 hover:bg-slate-700/90 border border-slate-600/80 text-slate-200 hover:text-white font-semibold rounded-xl transition-all flex items-center justify-center space-x-2 disabled:opacity-60 text-sm"
          >
            <UserPlus className="w-4 h-4 text-emerald-400" />
            <span>Đăng ký Tài khoản Mới (Self-Registration)</span>
          </button>
        </div>

        {/* Identity & Authorization Architecture Info Card */}
        <div className="mt-8 pt-6 border-t border-slate-700/60">
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-700/50 space-y-2.5 text-xs text-slate-300">
            <div className="flex items-center space-x-2 font-semibold text-sky-400">
              <Server className="w-4 h-4" />
              <span>Hạ tầng Xác thực Chính thức Keycloak OIDC</span>
            </div>
            <p className="text-slate-400 leading-relaxed">
              DX-Asset áp dụng chuẩn bảo mật OIDC Authorization Code Flow với PKCE. Mật khẩu và thông tin đăng nhập được xác thực tuyệt đối tại Server Keycloak IdP.
            </p>
            <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
              <span className="flex items-center space-x-1">
                <Lock className="w-3.5 h-3.5 text-emerald-400" />
                <span>Source of Truth Role: PostgreSQL</span>
              </span>
              <span className="flex items-center space-x-1 text-amber-400 font-mono">
                <ShieldAlert className="w-3.5 h-3.5" />
                <span>Single Owner</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
