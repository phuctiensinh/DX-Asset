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
  TrendingUp,
  Shield,
  Sparkles,
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
        return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'IT_ASSET_MANAGER':
        return 'bg-indigo-100 text-indigo-700 border-indigo-200';
      case 'MANAGER':
        return 'bg-emerald-100 text-emerald-700 border-emerald-200';
      case 'EMPLOYEE':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const getActionTypeBadge = (actionType: string) => {
    switch (actionType) {
      case 'CREATED':
        return { label: 'Tạo tài sản', style: 'bg-emerald-50 text-emerald-700 border-emerald-200' };
      case 'ASSIGNED':
        return { label: 'Cấp phát', style: 'bg-sky-50 text-sky-700 border-sky-200' };
      case 'RETURNED':
        return { label: 'Thu hồi', style: 'bg-indigo-50 text-indigo-700 border-indigo-200' };
      case 'INCIDENT_REPORTED':
        return { label: 'Báo sự cố', style: 'bg-rose-50 text-rose-700 border-rose-200' };
      case 'MAINTENANCE_UPDATED':
        return { label: 'Bảo trì', style: 'bg-amber-50 text-amber-800 border-amber-200' };
      case 'STATUS_CHANGED':
        return { label: 'Đổi trạng thái', style: 'bg-purple-50 text-purple-700 border-purple-200' };
      default:
        return { label: actionType, style: 'bg-slate-100 text-slate-700 border-slate-200' };
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        {/* Welcome Banner */}
        <div className="relative overflow-hidden bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm">
          <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-semibold mb-2">
                <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                <span>Bảng điều khiển Tổng quan DX-Asset Real-Time</span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                Xin chào, {user?.full_name}!
              </h1>
              <p className="text-slate-500 text-xs sm:text-sm mt-1">
                Theo dõi tình trạng thiết bị, phân bổ phòng ban, lịch sử bàn giao & báo hỏng theo thời gian thực.
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
                className="flex items-center space-x-2 px-3.5 py-2 bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700 text-xs font-semibold rounded-xl transition-all disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-indigo-600' : ''}`} />
                <span>Làm mới</span>
              </button>
            </div>
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-center justify-between gap-3 text-rose-800 text-xs font-medium shadow-sm">
            <div className="flex items-center space-x-3">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              onClick={loadDashboard}
              className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold shrink-0 transition-colors"
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
                <div key={i} className="h-28 bg-white border border-slate-200 rounded-2xl animate-pulse p-4 space-y-3 shadow-sm">
                  <div className="h-4 bg-slate-100 rounded w-1/2"></div>
                  <div className="h-8 bg-slate-200 rounded w-3/4"></div>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="h-72 bg-white border border-slate-200 rounded-2xl animate-pulse p-6 shadow-sm"></div>
              <div className="h-72 bg-white border border-slate-200 rounded-2xl animate-pulse p-6 shadow-sm"></div>
            </div>
          </div>
        )}

        {/* Main Dashboard Metrics */}
        {data && (
          <div className="space-y-6">
            {/* 5 Key Metric Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              {/* Total Assets */}
              <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm hover:shadow-md transition-all">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Tổng Tài sản</span>
                  <div className="p-2.5 rounded-xl bg-sky-50 text-sky-600 border border-sky-100">
                    <Boxes className="w-5 h-5" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-extrabold text-slate-900 tracking-tight">{data.assets.total}</div>
                  <p className="text-xs text-slate-500 mt-1">Toàn bộ danh mục</p>
                </div>
              </div>

              {/* In Stock */}
              <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm hover:shadow-md transition-all">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Đang có sẵn</span>
                  <div className="p-2.5 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-100">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-extrabold text-emerald-600 tracking-tight">{data.assets.in_stock}</div>
                  <p className="text-xs text-slate-500 mt-1">
                    Trong kho ({data.assets.total > 0 ? Math.round((data.assets.in_stock / data.assets.total) * 100) : 0}%)
                  </p>
                </div>
              </div>

              {/* Assigned */}
              <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm hover:shadow-md transition-all">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Đang cấp phát</span>
                  <div className="p-2.5 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
                    <UserCheck className="w-5 h-5" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-extrabold text-indigo-600 tracking-tight">{data.assets.assigned}</div>
                  <p className="text-xs text-slate-500 mt-1">
                    Nhân viên dùng ({data.assets.total > 0 ? Math.round((data.assets.assigned / data.assets.total) * 100) : 0}%)
                  </p>
                </div>
              </div>

              {/* Maintenance / Damaged */}
              <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm hover:shadow-md transition-all">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Bảo trì / Hỏng</span>
                  <div className="p-2.5 rounded-xl bg-amber-50 text-amber-700 border border-amber-100">
                    <Wrench className="w-5 h-5" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-extrabold text-amber-600 tracking-tight">
                    {data.assets.in_maintenance + data.assets.damaged}
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    {data.assets.in_maintenance} bảo trì, {data.assets.damaged} hỏng
                  </p>
                </div>
              </div>

              {/* Pending Incidents */}
              <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm hover:shadow-md transition-all">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Sự cố đang xử lý</span>
                  <div className="p-2.5 rounded-xl bg-rose-50 text-rose-600 border border-rose-100">
                    <AlertTriangle className="w-5 h-5" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-extrabold text-rose-600 tracking-tight">{data.incidents.pending}</div>
                  <p className="text-xs text-slate-500 mt-1">Tổng sự cố: {data.incidents.total}</p>
                </div>
              </div>
            </div>

            {/* 2-Column Section: Asset Status Distribution & Incident Status Breakdown */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Asset Status Distribution Card */}
              <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm space-y-5">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center space-x-2 text-indigo-600 font-bold text-base">
                    <TrendingUp className="w-5 h-5" />
                    <span>Phân bố Trạng thái Tài sản</span>
                  </div>
                  <Link
                    href="/assets"
                    className="text-xs text-indigo-600 hover:text-indigo-700 font-semibold inline-flex items-center space-x-1"
                  >
                    <span>Chi tiết</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>

                <div className="space-y-3.5">
                  {[
                    { key: 'IN_STOCK', label: 'Có sẵn (IN_STOCK)', count: data.assets.in_stock, color: 'bg-emerald-500', text: 'text-emerald-700' },
                    { key: 'ASSIGNED', label: 'Đang cấp phát (ASSIGNED)', count: data.assets.assigned, color: 'bg-sky-500', text: 'text-sky-700' },
                    { key: 'IN_MAINTENANCE', label: 'Đang bảo trì (IN_MAINTENANCE)', count: data.assets.in_maintenance, color: 'bg-amber-500', text: 'text-amber-800' },
                    { key: 'DAMAGED', label: 'Hư hỏng (DAMAGED)', count: data.assets.damaged, color: 'bg-rose-500', text: 'text-rose-700' },
                    { key: 'RETIRED', label: 'Đã thanh lý (RETIRED)', count: data.assets.retired, color: 'bg-slate-400', text: 'text-slate-700' },
                    { key: 'LOST', label: 'Thất lạc (LOST)', count: data.assets.lost, color: 'bg-purple-500', text: 'text-purple-700' },
                    { key: 'INACTIVE', label: 'Ngừng sử dụng (INACTIVE)', count: data.assets.inactive, color: 'bg-indigo-500', text: 'text-indigo-700' },
                  ].map((item) => {
                    const percentage = data.assets.total > 0 ? Math.round((item.count / data.assets.total) * 100) : 0;
                    return (
                      <div key={item.key} className="space-y-1">
                        <div className="flex justify-between text-xs font-semibold">
                          <span className="text-slate-700">{item.label}</span>
                          <span className={item.text}>
                            {item.count} <span className="text-slate-400 font-normal">({percentage}%)</span>
                          </span>
                        </div>
                        <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
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
              <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm space-y-5">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center space-x-2 text-rose-600 font-bold text-base">
                    <AlertTriangle className="w-5 h-5" />
                    <span>Thống kê Sự cố & Phiếu Bảo trì</span>
                  </div>
                  <Link
                    href="/incidents"
                    className="text-xs text-rose-600 hover:text-rose-700 font-semibold inline-flex items-center space-x-1"
                  >
                    <span>Xem tất cả</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div className="p-3 bg-rose-50/50 border border-rose-100 rounded-xl space-y-1">
                    <span className="text-[11px] font-bold uppercase text-rose-700">Mới tạo (OPEN)</span>
                    <div className="text-2xl font-extrabold text-slate-900">{data.incidents.open}</div>
                  </div>
                  <div className="p-3 bg-purple-50/50 border border-purple-100 rounded-xl space-y-1">
                    <span className="text-[11px] font-bold uppercase text-purple-700">Đang xem xét</span>
                    <div className="text-2xl font-extrabold text-slate-900">{data.incidents.in_review}</div>
                  </div>
                  <div className="p-3 bg-sky-50/50 border border-sky-100 rounded-xl space-y-1">
                    <span className="text-[11px] font-bold uppercase text-sky-700">Đang xử lý</span>
                    <div className="text-2xl font-extrabold text-slate-900">{data.incidents.in_progress}</div>
                  </div>
                  <div className="p-3 bg-amber-50/50 border border-amber-100 rounded-xl space-y-1">
                    <span className="text-[11px] font-bold uppercase text-amber-800">Chờ thông tin</span>
                    <div className="text-2xl font-extrabold text-slate-900">{data.incidents.waiting_for_info}</div>
                  </div>
                  <div className="p-3 bg-emerald-50/50 border border-emerald-100 rounded-xl space-y-1">
                    <span className="text-[11px] font-bold uppercase text-emerald-700">Đã giải quyết</span>
                    <div className="text-2xl font-extrabold text-slate-900">{data.incidents.resolved}</div>
                  </div>
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
                    <span className="text-[11px] font-bold uppercase text-slate-500">Đóng / Hủy</span>
                    <div className="text-2xl font-extrabold text-slate-900">
                      {data.incidents.closed + data.incidents.cancelled}
                    </div>
                  </div>
                </div>

                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between text-xs">
                  <div className="text-slate-600">
                    <span className="font-bold text-slate-900">{data.assignments.active}</span> tài sản đang thuộc các lệnh cấp phát ACTIVE trong tổng số <span className="font-bold text-slate-900">{data.assignments.total}</span> lượt cấp phát.
                  </div>
                  <Link href="/assignments" className="text-indigo-600 hover:text-indigo-700 font-semibold shrink-0 ml-2">
                    Lịch sử cấp phát &rarr;
                  </Link>
                </div>
              </div>
            </div>

            {/* Department Breakdown & Recent Activity */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Department Statistics Table (2 cols on lg) */}
              <div className="lg:col-span-2 bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center space-x-2 text-indigo-600 font-bold text-base">
                    <Building2 className="w-5 h-5" />
                    <span>Thống kê Tài sản theo Phòng ban</span>
                  </div>
                  <Link href="/departments" className="text-xs text-indigo-600 hover:text-indigo-700 font-semibold">
                    Xem danh mục ({data.departments.length} phòng ban)
                  </Link>
                </div>

                {data.departments.length === 0 ? (
                  <p className="text-xs text-slate-400 text-center py-6">Chưa có thông tin phòng ban.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-slate-200 text-slate-500 uppercase font-bold">
                          <th className="py-2.5 px-3">Phòng ban</th>
                          <th className="py-2.5 px-3 text-center">Tổng tài sản</th>
                          <th className="py-2.5 px-3 text-center">Đang cấp phát</th>
                          <th className="py-2.5 px-3 text-center">Có sẵn</th>
                          <th className="py-2.5 px-3 text-right">Tỷ lệ sử dụng</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 text-slate-700">
                        {data.departments.map((dept, index) => {
                          const rate = dept.total_assets > 0 ? Math.round((dept.assigned_assets / dept.total_assets) * 100) : 0;
                          return (
                            <tr key={`dept-${dept.department_id ?? 'null'}-${index}`} className="hover:bg-slate-50 transition-colors">
                              <td className="py-3 px-3">
                                <div className="font-bold text-slate-900">{dept.department_name}</div>
                                <div className="text-[11px] text-slate-400 font-mono">{dept.department_code}</div>
                              </td>
                              <td className="py-3 px-3 text-center font-extrabold text-slate-900">{dept.total_assets}</td>
                              <td className="py-3 px-3 text-center text-indigo-600 font-bold">{dept.assigned_assets}</td>
                              <td className="py-3 px-3 text-center text-emerald-600 font-bold">{dept.in_stock_assets}</td>
                              <td className="py-3 px-3 text-right">
                                <span className="inline-block font-bold px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-700">
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
              <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center space-x-2 text-purple-600 font-bold text-base">
                    <Activity className="w-5 h-5" />
                    <span>Hoạt động Gần đây</span>
                  </div>
                  <span className="text-xs text-slate-400 font-medium">Top 10 Nhật ký</span>
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
                          className="p-3 bg-slate-50 border border-slate-200/80 rounded-xl text-xs space-y-1.5"
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

                          <div className="font-bold text-slate-900">
                            {act.asset_name} <span className="text-slate-400 font-mono text-[11px]">({act.asset_code})</span>
                          </div>

                          {act.details && <div className="text-slate-600 text-[11px] line-clamp-2">{act.details}</div>}

                          <div className="text-[11px] text-slate-400 text-right">
                            Thực hiện: <span className="text-slate-700 font-medium">{act.performed_by_name}</span>
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

