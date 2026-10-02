'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/lib/auth-context';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { Navbar } from '@/components/Navbar';
import { fetchApi } from '@/lib/api';
import {
  Wrench,
  Plus,
  Search,
  Filter,
  X,
  Loader2,
  AlertCircle,
  CheckCircle2,
  User as UserIcon,
  Calendar,
  Boxes,
  Eye,
  DollarSign,
  Clock,
  Play,
  CheckCheck,
  AlertTriangle,
  FileText,
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
}

interface IncidentSummary {
  id: number;
  ticket_code: string;
  title: string;
  status: string;
}

interface Maintenance {
  id: number;
  maintenance_code: string;
  asset_id: number;
  incident_id?: number | null;
  technician_id?: number | null;
  status: string;
  title: string;
  description?: string | null;
  start_date?: string | null;
  completed_date?: string | null;
  repair_cost: number;
  resolution_notes?: string | null;
  created_at: string;
  updated_at: string;

  asset?: AssetSummary | null;
  incident?: IncidentSummary | null;
  technician?: UserSummary | null;
}

interface MaintenanceListResponse {
  items: Maintenance[];
  total: number;
  skip: number;
  limit: number;
}

interface AssetListResponse {
  items: AssetSummary[];
  total: number;
}

interface IncidentListResponse {
  items: IncidentSummary[];
  total: number;
}

export default function MaintenancePage() {
  const { user } = useAuth();
  const isManagerOrAdmin = user?.role === 'ADMIN' || user?.role === 'IT_ASSET_MANAGER';

  const [maintenances, setMaintenances] = useState<Maintenance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Dropdown options for asset & incident when creating
  const [availableAssets, setAvailableAssets] = useState<AssetSummary[]>([]);
  const [availableIncidents, setAvailableIncidents] = useState<IncidentSummary[]>([]);

  // Modals
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isCompleteOpen, setIsCompleteOpen] = useState(false);
  const [selectedMnt, setSelectedMnt] = useState<Maintenance | null>(null);

  // Form states
  const [createForm, setCreateForm] = useState({
    asset_id: '',
    incident_id: '',
    title: '',
    description: '',
    repair_cost: '0',
  });
  const [completeForm, setCompleteForm] = useState({
    resolution_notes: '',
    repair_cost: '0',
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Fetch Maintenances
  const loadMaintenances = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.append('status', statusFilter);
      if (search.trim()) params.append('search', search.trim());
      params.append('limit', '100');

      const data = await fetchApi<MaintenanceListResponse>(`/maintenances?${params.toString()}`);
      setMaintenances(data.items || []);
    } catch (err: any) {
      setError(err.message || 'Không thể tải danh sách bảo trì');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, search]);

  useEffect(() => {
    loadMaintenances();
  }, [loadMaintenances]);

  // Load assets & incidents when modal opens
  const loadOptions = async () => {
    try {
      const [assetRes, incRes] = await Promise.all([
        fetchApi<AssetListResponse>('/assets?limit=100'),
        fetchApi<IncidentListResponse>('/incidents?limit=100'),
      ]);
      setAvailableAssets(
        (assetRes.items || []).filter(
          (a) => a.status !== 'RETIRED' && a.status !== 'LOST' && a.status !== 'INACTIVE'
        )
      );
      setAvailableIncidents(incRes.items || []);
    } catch (err) {
      console.error('Error loading options:', err);
    }
  };

  const handleOpenCreate = () => {
    setCreateForm({
      asset_id: '',
      incident_id: '',
      title: '',
      description: '',
      repair_cost: '0',
    });
    setFormError(null);
    loadOptions();
    setIsCreateOpen(true);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createForm.asset_id || !createForm.title.trim()) {
      setFormError('Vui lòng chọn tài sản và nhập tiêu đề bảo trì.');
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      await fetchApi('/maintenances', {
        method: 'POST',
        body: JSON.stringify({
          asset_id: parseInt(createForm.asset_id),
          incident_id: createForm.incident_id ? parseInt(createForm.incident_id) : null,
          title: createForm.title.trim(),
          description: createForm.description.trim() || null,
          repair_cost: parseFloat(createForm.repair_cost) || 0,
        }),
      });
      setIsCreateOpen(false);
      loadMaintenances();
    } catch (err: any) {
      setFormError(err.message || 'Không thể tạo phiếu bảo trì');
    } finally {
      setSubmitting(false);
    }
  };

  const handleStartMaintenance = async (mnt: Maintenance) => {
    if (!confirm(`Xác nhận bắt đầu bảo trì phiếu ${mnt.maintenance_code}? Trạng thái tài sản sẽ chuyển sang IN_MAINTENANCE.`)) {
      return;
    }
    try {
      await fetchApi(`/maintenances/${mnt.id}/start`, {
        method: 'PATCH',
      });
      loadMaintenances();
    } catch (err: any) {
      alert(err.message || 'Lỗi khi bắt đầu bảo trì');
    }
  };

  const handleOpenCompleteModal = (mnt: Maintenance) => {
    setSelectedMnt(mnt);
    setCompleteForm({
      resolution_notes: '',
      repair_cost: mnt.repair_cost ? mnt.repair_cost.toString() : '0',
    });
    setFormError(null);
    setIsCompleteOpen(true);
  };

  const handleCompleteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedMnt) return;
    setSubmitting(true);
    setFormError(null);
    try {
      await fetchApi(`/maintenances/${selectedMnt.id}/complete`, {
        method: 'PATCH',
        body: JSON.stringify({
          resolution_notes: completeForm.resolution_notes.trim() || null,
          repair_cost: parseFloat(completeForm.repair_cost) || 0,
        }),
      });
      setIsCompleteOpen(false);
      loadMaintenances();
    } catch (err: any) {
      setFormError(err.message || 'Lỗi khi hoàn tất bảo trì');
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusBadge = (st: string) => {
    switch (st) {
      case 'SCHEDULED':
        return 'bg-amber-50 text-amber-800 border-amber-200 shadow-sm';
      case 'IN_PROGRESS':
        return 'bg-sky-50 text-sky-700 border-sky-200 shadow-sm animate-pulse';
      case 'COMPLETED':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200 shadow-sm';
      case 'CANCELLED':
        return 'bg-slate-100 text-slate-700 border-slate-200 shadow-sm';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200 shadow-sm';
    }
  };

  const getStatusLabel = (st: string) => {
    switch (st) {
      case 'SCHEDULED':
        return 'Đã lên lịch';
      case 'IN_PROGRESS':
        return 'Đang sửa chữa';
      case 'COMPLETED':
        return 'Hoàn thành';
      case 'CANCELLED':
        return 'Đã hủy';
      default:
        return st;
    }
  };

  // Aggregation stats
  const totalCount = maintenances.length;
  const inProgressCount = maintenances.filter((m) => m.status === 'IN_PROGRESS').length;
  const scheduledCount = maintenances.filter((m) => m.status === 'SCHEDULED').length;
  const completedCount = maintenances.filter((m) => m.status === 'COMPLETED').length;
  const totalCost = maintenances.reduce((acc, m) => acc + (m.repair_cost || 0), 0);

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans">
        <Navbar />

        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-8 py-8 space-y-8">
          {/* Top Banner & Action */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200/90 shadow-sm">
            <div>
              <div className="flex items-center space-x-3">
                <div className="p-3 rounded-xl bg-indigo-50 border border-indigo-100 text-indigo-600 shadow-sm">
                  <Wrench className="w-6 h-6" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Quy trình Bảo trì & Sửa chữa</h1>
                  <p className="text-slate-500 text-sm mt-0.5">
                    Quản lý các đợt bảo trì, khôi phục trạng thái tài sản & ghi nhận chi phí thực tế.
                  </p>
                </div>
              </div>
            </div>

            {isManagerOrAdmin && (
              <button
                onClick={handleOpenCreate}
                className="flex items-center justify-center space-x-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm rounded-xl transition-all shadow-md shadow-indigo-600/20"
              >
                <Plus className="w-4 h-4" />
                <span>Lên kế hoạch bảo trì</span>
              </button>
            )}
          </div>

          {/* Statistics Bar */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-white border border-slate-200/90 p-4 rounded-xl shadow-sm">
              <div className="text-slate-500 text-xs font-semibold">Tổng số lượt</div>
              <div className="text-2xl font-bold text-slate-900 mt-1">{totalCount}</div>
            </div>
            <div className="bg-white border border-slate-200/90 p-4 rounded-xl shadow-sm">
              <div className="text-sky-600 text-xs font-semibold">Đang sửa chữa</div>
              <div className="text-2xl font-bold text-sky-600 mt-1">{inProgressCount}</div>
            </div>
            <div className="bg-white border border-slate-200/90 p-4 rounded-xl shadow-sm">
              <div className="text-amber-600 text-xs font-semibold">Đã lên lịch</div>
              <div className="text-2xl font-bold text-amber-600 mt-1">{scheduledCount}</div>
            </div>
            <div className="bg-white border border-slate-200/90 p-4 rounded-xl shadow-sm">
              <div className="text-emerald-600 text-xs font-semibold">Đã hoàn thành</div>
              <div className="text-2xl font-bold text-emerald-600 mt-1">{completedCount}</div>
            </div>
            <div className="col-span-2 md:col-span-1 bg-white border border-slate-200/90 p-4 rounded-xl shadow-sm">
              <div className="text-slate-500 text-xs font-semibold">Tổng chi phí sửa chữa</div>
              <div className="text-lg font-bold text-emerald-600 mt-1">
                {totalCost.toLocaleString('vi-VN')} VNĐ
              </div>
            </div>
          </div>

          {/* Filters & Search */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white p-4 rounded-xl border border-slate-200/90 shadow-sm">
            <div className="relative w-full sm:w-80">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Tìm mã bảo trì, tiêu đề, mã tài sản..."
                className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-900 focus:outline-none focus:bg-white focus:border-indigo-500 transition-all"
              />
            </div>

            <div className="flex items-center space-x-3 w-full sm:w-auto">
              <Filter className="w-4 h-4 text-slate-400 hidden sm:block" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full sm:w-48 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs text-slate-700 focus:outline-none focus:bg-white focus:border-indigo-500 transition-all"
              >
                <option value="">Tất cả trạng thái</option>
                <option value="SCHEDULED">Đã lên lịch</option>
                <option value="IN_PROGRESS">Đang sửa chữa</option>
                <option value="COMPLETED">Hoàn thành</option>
                <option value="CANCELLED">Đã hủy</option>
              </select>
            </div>
          </div>

          {/* Maintenance List Table */}
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 space-y-3">
              <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
              <div className="text-slate-500 text-sm">Đang tải dữ liệu bảo trì...</div>
            </div>
          ) : error ? (
            <div className="bg-rose-50 border border-rose-200 p-6 rounded-2xl text-center space-y-2 shadow-sm">
              <AlertCircle className="w-8 h-8 text-rose-600 mx-auto" />
              <div className="text-rose-700 font-semibold">{error}</div>
              <button
                onClick={loadMaintenances}
                className="px-4 py-2 bg-rose-100 text-rose-700 rounded-xl text-xs font-semibold hover:bg-rose-200 transition-all"
              >
                Thử lại
              </button>
            </div>
          ) : maintenances.length === 0 ? (
            <div className="bg-white border border-slate-200/90 p-12 rounded-2xl text-center space-y-3 shadow-sm">
              <Wrench className="w-12 h-12 text-slate-300 mx-auto" />
              <div className="text-slate-700 font-medium">Chưa có phiếu bảo trì nào</div>
              <p className="text-slate-500 text-xs max-w-sm mx-auto">
                Không tìm thấy lượt bảo trì phù hợp với bộ lọc hiện tại.
              </p>
            </div>
          ) : (
            <div className="bg-white border border-slate-200/90 rounded-2xl overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 uppercase">
                    <tr>
                      <th className="px-4 py-3.5">Mã phiếu</th>
                      <th className="px-4 py-3.5">Tiêu đề & Tài sản</th>
                      <th className="px-4 py-3.5">Kỹ thuật viên</th>
                      <th className="px-4 py-3.5">Trạng thái</th>
                      <th className="px-4 py-3.5">Chi phí (VNĐ)</th>
                      <th className="px-4 py-3.5">Thời gian</th>
                      <th className="px-4 py-3.5 text-right">Thao tác</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {maintenances.map((mnt) => (
                      <tr key={mnt.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="px-4 py-3.5 font-mono font-semibold text-indigo-600">
                          {mnt.maintenance_code}
                        </td>
                        <td className="px-4 py-3.5">
                          <div className="font-semibold text-slate-900">{mnt.title}</div>
                          <div className="text-[11px] text-slate-500 mt-0.5 flex items-center space-x-1.5">
                            <Boxes className="w-3.5 h-3.5 text-slate-400" />
                            <span>
                              {mnt.asset ? `${mnt.asset.name} (${mnt.asset.asset_code})` : `Asset #${mnt.asset_id}`}
                            </span>
                          </div>
                          {mnt.incident && (
                            <div className="text-[10px] text-amber-600 font-medium mt-0.5">
                              Phiếu sự cố: {mnt.incident.ticket_code}
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3.5 whitespace-nowrap">
                          <div className="flex items-center space-x-1.5 font-medium text-slate-900">
                            <UserIcon className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                            <span>{mnt.technician ? mnt.technician.full_name : 'Chưa phân công'}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3.5 whitespace-nowrap">
                          <span className={`whitespace-nowrap inline-flex items-center px-2.5 py-1 rounded-md border text-[11px] font-medium ${getStatusBadge(mnt.status)}`}>
                            {getStatusLabel(mnt.status)}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 font-mono font-semibold text-emerald-600">
                          {mnt.repair_cost ? `${mnt.repair_cost.toLocaleString('vi-VN')}` : '0'}
                        </td>
                        <td className="px-4 py-3.5 text-slate-500 text-[11px]">
                          <div>Tạo: {new Date(mnt.created_at).toLocaleDateString('vi-VN')}</div>
                          {mnt.completed_date && (
                            <div className="text-emerald-600 font-medium">
                              Xong: {new Date(mnt.completed_date).toLocaleDateString('vi-VN')}
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3.5 text-right space-x-2">
                          <button
                            onClick={() => {
                              setSelectedMnt(mnt);
                              setIsDetailOpen(true);
                            }}
                            className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition-all shadow-sm"
                            title="Xem chi tiết"
                          >
                            <Eye className="w-4 h-4" />
                          </button>

                          {isManagerOrAdmin && mnt.status === 'SCHEDULED' && (
                            <button
                              onClick={() => handleStartMaintenance(mnt)}
                              className="px-2.5 py-1 bg-sky-50 border border-sky-200 text-sky-700 hover:bg-sky-100 rounded-lg font-semibold text-[11px] inline-flex items-center space-x-1 transition-all"
                            >
                              <Play className="w-3 h-3" />
                              <span>Bắt đầu</span>
                            </button>
                          )}

                          {isManagerOrAdmin && mnt.status === 'IN_PROGRESS' && (
                            <button
                              onClick={() => handleOpenCompleteModal(mnt)}
                              className="px-2.5 py-1 bg-emerald-50 border border-emerald-200 text-emerald-700 hover:bg-emerald-100 rounded-lg font-semibold text-[11px] inline-flex items-center space-x-1 transition-all"
                            >
                              <CheckCheck className="w-3 h-3" />
                              <span>Hoàn thành</span>
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </main>

        {/* Modal Create Maintenance */}
        {isCreateOpen && (
          <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white border border-slate-200/90 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl text-slate-800">
              <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center space-x-2 text-slate-900 font-bold text-base">
                  <Wrench className="w-5 h-5 text-indigo-600" />
                  <span>Lên kế hoạch bảo trì thiết bị</span>
                </div>
                <button onClick={() => setIsCreateOpen(false)} className="text-slate-400 hover:text-slate-600">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleCreateSubmit} className="p-6 space-y-4 text-xs">
                {formError && (
                  <div className="bg-rose-50 border border-rose-200 p-3 rounded-xl text-rose-700 font-medium">
                    {formError}
                  </div>
                )}

                <div>
                  <label className="block text-slate-700 font-semibold mb-1">
                    Chọn tài sản bảo trì <span className="text-rose-600">*</span>
                  </label>
                  <select
                    value={createForm.asset_id}
                    onChange={(e) => setCreateForm({ ...createForm, asset_id: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-900 focus:outline-none focus:bg-white focus:border-indigo-500"
                    required
                  >
                    <option value="">-- Chọn tài sản --</option>
                    {availableAssets.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name} ({a.asset_code}) - Trạng thái: {a.status}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-slate-700 font-semibold mb-1">
                    Phiếu sự cố liên kết (Không bắt buộc)
                  </label>
                  <select
                    value={createForm.incident_id}
                    onChange={(e) => setCreateForm({ ...createForm, incident_id: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-900 focus:outline-none focus:bg-white focus:border-indigo-500"
                  >
                    <option value="">-- Không liên kết sự cố --</option>
                    {availableIncidents.map((inc) => (
                      <option key={inc.id} value={inc.id}>
                        [{inc.ticket_code}] {inc.title}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-slate-700 font-semibold mb-1">
                    Tiêu đề bảo trì <span className="text-rose-600">*</span>
                  </label>
                  <input
                    type="text"
                    value={createForm.title}
                    onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                    placeholder="VD: Thay ổ cứng SSD, Thay màn hình..."
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-900 focus:outline-none focus:bg-white focus:border-indigo-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Dự kiến chi phí (VNĐ)</label>
                  <input
                    type="number"
                    min="0"
                    value={createForm.repair_cost}
                    onChange={(e) => setCreateForm({ ...createForm, repair_cost: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-900 focus:outline-none focus:bg-white focus:border-indigo-500 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Mô tả chi tiết</label>
                  <textarea
                    rows={3}
                    value={createForm.description}
                    onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                    placeholder="Chi tiết yêu cầu kỹ thuật hoặc linh kiện thay thế..."
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-900 focus:outline-none focus:bg-white focus:border-indigo-500 resize-none"
                  />
                </div>

                <div className="pt-2 flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => setIsCreateOpen(false)}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl"
                  >
                    Hủy
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl flex items-center space-x-2 shadow-md shadow-indigo-600/20"
                  >
                    {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                    <span>Lưu kế hoạch</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal Complete Maintenance */}
        {isCompleteOpen && selectedMnt && (
          <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white border border-slate-200/90 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl text-slate-800">
              <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center space-x-2 text-slate-900 font-bold text-base">
                  <CheckCheck className="w-5 h-5 text-emerald-600" />
                  <span>Hoàn tất đợt bảo trì [{selectedMnt.maintenance_code}]</span>
                </div>
                <button onClick={() => setIsCompleteOpen(false)} className="text-slate-400 hover:text-slate-600">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleCompleteSubmit} className="p-6 space-y-4 text-xs">
                {formError && (
                  <div className="bg-rose-50 border border-rose-200 p-3 rounded-xl text-rose-700 font-medium">
                    {formError}
                  </div>
                )}

                <div className="bg-slate-50 border border-slate-200 p-3.5 rounded-xl space-y-1">
                  <div className="text-slate-700 font-semibold">Tài sản: {selectedMnt.asset?.name} ({selectedMnt.asset?.asset_code})</div>
                  <div className="text-slate-600">Tiêu đề: {selectedMnt.title}</div>
                </div>

                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Chi phí thực tế (VNĐ)</label>
                  <input
                    type="number"
                    min="0"
                    value={completeForm.repair_cost}
                    onChange={(e) => setCompleteForm({ ...completeForm, repair_cost: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-900 focus:outline-none focus:bg-white focus:border-indigo-500 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Kết quả & Ghi chú hoàn thành</label>
                  <textarea
                    rows={3}
                    value={completeForm.resolution_notes}
                    onChange={(e) => setCompleteForm({ ...completeForm, resolution_notes: e.target.value })}
                    placeholder="VD: Đã thay ổ SSD 512GB, chạy mượt mà, kiểm tra nhiệt độ bình thường..."
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-900 focus:outline-none focus:bg-white focus:border-indigo-500 resize-none"
                  />
                </div>

                <div className="pt-2 flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => setIsCompleteOpen(false)}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl"
                  >
                    Hủy
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl flex items-center space-x-2 shadow-md shadow-emerald-600/20"
                  >
                    {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                    <span>Xác nhận hoàn thành</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal View Detail */}
        {isDetailOpen && selectedMnt && (
          <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white border border-slate-200/90 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl text-slate-800">
              <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center space-x-2 text-slate-900 font-bold text-base">
                  <Wrench className="w-5 h-5 text-indigo-600" />
                  <span>Chi tiết bảo trì [{selectedMnt.maintenance_code}]</span>
                </div>
                <button onClick={() => setIsDetailOpen(false)} className="text-slate-400 hover:text-slate-600">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-6 space-y-4 text-xs text-slate-700">
                <div className="grid grid-cols-2 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200/80">
                  <div>
                    <div className="text-slate-500 text-[11px]">Trạng thái</div>
                    <span className={`inline-block mt-1 px-2.5 py-0.5 rounded-md border text-[11px] font-semibold ${getStatusBadge(selectedMnt.status)}`}>
                      {getStatusLabel(selectedMnt.status)}
                    </span>
                  </div>
                  <div>
                    <div className="text-slate-500 text-[11px]">Chi phí sửa chữa</div>
                    <div className="text-sm font-bold text-emerald-600 mt-1">
                      {selectedMnt.repair_cost ? `${selectedMnt.repair_cost.toLocaleString('vi-VN')} VNĐ` : '0 VNĐ'}
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div><strong className="text-slate-900">Tiêu đề:</strong> {selectedMnt.title}</div>
                  <div><strong className="text-slate-900">Tài sản:</strong> {selectedMnt.asset?.name} (`{selectedMnt.asset?.asset_code}`)</div>
                  {selectedMnt.incident && <div><strong className="text-slate-900">Phiếu sự cố liên kết:</strong> {selectedMnt.incident.ticket_code}</div>}
                  <div><strong className="text-slate-900">Kỹ thuật viên:</strong> {selectedMnt.technician?.full_name || 'Chưa phân công'}</div>
                  {selectedMnt.description && <div><strong className="text-slate-900">Mô tả:</strong> {selectedMnt.description}</div>}
                  {selectedMnt.resolution_notes && (
                    <div className="bg-emerald-50 border border-emerald-200 p-3 rounded-xl text-emerald-800">
                      <strong className="block text-emerald-700 font-semibold mb-1">Ghi chú kết quả:</strong>
                      {selectedMnt.resolution_notes}
                    </div>
                  )}
                </div>

                <div className="pt-4 border-t border-slate-100 flex justify-end">
                  <button
                    onClick={() => setIsDetailOpen(false)}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl"
                  >
                    Đóng
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
