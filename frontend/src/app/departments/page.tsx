'use client';

import React, { useEffect, useState } from 'react';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { Navbar } from '@/components/Navbar';
import { fetchApi } from '@/lib/api';
import {
  Building2,
  Users,
  Boxes,
  Search,
  Plus,
  RefreshCw,
  AlertCircle,
  Eye,
  CheckCircle2,
  X,
  Layers,
  Sparkles,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';

interface Department {
  id: number;
  code: string;
  name: string;
  description?: string | null;
  created_at?: string;
  total_users?: number;
  total_assets?: number;
}

interface DashboardSummaryResponse {
  departments: {
    department_id: number | null;
    department_code: string;
    department_name: string;
    total_assets: number;
    assigned_assets: number;
    in_stock_assets: number;
  }[];
}

export default function DepartmentsPage() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [deptStats, setDeptStats] = useState<Record<string, { total: number; assigned: number; in_stock: number }>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  // Modals
  const [selectedDept, setSelectedDept] = useState<Department | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newCode, setNewCode] = useState('');
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [deptList, dashData] = await Promise.all([
        fetchApi<Department[]>('/departments'),
        fetchApi<DashboardSummaryResponse>('/dashboard/summary').catch(() => null),
      ]);

      setDepartments(deptList || []);

      if (dashData?.departments) {
        const statsMap: Record<string, { total: number; assigned: number; in_stock: number }> = {};
        dashData.departments.forEach((d) => {
          if (d.department_code) {
            statsMap[d.department_code] = {
              total: d.total_assets,
              assigned: d.assigned_assets,
              in_stock: d.in_stock_assets,
            };
          }
        });
        setDeptStats(statsMap);
      }
    } catch (err: any) {
      setError(err?.message || 'Không thể tải danh sách phòng ban.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredDepts = departments.filter(
    (d) =>
      d.name.toLowerCase().includes(search.toLowerCase()) ||
      d.code.toLowerCase().includes(search.toLowerCase()) ||
      (d.description && d.description.toLowerCase().includes(search.toLowerCase()))
  );

  const totalAssetsCount = Object.values(deptStats).reduce((acc, curr) => acc + curr.total, 0);

  const handleCreateDepartment = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCode.trim() || !newName.trim()) return;

    setFormSubmitting(true);
    setFeedback(null);

    // Simulate adding locally (or API post if backend supports)
    setTimeout(() => {
      const created: Department = {
        id: Date.now(),
        code: newCode.trim().toUpperCase(),
        name: newName.trim(),
        description: newDesc.trim() || 'Phòng ban mới tạo',
        created_at: new Date().toISOString(),
      };

      setDepartments((prev) => [created, ...prev]);
      setShowCreateModal(false);
      setNewCode('');
      setNewName('');
      setNewDesc('');
      setFormSubmitting(false);
      setFeedback({
        type: 'success',
        message: `Đã thêm phòng ban "${created.name}" thành công!`,
      });
      setTimeout(() => setFeedback(null), 4000);
    }, 400);
  };

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
        <Navbar />

        <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
          {/* Header Banner */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shadow-sm">
                <Building2 className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
                    Danh mục Phòng ban Doanh nghiệp
                  </h1>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-100">
                    DX-OS Human Space
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Quản lý cơ cấu phòng ban, sơ đồ phân bổ tài sản và nhân sự phụ trách toàn công ty.
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={loadData}
                disabled={loading}
                className="inline-flex items-center space-x-2 px-3.5 py-2 bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700 text-xs font-semibold rounded-xl transition-all disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-indigo-600' : ''}`} />
                <span>Làm mới</span>
              </button>

              <button
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center space-x-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-md shadow-indigo-500/20 transition-all"
              >
                <Plus className="w-4 h-4" />
                <span>Thêm phòng ban</span>
              </button>
            </div>
          </div>

          {/* Feedback Message */}
          {feedback && (
            <div
              className={`p-4 rounded-xl border text-xs font-medium flex items-center space-x-3 shadow-sm ${
                feedback.type === 'success'
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                  : 'bg-rose-50 border-rose-200 text-rose-800'
              }`}
            >
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <div className="flex-1">{feedback.message}</div>
              <button onClick={() => setFeedback(null)} className="text-slate-400 hover:text-slate-600">
                ✕
              </button>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center space-x-3 shadow-sm">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Key Metrics Overview */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm flex items-center justify-between">
              <div>
                <div className="text-xs font-medium text-slate-500">Tổng số phòng ban</div>
                <div className="text-2xl font-extrabold text-slate-900 mt-1">{departments.length}</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Đã đăng ký hệ thống</div>
              </div>
              <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
                <Building2 className="w-5 h-5" />
              </div>
            </div>

            <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm flex items-center justify-between">
              <div>
                <div className="text-xs font-medium text-slate-500">Tài sản đang sử dụng</div>
                <div className="text-2xl font-extrabold text-indigo-600 mt-1">{totalAssetsCount}</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Phân bổ tại phòng ban</div>
              </div>
              <div className="w-10 h-10 rounded-xl bg-sky-50 border border-sky-100 flex items-center justify-center text-sky-600">
                <Boxes className="w-5 h-5" />
              </div>
            </div>

            <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm flex items-center justify-between">
              <div>
                <div className="text-xs font-medium text-slate-500">Quy chuẩn quản lý</div>
                <div className="text-2xl font-extrabold text-emerald-600 mt-1">100%</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Định danh mã Code chuẩn</div>
              </div>
              <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600">
                <ShieldCheck className="w-5 h-5" />
              </div>
            </div>
          </div>

          {/* Search & Filter Bar */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="relative w-full sm:w-96">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Tìm mã phòng ban, tên phòng ban..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:bg-white transition-all"
              />
            </div>
            <div className="text-xs text-slate-500 font-medium">
              Hiển thị <span className="font-bold text-slate-900">{filteredDepts.length}</span> phòng ban
            </div>
          </div>

          {/* Department Cards Grid */}
          {loading ? (
            <div className="bg-white border border-slate-200/90 rounded-2xl p-12 text-center text-slate-500 text-xs flex flex-col items-center justify-center space-y-3 shadow-sm">
              <RefreshCw className="w-8 h-8 animate-spin text-indigo-600" />
              <p>Đang tải danh sách phòng ban...</p>
            </div>
          ) : filteredDepts.length === 0 ? (
            <div className="bg-white border border-slate-200/90 rounded-2xl p-12 text-center text-slate-500 text-xs shadow-sm">
              Không tìm thấy phòng ban phù hợp.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {filteredDepts.map((dept) => {
                const stat = deptStats[dept.code] || { total: 0, assigned: 0, in_stock: 0 };
                return (
                  <div
                    key={dept.id}
                    className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm hover:shadow-md hover:border-indigo-200 transition-all flex flex-col justify-between group"
                  >
                    <div className="space-y-3">
                      <div className="flex items-start justify-between">
                        <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 font-extrabold text-sm group-hover:scale-105 transition-transform">
                          {dept.code.substring(0, 3)}
                        </div>
                        <span className="px-2.5 py-1 rounded-full text-[11px] font-bold font-mono bg-slate-100 text-slate-700 border border-slate-200">
                          {dept.code}
                        </span>
                      </div>

                      <div>
                        <h3 className="font-extrabold text-slate-900 text-base group-hover:text-indigo-600 transition-colors">
                          {dept.name}
                        </h3>
                        <p className="text-xs text-slate-500 mt-1 line-clamp-2">
                          {dept.description || 'Chưa cập nhật mô tả chức năng phòng ban.'}
                        </p>
                      </div>
                    </div>

                    <div className="mt-5 pt-4 border-t border-slate-100 space-y-3">
                      <div className="grid grid-cols-3 gap-2 text-center text-xs">
                        <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                          <div className="text-[10px] text-slate-400 font-medium">Tổng TS</div>
                          <div className="font-bold text-slate-900 text-sm mt-0.5">{stat.total}</div>
                        </div>
                        <div className="p-2 rounded-xl bg-indigo-50/60 border border-indigo-100">
                          <div className="text-[10px] text-indigo-600 font-medium">Cấp phát</div>
                          <div className="font-bold text-indigo-700 text-sm mt-0.5">{stat.assigned}</div>
                        </div>
                        <div className="p-2 rounded-xl bg-emerald-50/60 border border-emerald-100">
                          <div className="text-[10px] text-emerald-600 font-medium">Sẵn có</div>
                          <div className="font-bold text-emerald-700 text-sm mt-0.5">{stat.in_stock}</div>
                        </div>
                      </div>

                      <button
                        onClick={() => {
                          setSelectedDept(dept);
                          setShowDetailModal(true);
                        }}
                        className="w-full py-2 bg-slate-50 hover:bg-indigo-50 border border-slate-200 hover:border-indigo-200 text-slate-700 hover:text-indigo-700 text-xs font-semibold rounded-xl transition-all flex items-center justify-center space-x-1.5"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Xem chi tiết hồ sơ</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </main>

        {/* CREATE DEPARTMENT MODAL */}
        {showCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
            <div className="w-full max-w-md bg-white border border-slate-200 rounded-2xl shadow-xl p-6 text-slate-900">
              <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                <div className="flex items-center space-x-2 font-bold text-slate-900 text-base">
                  <Building2 className="w-5 h-5 text-indigo-600" />
                  <span>Thêm Phòng Ban Mới</span>
                </div>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="text-slate-400 hover:text-slate-600 text-sm"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleCreateDepartment} className="space-y-4 mt-4 text-xs">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Mã Phòng Ban (Code) <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="VD: IT, HR, FIN, MKT"
                    value={newCode}
                    onChange={(e) => setNewCode(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-xs text-slate-900 focus:outline-none focus:border-indigo-500 uppercase font-mono"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Tên Phòng Ban <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="VD: Phòng Công nghệ Thông tin"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-xs text-slate-900 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Mô tả chức năng</label>
                  <textarea
                    rows={3}
                    placeholder="Nhập mô tả nhiệm vụ hoặc vị trí phòng ban..."
                    value={newDesc}
                    onChange={(e) => setNewDesc(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-xs text-slate-900 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl"
                  >
                    Hủy bỏ
                  </button>
                  <button
                    type="submit"
                    disabled={formSubmitting}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl shadow-md shadow-indigo-500/20 disabled:opacity-50"
                  >
                    {formSubmitting ? 'Đang tạo...' : 'Tạo mới'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* DETAIL MODAL */}
        {showDetailModal && selectedDept && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
            <div className="w-full max-w-lg bg-white border border-slate-200 rounded-2xl shadow-xl p-6 text-slate-900 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 font-bold">
                    <Building2 className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-extrabold text-lg text-slate-900">{selectedDept.name}</h3>
                    <span className="text-xs font-mono font-bold text-indigo-600">{selectedDept.code}</span>
                  </div>
                </div>
                <button
                  onClick={() => setShowDetailModal(false)}
                  className="text-slate-400 hover:text-slate-600 text-sm"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-3 text-xs">
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 space-y-1">
                  <div className="font-semibold text-slate-700">Mô tả chi tiết:</div>
                  <p className="text-slate-600">
                    {selectedDept.description || 'Chưa cập nhật chi tiết nhiệm vụ.'}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-indigo-50/50 rounded-xl border border-indigo-100">
                    <div className="text-indigo-600 font-medium">Tài sản bàn giao</div>
                    <div className="text-xl font-bold text-indigo-800 mt-1">
                      {deptStats[selectedDept.code]?.assigned || 0} thiết bị
                    </div>
                  </div>
                  <div className="p-3 bg-emerald-50/50 rounded-xl border border-emerald-100">
                    <div className="text-emerald-600 font-medium">Tài sản kho sẵn có</div>
                    <div className="text-xl font-bold text-emerald-800 mt-1">
                      {deptStats[selectedDept.code]?.in_stock || 0} thiết bị
                    </div>
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex justify-end">
                <button
                  onClick={() => setShowDetailModal(false)}
                  className="px-4 py-2 bg-indigo-600 text-white font-semibold rounded-xl text-xs"
                >
                  Đóng
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
