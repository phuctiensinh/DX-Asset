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
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4 sm:p-6 lg:p-8 relative overflow-hidden">
      {/* Subtle Background decoration gradients for Light UI */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-indigo-200/50 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-sky-200/50 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md bg-white border border-slate-200/90 rounded-2xl shadow-xl p-6 sm:p-8 relative z-10 text-slate-900">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-600 text-white mb-4 shadow-md shadow-indigo-500/30">
            <ShieldCheck className="w-8 h-8" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
            DX-Asset
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1 font-medium">
            Hệ thống Quản lý Vòng đời Tài sản số Doanh nghiệp
          </p>
        </div>

        {/* Error Alert Box */}
        {activeError && (
          <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-start space-x-3 text-rose-800 animate-fadeIn text-xs font-semibold shadow-sm">
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">{activeError}</div>
          </div>
        )}

        {/* Primary Action: Keycloak OIDC Authentication Buttons */}
        <div className="space-y-3.5">
          <button
            type="button"
            onClick={handleKeycloakLogin}
            disabled={isKeycloakRedirecting}
            className="w-full py-3.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs sm:text-sm rounded-xl shadow-md shadow-indigo-500/25 transition-all flex items-center justify-center space-x-2.5 disabled:opacity-60 disabled:cursor-not-allowed group"
          >
            {isKeycloakRedirecting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Đang chuyển hướng sang Keycloak...</span>
              </>
            ) : (
              <>
                <KeyRound className="w-4 h-4 text-indigo-200 group-hover:scale-110 transition-transform" />
                <span>Đăng nhập bằng Keycloak SSO (OIDC)</span>
                <ArrowRight className="w-4 h-4 opacity-70 group-hover:translate-x-1 transition-transform" />
              </>
            )}
          </button>

          <button
            type="button"
            onClick={handleKeycloakRegister}
            disabled={isKeycloakRedirecting}
            className="w-full py-3 px-4 bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 hover:text-slate-900 font-semibold rounded-xl transition-all flex items-center justify-center space-x-2 disabled:opacity-60 text-xs shadow-sm"
          >
            <UserPlus className="w-4 h-4 text-emerald-600" />
            <span>Đăng ký Tài khoản Mới (Self-Registration)</span>
          </button>
        </div>

        {/* Identity & Authorization Architecture Info Card */}
        <div className="mt-8 pt-6 border-t border-slate-100">
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2.5 text-xs text-slate-600 font-medium">
            <div className="flex items-center space-x-2 font-bold text-indigo-600">
              <Server className="w-4 h-4 text-indigo-600" />
              <span>Hạ tầng Xác thực Chính thức Keycloak OIDC</span>
            </div>
            <p className="text-slate-500 text-[11px] leading-relaxed">
              DX-Asset áp dụng chuẩn bảo mật OIDC Authorization Code Flow với PKCE. Mật khẩu và thông tin đăng nhập được xác thực tuyệt đối tại Server Keycloak IdP.
            </p>
            <div className="pt-2 border-t border-slate-200/80 flex items-center justify-between text-[11px]">
              <span className="flex items-center space-x-1 text-slate-700 font-medium">
                <Lock className="w-3.5 h-3.5 text-emerald-600" />
                <span>Source of Truth Role: PostgreSQL</span>
              </span>
              <span className="flex items-center space-x-1 text-amber-700 font-mono font-bold">
                <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
                <span>Single Owner</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

