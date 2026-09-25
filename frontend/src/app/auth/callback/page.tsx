'use client';

import React, { useEffect, useState, useRef, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { handleOidcCallback } from '@/lib/oidc';
import { setStoredToken, setStoredRefreshToken, clearStoredTokens } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { Loader2, AlertTriangle, ShieldCheck } from 'lucide-react';

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { loadCurrentUser } = useAuth();

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const processedRef = useRef(false);

  useEffect(() => {
    if (processedRef.current) return;
    processedRef.current = true;

    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const error = searchParams.get('error');
    const errorDescription = searchParams.get('error_description');

    if (error) {
      clearStoredTokens();
      setErrorMessage(errorDescription || `Xác thực bị từ chối: ${error}`);
      return;
    }

    if (!code || !state) {
      clearStoredTokens();
      setErrorMessage('Thiếu mã Authorization Code hoặc State từ Keycloak.');
      return;
    }

    async function processCallback() {
      try {
        clearStoredTokens();

        const tokenRes = await handleOidcCallback(code!, state!);
        if (!tokenRes || !tokenRes.access_token) {
          throw new Error('Không nhận được Access Token hợp lệ từ Keycloak.');
        }

        setStoredToken(tokenRes.access_token);
        if (tokenRes.refresh_token) {
          setStoredRefreshToken(tokenRes.refresh_token);
        }

        const user = await loadCurrentUser(tokenRes.access_token);
        if (!user) {
          throw new Error('Xác thực thông tin người dùng thất bại từ backend FastAPI (401 Unauthorized).');
        }

        router.push('/dashboard');
      } catch (err: any) {
        clearStoredTokens();
        setErrorMessage(err?.message || 'Xảy ra lỗi trong quá trình trao đổi Keycloak Token.');
      }
    }

    processCallback();
  }, [searchParams, router, loadCurrentUser]);

  if (errorMessage) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 p-4">
        <div className="max-w-md w-full bg-slate-800 border border-slate-700 rounded-2xl p-6 text-center text-slate-100 shadow-2xl">
          <div className="w-12 h-12 rounded-2xl bg-red-500/10 border border-red-500/30 flex items-center justify-center text-red-400 mx-auto mb-4">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Đăng nhập Không Thành công</h2>
          <p className="text-sm text-slate-300 mb-6">{errorMessage}</p>
          <button
            onClick={() => router.push('/login')}
            className="w-full py-3 bg-sky-600 hover:bg-sky-500 text-white font-semibold rounded-xl transition-all text-sm shadow-md"
          >
            Quay lại trang Đăng nhập
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900">
      <div className="flex flex-col items-center space-y-4">
        <div className="w-12 h-12 rounded-2xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400 animate-pulse">
          <ShieldCheck className="w-7 h-7" />
        </div>
        <div className="flex items-center space-x-3 text-slate-300 font-medium text-sm">
          <Loader2 className="w-5 h-5 animate-spin text-sky-400" />
          <span>Đang hoàn tất xác thực từ Keycloak OIDC...</span>
        </div>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-slate-900">
          <div className="flex flex-col items-center space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400 animate-pulse">
              <ShieldCheck className="w-7 h-7" />
            </div>
            <div className="flex items-center space-x-3 text-slate-300 font-medium text-sm">
              <Loader2 className="w-5 h-5 animate-spin text-sky-400" />
              <span>Đang tải tham số xác thực...</span>
            </div>
          </div>
        </div>
      }
    >
      <AuthCallbackContent />
    </Suspense>
  );
}
