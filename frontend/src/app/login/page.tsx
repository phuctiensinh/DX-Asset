'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth-context';
import { useRouter } from 'next/navigation';
import {
  ShieldCheck,
  Lock,
  Mail,
  Eye,
  EyeOff,
  AlertCircle,
  Loader2,
  Building2,
} from 'lucide-react';

export default function LoginPage() {
  const { login, isAuthenticated, isLoading, error, clearError } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isLoading, isAuthenticated, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!email.trim()) {
      setLocalError('Vui lòng nhập địa chỉ email.');
      return;
    }
    if (!password) {
      setLocalError('Vui lòng nhập mật khẩu.');
      return;
    }

    setIsSubmitting(true);
    try {
      await login({ email: email.trim(), password });
    } catch (err) {
      // Error handled inside AuthContext or setting local error
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDemoFill = (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword('password123');
    setLocalError(null);
    clearError();
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

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
              Email tài khoản
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Mail className="w-5 h-5" />
              </div>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@dxasset.local"
                className="w-full pl-11 pr-4 py-3 bg-slate-900/80 border border-slate-700 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 rounded-xl text-sm text-slate-100 placeholder-slate-500 transition-all outline-none"
                disabled={isSubmitting}
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
              Mật khẩu
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Lock className="w-5 h-5" />
              </div>
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-11 pr-11 py-3 bg-slate-900/80 border border-slate-700 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 rounded-xl text-sm text-slate-100 placeholder-slate-500 transition-all outline-none"
                disabled={isSubmitting}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-200 transition-colors"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3.5 px-4 bg-gradient-to-r from-sky-500 to-sky-600 hover:from-sky-400 hover:to-sky-500 text-white font-semibold rounded-xl shadow-lg shadow-sky-500/25 transition-all flex items-center justify-center space-x-2 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Đang đăng nhập...</span>
              </>
            ) : (
              <span>Đăng nhập hệ thống</span>
            )}
          </button>
        </form>

        {/* Demo Accounts Quick-Fill Section */}
        <div className="mt-8 pt-6 border-t border-slate-700/60">
          <div className="flex items-center space-x-2 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            <Building2 className="w-4 h-4 text-sky-400" />
            <span>Tài khoản Demo Local (Click để thử)</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <button
              type="button"
              onClick={() => handleDemoFill('admin@dxasset.local')}
              className="p-2.5 rounded-lg bg-slate-900/50 hover:bg-slate-700/60 border border-slate-700/50 text-left transition-colors"
            >
              <div className="font-semibold text-sky-400">ADMIN</div>
              <div className="text-slate-400 truncate">admin@dxasset.local</div>
            </button>

            <button
              type="button"
              onClick={() => handleDemoFill('it_manager@dxasset.local')}
              className="p-2.5 rounded-lg bg-slate-900/50 hover:bg-slate-700/60 border border-slate-700/50 text-left transition-colors"
            >
              <div className="font-semibold text-indigo-400">IT MANAGER</div>
              <div className="text-slate-400 truncate">it_manager@dxasset.local</div>
            </button>

            <button
              type="button"
              onClick={() => handleDemoFill('manager@dxasset.local')}
              className="p-2.5 rounded-lg bg-slate-900/50 hover:bg-slate-700/60 border border-slate-700/50 text-left transition-colors"
            >
              <div className="font-semibold text-emerald-400">MANAGER</div>
              <div className="text-slate-400 truncate">manager@dxasset.local</div>
            </button>

            <button
              type="button"
              onClick={() => handleDemoFill('employee1@dxasset.local')}
              className="p-2.5 rounded-lg bg-slate-900/50 hover:bg-slate-700/60 border border-slate-700/50 text-left transition-colors"
            >
              <div className="font-semibold text-amber-400">EMPLOYEE</div>
              <div className="text-slate-400 truncate">employee1@dxasset.local</div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
