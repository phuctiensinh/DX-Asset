'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { Navbar } from '@/components/Navbar';
import { fetchApi } from '@/lib/api';
import Link from 'next/link';
import {
  Boxes,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Building2,
  Activity,
  ArrowRight,
  RefreshCw,
  UserCheck,
  Wrench,
  XCircle,
  Archive,
  FileQuestion,
  TrendingUp,
  Shield,
} from 'lucide-react';

interface AssetStatusCounts {
  total: number;
  by_status: Record<string, number>;
  in_stock: number;
  assigned: number;
  in_maintenance: number;
  damaged: number;
  retired: number;
  lost: number;
  inactive: number;
}

interface AssignmentStatusCounts {
  total: number;
  by_status: Record<string, number>;
  active: number;
  returned: number;
}

interface IncidentStatusCounts {
  total: number;
  by_status: Record<string, number>;
  open: number;
  in_review: number;
  in_progress: number;
  waiting_for_info: number;
  resolved: number;
  closed: number;
  cancelled: number;
  pending: number;
}

interface DepartmentAssetStats {
  department_id: number | null;
  department_code: string;
  department_name: string;
  total_assets: number;
  assigned_assets: number;
  in_stock_assets: number;
}

interface RecentActivityItem {
  id: number;
  asset_id: number;
  asset_code: string;
  asset_name: string;
  action_type: string;
  performed_by_id: number | null;
  performed_by_name: string | null;
  details: string | null;
  created_at: string;
}

interface DashboardSummaryResponse {
  assets: AssetStatusCounts;
  assignments: AssignmentStatusCounts;
  incidents: IncidentStatusCounts;
  departments: DepartmentAssetStats[];
  recent_activities: RecentActivityItem[];
}

function DashboardContent() {
  const { user } = useAuth();
  const [data, setData] = useState<DashboardSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchApi<DashboardSummaryResponse>('/dashboard/summary');
      setData(res);
    } catch (err: any) {
      setError(err?.message || 'Không thể tải dữ liệu bảng điều khiển dashboard.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

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

  const getActionTypeBadge = (actionType: string) => {
    switch (actionType) {
      case 'CREATED':
        return { label: 'Tạo tài sản', style: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' };
      case 'ASSIGNED':
        return { label: 'Cấp phát', style: 'bg-sky-500/10 text-sky-400 border-sky-500/30' };
      case 'RETURNED':
        return { label: 'Thu hồi', style: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30' };
      case 'INCIDENT_REPORTED':
        return { label: 'Báo sự cố', style: 'bg-rose-500/10 text-rose-400 border-rose-500/30' };
      case 'MAINTENANCE_UPDATED':
        return { label: 'Bảo trì', style: 'bg-amber-500/10 text-amber-400 border-amber-500/30' };
      case 'STATUS_CHANGED':
        return { label: 'Đổi trạng thái', style: 'bg-purple-500/10 text-purple-400 border-purple-500/30' };
      default:
        return { label: actionType, style: 'bg-slate-500/10 text-slate-400 border-slate-500/30' };
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        {/* Welcome Header */}
        <div className="relative overflow-hidden bg-gradient-to-r from-sky-900/40 via-indigo-900/30 to-slate-800/80 border border-slate-700/70 rounded-2xl p-6 shadow-xl">
          <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-sky-500/10 border border-sky-500/30 text-sky-400 text-xs font-medium mb-3">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Bảng điều khiển Tổng quan (Phase 8 Real-Time Stats)</span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                Xin chào, {user?.full_name}!
              </h1>
              <p className="text-slate-300 text-sm mt-1">
                Xem thống kê tài sản, cấp phát, sự cố kỹ thuật và phân bổ phòng ban theo thời gian thực.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <span className={`px-3 py-1.5 rounded-xl border text-xs font-bold ${getRoleBadgeStyle(user?.role)}`}>
                <Shield className="w-3.5 h-3.5 inline mr-1" />
                {user?.role}
              </span>

              <button
                onClick={loadDashboard}
                disabled={loading}
                className="flex items-center space-x-2 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-semibold rounded-xl transition-all disabled:opacity-50"
                title="Tải lại dữ liệu"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-sky-400' : ''}`} />
                <span>Làm mới</span>
              </button>
            </div>
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-center justify-between gap-3 text-rose-300 text-sm">
            <div className="flex items-center space-x-3">
              <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              onClick={loadDashboard}
              className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold shrink-0 transition-colors"
            >
              Thử lại
            </button>
          </div>
        )}

        {/* Skeleton Loading State */}
        {loading && !data && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-28 bg-slate-800/60 border border-slate-700/50 rounded-2xl animate-pulse p-4 space-y-3">
                  <div className="h-4 bg-slate-700/50 rounded w-1/2"></div>
                  <div className="h-8 bg-slate-700/70 rounded w-3/4"></div>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="h-72 bg-slate-800/60 border border-slate-700/50 rounded-2xl animate-pulse p-6"></div>
              <div className="h-72 bg-slate-800/60 border border-slate-700/50 rounded-2xl animate-pulse p-6"></div>
            </div>
          </div>
        )}

        {/* Main Dashboard Metrics */}
        {data && (
          <div className="space-y-6">
            {/* 5 Key Metric Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              {/* Total Assets */}
              <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl p-5 shadow-lg relative overflow-hidden group hover:border-sky-500/50 transition-all">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Tổng Tài sản</span>
                  <div className="p-2.5 rounded-xl bg-sky-500/10 text-sky-400 border border-sky-500/20">
                    <Boxes className="w-5 h-5" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-extrabold text-white tracking-tight">{data.assets.total}</div>
                  <p className="text-xs text-slate-400 mt-1">Trong toàn hệ thống</p>
                </div>
              </div>

              {/* In Stock */}
              <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl p-5 shadow-lg relative overflow-hidden group hover:border-emerald-500/50 transition-all">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Đang có sẵn</span>
                  <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-extrabold text-emerald-400 tracking-tight">{data.assets.in_stock}</div>
                  <p className="text-xs text-slate-400 mt-1">
                    Sẵn sàng cấp phát ({data.assets.total > 0 ? Math.round((data.assets.in_stock / data.assets.total) * 100) : 0}%)
                  </p>
                </div>
              </div>

              {/* Assigned */}
              <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl p-5 shadow-lg relative overflow-hidden group hover:border-indigo-500/50 transition-all">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Đang cấp phát</span>
                  <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    <UserCheck className="w-5 h-5" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-extrabold text-indigo-400 tracking-tight">{data.assets.assigned}</div>
                  <p className="text-xs text-slate-400 mt-1">
                    Nhân viên đang sử dụng ({data.assets.total > 0 ? Math.round((data.assets.assigned / data.assets.total) * 100) : 0}%)
                  </p>
                </div>
              </div>

              {/* Maintenance / Damaged */}
              <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl p-5 shadow-lg relative overflow-hidden group hover:border-amber-500/50 transition-all">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Bảo trì / Hỏng</span>
                  <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    <Wrench className="w-5 h-5" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-extrabold text-amber-400 tracking-tight">
                    {data.assets.in_maintenance + data.assets.damaged}
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    {data.assets.in_maintenance} bảo trì, {data.assets.damaged} hỏng
                  </p>
                </div>
              </div>

              {/* Pending Incidents */}
              <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl p-5 shadow-lg relative overflow-hidden group hover:border-rose-500/50 transition-all">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Sự cố đang xử lý</span>
                  <div className="p-2.5 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
                    <AlertTriangle className="w-5 h-5" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-extrabold text-rose-400 tracking-tight">{data.incidents.pending}</div>
                  <p className="text-xs text-slate-400 mt-1">Tổng sự cố: {data.incidents.total}</p>
                </div>
              </div>
            </div>

            {/* 2-Column Section: Asset Status Distribution & Incident Status Breakdown */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Asset Status Distribution Card */}
              <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl p-6 shadow-lg space-y-5">
                <div className="flex items-center justify-between border-b border-slate-700/60 pb-3">
                  <div className="flex items-center space-x-2.5 text-sky-400 font-semibold text-base">
                    <TrendingUp className="w-5 h-5" />
                    <span>Phân bố Trạng thái Tài sản</span>
                  </div>
                  <Link
                    href="/assets"
                    className="text-xs text-sky-400 hover:text-sky-300 font-medium inline-flex items-center space-x-1"
                  >
                    <span>Quản lý</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>

                <div className="space-y-3">
                  {[
                    { key: 'IN_STOCK', label: 'Có sẵn (IN_STOCK)', count: data.assets.in_stock, color: 'bg-emerald-500', text: 'text-emerald-400' },
                    { key: 'ASSIGNED', label: 'Đang cấp phát (ASSIGNED)', count: data.assets.assigned, color: 'bg-sky-500', text: 'text-sky-400' },
                    { key: 'IN_MAINTENANCE', label: 'Đang bảo trì (IN_MAINTENANCE)', count: data.assets.in_maintenance, color: 'bg-amber-500', text: 'text-amber-400' },
                    { key: 'DAMAGED', label: 'Hư hỏng (DAMAGED)', count: data.assets.damaged, color: 'bg-rose-500', text: 'text-rose-400' },
                    { key: 'RETIRED', label: 'Đã thanh lý (RETIRED)', count: data.assets.retired, color: 'bg-slate-500', text: 'text-slate-400' },
                    { key: 'LOST', label: 'Thất lạc (LOST)', count: data.assets.lost, color: 'bg-purple-500', text: 'text-purple-400' },
                    { key: 'INACTIVE', label: 'Ngừng sử dụng (INACTIVE)', count: data.assets.inactive, color: 'bg-indigo-500', text: 'text-indigo-400' },
                  ].map((item) => {
                    const percentage = data.assets.total > 0 ? Math.round((item.count / data.assets.total) * 100) : 0;
                    return (
                      <div key={item.key} className="space-y-1">
                        <div className="flex justify-between text-xs font-medium">
                          <span className="text-slate-300">{item.label}</span>
                          <span className={item.text}>
                            {item.count} <span className="text-slate-400 font-normal">({percentage}%)</span>
                          </span>
                        </div>
                        <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${item.color} transition-all duration-500`}
                            style={{ width: `${percentage}%` }}
                          ></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Incident Breakdown Card */}
              <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl p-6 shadow-lg space-y-5">
                <div className="flex items-center justify-between border-b border-slate-700/60 pb-3">
                  <div className="flex items-center space-x-2.5 text-rose-400 font-semibold text-base">
                    <AlertTriangle className="w-5 h-5" />
                    <span>Thống kê Sự cố & Phiếu Bảo trì</span>
                  </div>
                  <Link
                    href="/incidents"
                    className="text-xs text-rose-400 hover:text-rose-300 font-medium inline-flex items-center space-x-1"
                  >
                    <span>Xem tất cả</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div className="p-3 bg-slate-900/60 border border-slate-700/50 rounded-xl space-y-1">
                    <span className="text-[11px] font-semibold uppercase text-rose-400">Mới tạo (OPEN)</span>
                    <div className="text-2xl font-bold text-white">{data.incidents.open}</div>
                  </div>
                  <div className="p-3 bg-slate-900/60 border border-slate-700/50 rounded-xl space-y-1">
                    <span className="text-[11px] font-semibold uppercase text-purple-400">Đang xem xét</span>
                    <div className="text-2xl font-bold text-white">{data.incidents.in_review}</div>
                  </div>
                  <div className="p-3 bg-slate-900/60 border border-slate-700/50 rounded-xl space-y-1">
                    <span className="text-[11px] font-semibold uppercase text-sky-400">Đang xử lý</span>
                    <div className="text-2xl font-bold text-white">{data.incidents.in_progress}</div>
                  </div>
                  <div className="p-3 bg-slate-900/60 border border-slate-700/50 rounded-xl space-y-1">
                    <span className="text-[11px] font-semibold uppercase text-amber-400">Chờ thông tin</span>
                    <div className="text-2xl font-bold text-white">{data.incidents.waiting_for_info}</div>
                  </div>
                  <div className="p-3 bg-slate-900/60 border border-slate-700/50 rounded-xl space-y-1">
                    <span className="text-[11px] font-semibold uppercase text-emerald-400">Đã giải quyết</span>
                    <div className="text-2xl font-bold text-white">{data.incidents.resolved}</div>
                  </div>
                  <div className="p-3 bg-slate-900/60 border border-slate-700/50 rounded-xl space-y-1">
                    <span className="text-[11px] font-semibold uppercase text-slate-400">Đóng / Hủy</span>
                    <div className="text-2xl font-bold text-white">
                      {data.incidents.closed + data.incidents.cancelled}
                    </div>
                  </div>
                </div>

                <div className="p-4 bg-slate-900/80 border border-slate-700/60 rounded-xl flex items-center justify-between text-xs">
                  <div className="text-slate-300">
                    <span className="font-semibold text-white">{data.assignments.active}</span> tài sản đang thuộc các lệnh cấp phát ACTIVE trong tổng số <span className="font-semibold text-white">{data.assignments.total}</span> lượt cấp phát.
                  </div>
                  <Link href="/assignments" className="text-sky-400 hover:text-sky-300 font-medium shrink-0 ml-2">
                    Lịch sử cấp phát &rarr;
                  </Link>
                </div>
              </div>
            </div>

            {/* Department Breakdown & Recent Activity */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Department Statistics Table (2 cols on lg) */}
              <div className="lg:col-span-2 bg-slate-800/80 border border-slate-700/70 rounded-2xl p-6 shadow-lg space-y-4">
                <div className="flex items-center justify-between border-b border-slate-700/60 pb-3">
                  <div className="flex items-center space-x-2.5 text-indigo-400 font-semibold text-base">
                    <Building2 className="w-5 h-5" />
                    <span>Thống kê Tài sản theo Phòng ban</span>
                  </div>
                  <span className="text-xs text-slate-400 font-medium">
                    {data.departments.length} phòng ban
                  </span>
                </div>

                {data.departments.length === 0 ? (
                  <p className="text-xs text-slate-400 text-center py-6">Chưa có thông tin phòng ban.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-slate-700/60 text-slate-400 uppercase font-semibold">
                          <th className="py-2.5 px-3">Phòng ban</th>
                          <th className="py-2.5 px-3 text-center">Tổng tài sản</th>
                          <th className="py-2.5 px-3 text-center">Đang cấp phát</th>
                          <th className="py-2.5 px-3 text-center">Có sẵn</th>
                          <th className="py-2.5 px-3 text-right">Tỷ lệ sử dụng</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-700/40 text-slate-200">
                        {data.departments.map((dept, index) => {
                          const rate = dept.total_assets > 0 ? Math.round((dept.assigned_assets / dept.total_assets) * 100) : 0;
                          return (
                            <tr key={dept.department_id || index} className="hover:bg-slate-700/20 transition-colors">
                              <td className="py-3 px-3">
                                <div className="font-semibold text-white">{dept.department_name}</div>
                                <div className="text-[11px] text-slate-400 font-mono">{dept.department_code}</div>
                              </td>
                              <td className="py-3 px-3 text-center font-bold text-white">{dept.total_assets}</td>
                              <td className="py-3 px-3 text-center text-sky-400 font-semibold">{dept.assigned_assets}</td>
                              <td className="py-3 px-3 text-center text-emerald-400 font-semibold">{dept.in_stock_assets}</td>
                              <td className="py-3 px-3 text-right">
                                <span className="inline-block font-semibold px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300">
                                  {rate}%
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Recent Activity Timeline (1 col on lg) */}
              <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl p-6 shadow-lg space-y-4">
                <div className="flex items-center justify-between border-b border-slate-700/60 pb-3">
                  <div className="flex items-center space-x-2.5 text-purple-400 font-semibold text-base">
                    <Activity className="w-5 h-5" />
                    <span>Hoạt động Gần đây</span>
                  </div>
                  <span className="text-xs text-slate-400 font-medium">Top 10</span>
                </div>

                {data.recent_activities.length === 0 ? (
                  <p className="text-xs text-slate-400 text-center py-6">Chưa có nhật ký hoạt động.</p>
                ) : (
                  <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
                    {data.recent_activities.map((act) => {
                      const badge = getActionTypeBadge(act.action_type);
                      return (
                        <div
                          key={act.id}
                          className="p-3 bg-slate-900/60 border border-slate-700/50 rounded-xl text-xs space-y-1.5"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${badge.style}`}>
                              {badge.label}
                            </span>
                            <span className="text-[11px] text-slate-400 flex items-center space-x-1">
                              <Clock className="w-3 h-3" />
                              <span>{new Date(act.created_at).toLocaleString('vi-VN')}</span>
                            </span>
                          </div>

                          <div className="font-semibold text-slate-200">
                            {act.asset_name} <span className="text-slate-400 font-mono text-[11px]">({act.asset_code})</span>
                          </div>

                          {act.details && <div className="text-slate-400 text-[11px] line-clamp-2">{act.details}</div>}

                          <div className="text-[11px] text-slate-400 text-right">
                            Thực hiện bởi: <span className="text-slate-300 font-medium">{act.performed_by_name}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
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
