'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/lib/auth-context';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { Navbar } from '@/components/Navbar';
import { fetchApi } from '@/lib/api';
import {
  UserCheck,
  Plus,
  Search,
  Filter,
  RefreshCw,
  X,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Building2,
  User as UserIcon,
  Calendar,
  FileText,
  ArrowRightLeft,
  Undo2,
  Clock,
  Boxes,
} from 'lucide-react';

interface AssetSummary {
  id: number;
  asset_code: string;
  name: string;
  category: string;
  status: string;
}

interface UserSummary {
  id: number;
  email: string;
  full_name: string;
  role: string;
  department_id?: number | null;
}

interface DepartmentSummary {
  id: number;
  code: string;
  name: string;
}

interface Assignment {
  id: number;
  asset_id: number;
  assigned_to_user_id: number;
  assigned_by_user_id: number;
  assigned_date: string;
  return_date?: string | null;
  status: 'ACTIVE' | 'RETURNED';
  notes?: string | null;
  created_at: string;
  asset?: AssetSummary | null;
  assigned_to_user?: UserSummary | null;
  assigned_by_user?: UserSummary | null;
}

interface AssignmentListResponse {
  items: Assignment[];
  total: number;
  skip: number;
  limit: number;
}

interface AssetListResponse {
  items: AssetSummary[];
  total: number;
}

function AssignmentsContent() {
  const { user } = useAuth();
  const canManage = user?.role === 'ADMIN' || user?.role === 'IT_ASSET_MANAGER';

  // State
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [skip, setSkip] = useState<number>(0);
  const limit = 10;
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  // Dropdown reference data for modals
  const [availableAssets, setAvailableAssets] = useState<AssetSummary[]>([]);
  const [usersList, setUsersList] = useState<UserSummary[]>([]);
  const [departmentsList, setDepartmentsList] = useState<DepartmentSummary[]>([]);

  // Modals
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [showReturnModal, setShowReturnModal] = useState<boolean>(false);
  const [showTransferModal, setShowTransferModal] = useState<boolean>(false);
  const [selectedAssignment, setSelectedAssignment] = useState<Assignment | null>(null);

  // Form states
  const [createFormData, setCreateFormData] = useState({
    asset_id: '',
    user_id: '',
    department_id: '',
    assigned_date: new Date().toISOString().split('T')[0],
    notes: '',
  });

  const [returnNotes, setReturnNotes] = useState<string>('');

  const [transferFormData, setTransferFormData] = useState({
    target_user_id: '',
    department_id: '',
    notes: '',
  });

  const [formSubmitting, setFormSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loadAssignments = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append('skip', skip.toString());
      params.append('limit', limit.toString());

      if (search.trim()) params.append('search', search.trim());
      if (statusFilter) params.append('status', statusFilter);

      const data = await fetchApi<AssignmentListResponse>(`/assignments?${params.toString()}`);
      setAssignments(data.items);
      setTotal(data.total);
    } catch (err: any) {
      setError(err?.message || 'Không thể tải danh sách cấp phát tài sản');
    } finally {
      setIsLoading(false);
    }
  }, [skip, search, statusFilter]);

  useEffect(() => {
    loadAssignments();
  }, [loadAssignments]);

  // Load dropdown data when modal opens
  const loadReferenceData = async () => {
    try {
      const [assetsData, usersData, deptsData] = await Promise.all([
        fetchApi<AssetListResponse>('/assets?status=IN_STOCK&limit=100'),
        fetchApi<UserSummary[]>('/users'),
        fetchApi<DepartmentSummary[]>('/departments'),
      ]);
      setAvailableAssets(assetsData.items || []);
      setUsersList(usersData || []);
      setDepartmentsList(deptsData || []);
    } catch (err: any) {
      console.error('Lỗi khi tải dữ liệu bổ trợ:', err);
    }
  };

  const openCreateModal = () => {
    loadReferenceData();
    setCreateFormData({
      asset_id: '',
      user_id: '',
      department_id: '',
      assigned_date: new Date().toISOString().split('T')[0],
      notes: '',
    });
    setFormError(null);
    setShowCreateModal(true);
  };

  const openReturnModal = (asm: Assignment) => {
    setSelectedAssignment(asm);
    setReturnNotes('');
    setFormError(null);
    setShowReturnModal(true);
  };

  const openTransferModal = (asm: Assignment) => {
    loadReferenceData();
    setSelectedAssignment(asm);
    setTransferFormData({
      target_user_id: '',
      department_id: '',
      notes: '',
    });
    setFormError(null);
    setShowTransferModal(true);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!createFormData.asset_id) {
      setFormError('Vui lòng chọn tài sản cần cấp phát.');
      return;
    }
    if (!createFormData.user_id) {
      setFormError('Vui lòng chọn nhân viên tiếp nhận.');
      return;
    }

    setFormSubmitting(true);
    try {
      await fetchApi<Assignment>('/assignments', {
        method: 'POST',
        body: JSON.stringify({
          asset_id: parseInt(createFormData.asset_id),
          user_id: parseInt(createFormData.user_id),
          department_id: createFormData.department_id ? parseInt(createFormData.department_id) : undefined,
          assigned_date: createFormData.assigned_date ? new Date(createFormData.assigned_date).toISOString() : undefined,
          notes: createFormData.notes.trim() || undefined,
        }),
      });

      setShowCreateModal(false);
      setSuccessMsg('Cấp phát tài sản thành công!');
      setTimeout(() => setSuccessMsg(null), 4000);
      loadAssignments();
    } catch (err: any) {
      setFormError(err?.message || 'Không thể thực hiện cấp phát tài sản');
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleReturnSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAssignment) return;
    setFormError(null);

    setFormSubmitting(true);
    try {
      await fetchApi<Assignment>(`/assignments/${selectedAssignment.id}/return`, {
        method: 'PATCH',
        body: JSON.stringify({
          notes: returnNotes.trim() || undefined,
        }),
      });

      setShowReturnModal(false);
      setSuccessMsg(`Đã thu hồi tài sản thành công khỏi ${selectedAssignment.assigned_to_user?.full_name || 'nhân viên'}.`);
      setTimeout(() => setSuccessMsg(null), 4000);
      loadAssignments();
    } catch (err: any) {
      setFormError(err?.message || 'Không thể thu hồi tài sản');
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleTransferSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAssignment) return;
    setFormError(null);

    if (!transferFormData.target_user_id) {
      setFormError('Vui lòng chọn nhân viên nhận chuyển giao.');
      return;
    }

    setFormSubmitting(true);
    try {
      await fetchApi<Assignment>(`/assignments/${selectedAssignment.id}/transfer`, {
        method: 'PATCH',
        body: JSON.stringify({
          target_user_id: parseInt(transferFormData.target_user_id),
          department_id: transferFormData.department_id ? parseInt(transferFormData.department_id) : undefined,
          notes: transferFormData.notes.trim() || undefined,
        }),
      });

      setShowTransferModal(false);
      setSuccessMsg('Chuyển giao tài sản thành công!');
      setTimeout(() => setSuccessMsg(null), 4000);
      loadAssignments();
    } catch (err: any) {
      setFormError(err?.message || 'Không thể chuyển giao tài sản');
    } finally {
      setFormSubmitting(false);
    }
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return '—';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('vi-VN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-800/80 border border-slate-700/70 rounded-2xl p-6 shadow-xl">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <UserCheck className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">
                Lịch sử Cấp phát & Thu hồi Tài sản
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Quản lý quá trình bàn giao, luân chuyển thiết bị doanh nghiệp. Tổng số lượt: <span className="font-semibold text-indigo-400">{total}</span>
              </p>
            </div>
          </div>

          {canManage && (
            <button
              onClick={openCreateModal}
              className="flex items-center justify-center space-x-2 px-4 py-2.5 bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-400 hover:to-indigo-500 text-white font-semibold text-xs rounded-xl shadow-lg shadow-indigo-500/20 transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>+ Cấp phát tài sản</span>
            </button>
          )}
        </div>

        {/* Global Notifications */}
        {successMsg && (
          <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm flex items-center space-x-2 animate-fadeIn">
            <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {error && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Search & Filter Toolbar */}
        <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl p-4 sm:p-5 shadow-lg space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
            {/* Search Input */}
            <div className="sm:col-span-8 relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Search className="w-4 h-4" />
              </div>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Tìm mã tài sản, tên thiết bị, tên nhân viên..."
                className="w-full pl-10 pr-4 py-2.5 bg-slate-900/80 border border-slate-700 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/20 rounded-xl text-xs text-slate-100 placeholder-slate-500 outline-none"
              />
            </div>

            {/* Status Filter */}
            <div className="sm:col-span-4">
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setSkip(0);
                }}
                className="w-full py-2.5 px-3 bg-slate-900/80 border border-slate-700 focus:border-indigo-500 rounded-xl text-xs text-slate-200 outline-none"
              >
                <option value="">Tất cả Trạng thái Cấp phát</option>
                <option value="ACTIVE">Đang hoạt động (ACTIVE)</option>
                <option value="RETURNED">Đã thu hồi (RETURNED)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Table / List Area */}
        <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl shadow-xl overflow-hidden">
          {isLoading ? (
            <div className="p-12 flex flex-col items-center justify-center space-y-3">
              <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
              <span className="text-xs text-slate-400">Đang tải lịch sử cấp phát tài sản...</span>
            </div>
          ) : assignments.length === 0 ? (
            <div className="p-12 text-center space-y-3">
              <UserCheck className="w-12 h-12 text-slate-600 mx-auto" />
              <div className="text-base font-semibold text-slate-300">Không tìm thấy bản ghi cấp phát</div>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Chưa có tài sản nào được cấp phát hoặc không tìm thấy dữ liệu khớp với bộ lọc.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900/80 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-700/80">
                  <tr>
                    <th className="py-3.5 px-4">Tài Sản</th>
                    <th className="py-3.5 px-4">Người Tiếp Nhận</th>
                    <th className="py-3.5 px-4">Ngày Cấp</th>
                    <th className="py-3.5 px-4">Ngày Thu Hồi</th>
                    <th className="py-3.5 px-4">Trạng Thái</th>
                    <th className="py-3.5 px-4">Người Thực Hiện</th>
                    <th className="py-3.5 px-4">Ghi Chú</th>
                    {canManage && <th className="py-3.5 px-4 text-right">Thao Tác</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/60">
                  {assignments.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-700/40 transition-colors">
                      <td className="py-3.5 px-4 font-medium text-white">
                        <div className="font-mono text-indigo-400 font-bold">
                          {item.asset?.asset_code || `TS #${item.asset_id}`}
                        </div>
                        <div className="text-slate-200">{item.asset?.name}</div>
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-slate-100 flex items-center space-x-1.5">
                          <UserIcon className="w-3.5 h-3.5 text-indigo-400" />
                          <span>{item.assigned_to_user?.full_name || `User #${item.assigned_to_user_id}`}</span>
                        </div>
                        <div className="text-[11px] text-slate-400">{item.assigned_to_user?.email}</div>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-300">
                        {formatDate(item.assigned_date)}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-300">
                        {item.status === 'ACTIVE' ? (
                          <span className="text-sky-400 font-sans italic text-[11px]">Đang sử dụng</span>
                        ) : (
                          formatDate(item.return_date)
                        )}
                      </td>
                      <td className="py-3.5 px-4">
                        {item.status === 'ACTIVE' ? (
                          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/30">
                            Đang hoạt động (ACTIVE)
                          </span>
                        ) : (
                          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/30">
                            Đã thu hồi (RETURNED)
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-slate-400">
                        {item.assigned_by_user?.full_name || 'Hệ thống'}
                      </td>
                      <td className="py-3.5 px-4 text-slate-300 max-w-xs truncate" title={item.notes || ''}>
                        {item.notes || '—'}
                      </td>
                      {canManage && (
                        <td className="py-3.5 px-4 text-right">
                          {item.status === 'ACTIVE' ? (
                            <div className="flex items-center justify-end space-x-2">
                              <button
                                onClick={() => openTransferModal(item)}
                                className="px-2.5 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 transition-colors text-[11px] font-semibold flex items-center space-x-1"
                                title="Chuyển sang nhân viên khác"
                              >
                                <ArrowRightLeft className="w-3.5 h-3.5" />
                                <span className="hidden lg:inline">Chuyển giao</span>
                              </button>
                              <button
                                onClick={() => openReturnModal(item)}
                                className="px-2.5 py-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 transition-colors text-[11px] font-semibold flex items-center space-x-1"
                                title="Thu hồi tài sản về kho"
                              >
                                <Undo2 className="w-3.5 h-3.5" />
                                <span>Thu hồi</span>
                              </button>
                            </div>
                          ) : (
                            <span className="text-slate-600 text-[11px] italic">Hoàn tất</span>
                          )}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Controls */}
          {total > limit && (
            <div className="px-4 py-3.5 bg-slate-900/60 border-t border-slate-700/60 flex items-center justify-between text-xs text-slate-400">
              <div>
                Hiển thị <span className="font-semibold text-white">{skip + 1}</span> -{' '}
                <span className="font-semibold text-white">
                  {Math.min(skip + limit, total)}
                </span>{' '}
                trên tổng số <span className="font-semibold text-white">{total}</span> bản ghi
              </div>
              <div className="flex items-center space-x-2">
                <button
                  disabled={skip === 0}
                  onClick={() => setSkip(Math.max(0, skip - limit))}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-700 text-slate-200"
                >
                  Trang trước
                </button>
                <button
                  disabled={skip + limit >= total}
                  onClick={() => setSkip(skip + limit)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-700 text-slate-200"
                >
                  Trang sau
                </button>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* CREATE ASSIGNMENT MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
          <div className="w-full max-w-lg bg-slate-800 border border-slate-700 rounded-2xl shadow-2xl p-6 text-slate-100 my-8">
            <div className="flex items-center justify-between pb-4 border-b border-slate-700">
              <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                <UserCheck className="w-5 h-5 text-indigo-400" />
                <span>Cấp phát tài sản cho nhân viên</span>
              </h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="mt-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="space-y-4 mt-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-300 mb-1">
                  Chọn tài sản trong kho (IN_STOCK) <span className="text-red-400">*</span>
                </label>
                <select
                  required
                  value={createFormData.asset_id}
                  onChange={(e) => setCreateFormData({ ...createFormData, asset_id: e.target.value })}
                  className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-indigo-500 outline-none text-white font-mono"
                >
                  <option value="">-- Chọn tài sản cần cấp --</option>
                  {availableAssets.map((asset) => (
                    <option key={asset.id} value={asset.id}>
                      [{asset.asset_code}] {asset.name} ({asset.category})
                    </option>
                  ))}
                </select>
                {availableAssets.length === 0 && (
                  <p className="text-[11px] text-amber-400 mt-1">
                    Hiện không có tài sản nào đang ở trạng thái 'Trong kho' (IN_STOCK).
                  </p>
                )}
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">
                  Nhân viên tiếp nhận <span className="text-red-400">*</span>
                </label>
                <select
                  required
                  value={createFormData.user_id}
                  onChange={(e) => setCreateFormData({ ...createFormData, user_id: e.target.value })}
                  className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-indigo-500 outline-none text-white"
                >
                  <option value="">-- Chọn nhân viên --</option>
                  {usersList.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.full_name} ({u.email}) - {u.role}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">Phòng ban sử dụng (Tùy chọn)</label>
                <select
                  value={createFormData.department_id}
                  onChange={(e) => setCreateFormData({ ...createFormData, department_id: e.target.value })}
                  className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-indigo-500 outline-none text-white"
                >
                  <option value="">-- Giữ nguyên theo nhân viên / Không đổi --</option>
                  {departmentsList.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">Ngày bàn giao</label>
                <input
                  type="date"
                  value={createFormData.assigned_date}
                  onChange={(e) => setCreateFormData({ ...createFormData, assigned_date: e.target.value })}
                  className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-indigo-500 outline-none text-white"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">Ghi chú bàn giao</label>
                <textarea
                  rows={2}
                  value={createFormData.notes}
                  onChange={(e) => setCreateFormData({ ...createFormData, notes: e.target.value })}
                  placeholder="Lý do cấp phát, phụ kiện đi kèm..."
                  className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-indigo-500 outline-none text-white"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-700">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2.5 rounded-xl bg-slate-700 hover:bg-slate-600 text-slate-200 font-semibold"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting || availableAssets.length === 0}
                  className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-indigo-500 hover:bg-indigo-400 text-white font-semibold shadow-lg shadow-indigo-500/20 disabled:opacity-60"
                >
                  {formSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Đang xử lý...</span>
                    </>
                  ) : (
                    <span>Xác nhận Cấp phát</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* RETURN MODAL */}
      {showReturnModal && selectedAssignment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
          <div className="w-full max-w-md bg-slate-800 border border-slate-700 rounded-2xl shadow-2xl p-6 text-slate-100">
            <div className="flex items-center justify-between pb-3 border-b border-slate-700">
              <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                <Undo2 className="w-5 h-5 text-red-400" />
                <span>Xác nhận Thu hồi Tài sản</span>
              </h3>
              <button
                onClick={() => setShowReturnModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="mt-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleReturnSubmit} className="space-y-4 mt-4 text-xs">
              <div className="p-3 bg-slate-900/60 border border-slate-700/60 rounded-xl space-y-1">
                <div>
                  Tài sản:{' '}
                  <span className="font-bold text-indigo-400 font-mono">
                    {selectedAssignment.asset?.asset_code}
                  </span>{' '}
                  - {selectedAssignment.asset?.name}
                </div>
                <div>
                  Người đang giữ:{' '}
                  <span className="font-semibold text-white">
                    {selectedAssignment.assigned_to_user?.full_name}
                  </span>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">Ghi chú / Lý do thu hồi</label>
                <textarea
                  rows={3}
                  value={returnNotes}
                  onChange={(e) => setReturnNotes(e.target.value)}
                  placeholder="VD: Hết hạn sử dụng, trả máy chuyển công tác..."
                  className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-red-500 outline-none text-white"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-700">
                <button
                  type="button"
                  onClick={() => setShowReturnModal(false)}
                  className="px-4 py-2.5 rounded-xl bg-slate-700 hover:bg-slate-600 text-slate-200 font-semibold"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-red-500 hover:bg-red-400 text-white font-semibold shadow-lg shadow-red-500/20 disabled:opacity-60"
                >
                  {formSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Đang thu hồi...</span>
                    </>
                  ) : (
                    <span>Thu hồi về Kho</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* TRANSFER MODAL */}
      {showTransferModal && selectedAssignment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
          <div className="w-full max-w-md bg-slate-800 border border-slate-700 rounded-2xl shadow-2xl p-6 text-slate-100">
            <div className="flex items-center justify-between pb-3 border-b border-slate-700">
              <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                <ArrowRightLeft className="w-5 h-5 text-amber-400" />
                <span>Chuyển giao Tài sản</span>
              </h3>
              <button
                onClick={() => setShowTransferModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="mt-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleTransferSubmit} className="space-y-4 mt-4 text-xs">
              <div className="p-3 bg-slate-900/60 border border-slate-700/60 rounded-xl space-y-1">
                <div>
                  Tài sản:{' '}
                  <span className="font-bold text-indigo-400 font-mono">
                    {selectedAssignment.asset?.asset_code}
                  </span>
                </div>
                <div>
                  Người giữ hiện tại:{' '}
                  <span className="font-semibold text-slate-300">
                    {selectedAssignment.assigned_to_user?.full_name}
                  </span>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">
                  Nhân viên tiếp nhận mới <span className="text-red-400">*</span>
                </label>
                <select
                  required
                  value={transferFormData.target_user_id}
                  onChange={(e) => setTransferFormData({ ...transferFormData, target_user_id: e.target.value })}
                  className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-amber-500 outline-none text-white"
                >
                  <option value="">-- Chọn nhân viên nhận tài sản --</option>
                  {usersList
                    .filter((u) => u.id !== selectedAssignment.assigned_to_user_id)
                    .map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.full_name} ({u.email})
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">Phòng ban mới (Tùy chọn)</label>
                <select
                  value={transferFormData.department_id}
                  onChange={(e) => setTransferFormData({ ...transferFormData, department_id: e.target.value })}
                  className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-amber-500 outline-none text-white"
                >
                  <option value="">-- Cập nhật theo phòng ban người nhận mới --</option>
                  {departmentsList.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">Ghi chú chuyển giao</label>
                <textarea
                  rows={2}
                  value={transferFormData.notes}
                  onChange={(e) => setTransferFormData({ ...transferFormData, notes: e.target.value })}
                  placeholder="Lý do bàn giao giữa 2 nhân viên..."
                  className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-amber-500 outline-none text-white"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-700">
                <button
                  type="button"
                  onClick={() => setShowTransferModal(false)}
                  className="px-4 py-2.5 rounded-xl bg-slate-700 hover:bg-slate-600 text-slate-200 font-semibold"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-white font-semibold shadow-lg shadow-amber-500/20 disabled:opacity-60"
                >
                  {formSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Đang chuyển giao...</span>
                    </>
                  ) : (
                    <span>Xác nhận Chuyển giao</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default function AssignmentsPage() {
  return (
    <ProtectedRoute>
      <AssignmentsContent />
    </ProtectedRoute>
  );
}
