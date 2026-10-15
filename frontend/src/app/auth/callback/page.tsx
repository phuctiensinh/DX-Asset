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

    if (error) {
      clearStoredTokens();
      setErrorMessage('Đăng nhập bị từ chối hoặc đã bị hủy. Vui lòng thử lại.');
      return;
    }

    if (!code || !state) {
      clearStoredTokens();
      setErrorMessage('Thiếu thông tin đăng nhập trả về. Vui lòng đăng nhập lại.');
      return;
    }

    async function processCallback() {
      try {
        clearStoredTokens();

        const tokenRes = await handleOidcCallback(code!, state!);
        if (!tokenRes || !tokenRes.access_token) {
          throw new Error('Không nhận được phiên đăng nhập hợp lệ. Vui lòng đăng nhập lại.');
        }

        setStoredToken(tokenRes.access_token);
        if (tokenRes.refresh_token) {
          setStoredRefreshToken(tokenRes.refresh_token);
        }

        const user = await loadCurrentUser(tokenRes.access_token);
        if (!user) {
          throw new Error('Không thể xác nhận tài khoản của bạn trên hệ thống. Vui lòng đăng nhập lại hoặc liên hệ quản trị viên.');
        }

        router.push('/dashboard');
      } catch (err: any) {
        clearStoredTokens();
        setErrorMessage(err?.message || 'Đã xảy ra lỗi trong quá trình đăng nhập. Vui lòng thử lại.');
      }
    }

    processCallback();
  }, [searchParams, router, loadCurrentUser]);

  if (errorMessage) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
        <div className="max-w-md w-full bg-white border border-slate-200 rounded-2xl p-6 text-center text-slate-800 shadow-xl">
          <div className="w-12 h-12 rounded-2xl bg-rose-50 border border-rose-100 flex items-center justify-center text-rose-600 mx-auto mb-4">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-slate-900 mb-2">Đăng nhập Không Thành công</h2>
          <p className="text-sm text-slate-600 mb-6">{errorMessage}</p>
          <button
            onClick={() => router.push('/login')}
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl transition-all text-sm shadow-md shadow-indigo-600/20"
          >
            Quay lại trang Đăng nhập
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="flex flex-col items-center space-y-4">
        <div className="w-14 h-14 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shadow-md animate-pulse">
          <ShieldCheck className="w-8 h-8" />
        </div>
        <div className="flex items-center space-x-3 text-slate-700 font-medium text-sm">
          <Loader2 className="w-5 h-5 animate-spin text-indigo-600" />
          <span>Đang hoàn tất đăng nhập...</span>
        </div>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-slate-50">
          <div className="flex flex-col items-center space-y-4">
            <div className="w-14 h-14 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shadow-md animate-pulse">
              <ShieldCheck className="w-8 h-8" />
            </div>
            <div className="flex items-center space-x-3 text-slate-700 font-medium text-sm">
              <Loader2 className="w-5 h-5 animate-spin text-indigo-600" />
              <span>Đang chuẩn bị đăng nhập...</span>
            </div>
          </div>
        </div>
      }
    >
      <AuthCallbackContent />
    </Suspense>
  );
}
