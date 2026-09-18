'use client';

import React from 'react';
import { useAuth } from '@/lib/auth-context';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { Navbar } from '@/components/Navbar';
import Link from 'next/link';
import {
  User as UserIcon,
  Mail,
  Shield,
  CheckCircle2,
  Boxes,
  KeyRound,
  Calendar,
  ArrowRight,
} from 'lucide-react';

function DashboardContent() {
  const { user, logout } = useAuth();

  const getRoleBadgeStyle = (role?: string) => {
    switch (role) {
      case 'ADMIN':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      case 'IT_ASSET_MANAGER':
        return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30';
      case 'MANAGER':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'EMPLOYEE':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/30';
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      <Navbar />

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        {/* Welcome Banner */}
        <div className="relative overflow-hidden bg-gradient-to-r from-sky-900/40 via-indigo-900/30 to-slate-800/80 border border-slate-700/70 rounded-2xl p-6 sm:p-8 shadow-xl">
          <div className="relative z-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-sky-500/10 border border-sky-500/30 text-sky-400 text-xs font-medium mb-3">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Phiên làm việc xác thực thành công (Phase 5C)</span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                Xin chào, {user?.full_name}!
              </h2>
              <p className="text-slate-300 text-sm mt-1">
                Bạn đang truy cập hệ thống quản lý tài sản với vai trò{' '}
                <span className="font-semibold text-sky-400">{user?.role}</span>.
              </p>
            </div>

            <Link
              href="/assets"
              className="flex items-center space-x-2 px-5 py-3 bg-sky-500 hover:bg-sky-400 text-white text-xs font-semibold rounded-xl shadow-lg shadow-sky-500/20 transition-all"
            >
              <Boxes className="w-4 h-4" />
              <span>Đi tới Quản lý Tài sản</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>

        {/* Account & Session Detail Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* User Info Card */}
          <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl p-6 shadow-lg space-y-4">
            <div className="flex items-center space-x-3 text-sky-400 font-semibold text-sm border-b border-slate-700/60 pb-3">
              <UserIcon className="w-5 h-5" />
              <span>Thông tin Tài khoản</span>
            </div>
            <div className="space-y-3 text-sm">
              <div>
                <div className="text-xs text-slate-400 uppercase font-medium">Họ và tên</div>
                <div className="font-semibold text-white mt-0.5">{user?.full_name}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400 uppercase font-medium">Email đăng nhập</div>
                <div className="font-semibold text-slate-200 mt-0.5 flex items-center space-x-2">
                  <Mail className="w-4 h-4 text-slate-400" />
                  <span>{user?.email}</span>
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-400 uppercase font-medium">Phân quyền (Role)</div>
                <div className="mt-1">
                  <span
                    className={`inline-block px-2.5 py-1 rounded-lg border text-xs font-bold ${getRoleBadgeStyle(
                      user?.role
                    )}`}
                  >
                    {user?.role}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Session Security Card */}
          <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl p-6 shadow-lg space-y-4">
            <div className="flex items-center space-x-3 text-emerald-400 font-semibold text-sm border-b border-slate-700/60 pb-3">
              <Shield className="w-5 h-5" />
              <span>Bảo mật & Phiên JWT</span>
            </div>
            <div className="space-y-3 text-sm">
              <div>
                <div className="text-xs text-slate-400 uppercase font-medium">Trạng thái tài khoản</div>
                <div className="font-semibold text-emerald-400 mt-0.5 flex items-center space-x-1.5">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Hoạt động (Active)</span>
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-400 uppercase font-medium">Cơ chế xác thực</div>
                <div className="font-semibold text-slate-200 mt-0.5 flex items-center space-x-2">
                  <KeyRound className="w-4 h-4 text-indigo-400" />
                  <span>JWT Bearer Access Token</span>
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-400 uppercase font-medium">Thời điểm tạo tài khoản</div>
                <div className="font-semibold text-slate-300 mt-0.5 flex items-center space-x-2 text-xs">
                  <Calendar className="w-4 h-4 text-slate-400" />
                  <span>
                    {user?.created_at ? new Date(user.created_at).toLocaleString('vi-VN') : 'N/A'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* System Status Card */}
          <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl p-6 shadow-lg space-y-4">
            <div className="flex items-center space-x-3 text-indigo-400 font-semibold text-sm border-b border-slate-700/60 pb-3">
              <Boxes className="w-5 h-5" />
              <span>Trạng thái Hệ thống</span>
            </div>
            <div className="space-y-3 text-xs text-slate-300">
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-700/50 space-y-1">
                <div className="font-semibold text-slate-200">Backend API</div>
                <div className="text-slate-400">http://localhost:8000/api/v1</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-700/50 space-y-1">
                <div className="font-semibold text-slate-200">Kế hoạch tiếp theo</div>
                <div className="text-slate-400">Phase 5C+: Asset CRUD & Assignment Management</div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
