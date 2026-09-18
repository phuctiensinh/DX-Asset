'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/lib/auth-context';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { Navbar } from '@/components/Navbar';
import { fetchApi } from '@/lib/api';
import {
  Boxes,
  Plus,
  Search,
  Filter,
  Eye,
  Edit3,
  X,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Tag,
  Building2,
  User as UserIcon,
  Calendar,
  QrCode,
  Laptop,
} from 'lucide-react';

interface Asset {
  id: number;
  asset_code: string;
  name: string;
  category: string;
  brand?: string | null;
  model?: string | null;
  serial_number?: string | null;
  status: string;
  purchase_date?: string | null;
  warranty_expiry?: string | null;
  current_user_id?: number | null;
  department_id?: number | null;
  location?: string | null;
  description?: string | null;
  qr_code_url?: string | null;
  created_at: string;
  updated_at: string;
  current_user?: { id: number; full_name: string; email: string } | null;
  department?: { id: number; code: string; name: string } | null;
}

interface AssetListResponse {
  items: Asset[];
  total: number;
  skip: number;
  limit: number;
}

function AssetsContent() {
  const { user } = useAuth();
  const canEdit = user?.role === 'ADMIN' || user?.role === 'IT_ASSET_MANAGER';

  // Data state
  const [assets, setAssets] = useState<Asset[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [skip, setSkip] = useState<number>(0);
  const limit = 10;
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');

  // Modal States
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [showDetailModal, setShowDetailModal] = useState<boolean>(false);
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [showEditModal, setShowEditModal] = useState<boolean>(false);

  // Form State
  const [formData, setFormData] = useState({
    asset_code: '',
    name: '',
    category: 'Laptop',
    brand: '',
    model: '',
    serial_number: '',
    status: 'IN_STOCK',
    location: '',
    description: '',
  });
  const [formSubmitting, setFormSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loadAssets = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append('skip', skip.toString());
      params.append('limit', limit.toString());

      if (search.trim()) params.append('search', search.trim());
      if (statusFilter) params.append('status', statusFilter);
      if (categoryFilter) params.append('category', categoryFilter);

      const data = await fetchApi<AssetListResponse>(`/assets?${params.toString()}`);
      setAssets(data.items);
      setTotal(data.total);
    } catch (err: any) {
      setError(err?.message || 'Không thể tải danh sách tài sản');
    } finally {
      setIsLoading(false);
    }
  }, [skip, search, statusFilter, categoryFilter]);

  useEffect(() => {
    loadAssets();
  }, [loadAssets]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSkip(0);
    loadAssets();
  };

  const handleResetFilters = () => {
    setSearch('');
    setStatusFilter('');
    setCategoryFilter('');
    setSkip(0);
  };

  const openCreateModal = () => {
    setFormData({
      asset_code: '',
      name: '',
      category: 'Laptop',
      brand: '',
      model: '',
      serial_number: '',
      status: 'IN_STOCK',
      location: '',
      description: '',
    });
    setFormError(null);
    setShowCreateModal(true);
  };

  const openEditModal = (asset: Asset) => {
    setSelectedAsset(asset);
    setFormData({
      asset_code: asset.asset_code,
      name: asset.name,
      category: asset.category,
      brand: asset.brand || '',
      model: asset.model || '',
      serial_number: asset.serial_number || '',
      status: asset.status,
      location: asset.location || '',
      description: asset.description || '',
    });
    setFormError(null);
    setShowEditModal(true);
  };

  const openDetailModal = (asset: Asset) => {
    setSelectedAsset(asset);
    setShowDetailModal(true);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!formData.asset_code.trim()) {
      setFormError('Mã tài sản là bắt buộc.');
      return;
    }
    if (!formData.name.trim()) {
      setFormError('Tên tài sản là bắt buộc.');
      return;
    }
    if (!formData.category.trim()) {
      setFormError('Loại tài sản là bắt buộc.');
      return;
    }

    setFormSubmitting(true);
    try {
      await fetchApi<Asset>('/assets', {
        method: 'POST',
        body: JSON.stringify({
          asset_code: formData.asset_code.trim(),
          name: formData.name.trim(),
          category: formData.category.trim(),
          brand: formData.brand.trim() || null,
          model: formData.model.trim() || null,
          serial_number: formData.serial_number.trim() || null,
          status: formData.status,
          location: formData.location.trim() || null,
          description: formData.description.trim() || null,
        }),
      });

      setShowCreateModal(false);
      setSuccessMsg('Thêm tài sản mới thành công!');
      setTimeout(() => setSuccessMsg(null), 4000);
      loadAssets();
    } catch (err: any) {
      setFormError(err?.message || 'Không thể tạo tài sản');
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAsset) return;
    setFormError(null);

    setFormSubmitting(true);
    try {
      await fetchApi<Asset>(`/assets/${selectedAsset.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          name: formData.name.trim(),
          category: formData.category.trim(),
          brand: formData.brand.trim() || null,
          model: formData.model.trim() || null,
          serial_number: formData.serial_number.trim() || null,
          status: formData.status,
          location: formData.location.trim() || null,
          description: formData.description.trim() || null,
        }),
      });

      setShowEditModal(false);
      setSuccessMsg('Cập nhật tài sản thành công!');
      setTimeout(() => setSuccessMsg(null), 4000);
      loadAssets();
    } catch (err: any) {
      setFormError(err?.message || 'Không thể cập nhật tài sản');
    } finally {
      setFormSubmitting(false);
    }
  };

  const getStatusBadge = (statusStr: string) => {
    switch (statusStr) {
      case 'IN_STOCK':
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">Trong kho (In Stock)</span>;
      case 'ASSIGNED':
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/30">Đã cấp phát</span>;
      case 'IN_MAINTENANCE':
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">Đang bảo trì</span>;
      case 'DAMAGED':
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/30">Hỏng hóc</span>;
      case 'RETIRED':
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/30">Đã thanh lý</span>;
      case 'LOST':
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/30">Mất mát</span>;
      default:
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-zinc-500/10 text-zinc-400 border border-zinc-500/30">{statusStr}</span>;
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-800/80 border border-slate-700/70 rounded-2xl p-6 shadow-xl">
          <div>
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400">
                <Boxes className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white tracking-tight">
                  Quản lý Tài sản Doanh nghiệp
                </h1>
                <p className="text-xs text-slate-400 mt-0.5">
                  Tổng số tài sản trong hệ thống: <span className="font-semibold text-sky-400">{total}</span>
                </p>
              </div>
            </div>
          </div>

          {canEdit && (
            <button
              onClick={openCreateModal}
              className="flex items-center justify-center space-x-2 px-4 py-2.5 bg-gradient-to-r from-sky-500 to-sky-600 hover:from-sky-400 hover:to-sky-500 text-white font-semibold text-xs rounded-xl shadow-lg shadow-sky-500/20 transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>Thêm tài sản mới</span>
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
          <form onSubmit={handleSearchSubmit} className="grid grid-cols-1 sm:grid-cols-12 gap-3">
            {/* Search Input */}
            <div className="sm:col-span-6 relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Search className="w-4 h-4" />
              </div>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Tìm mã tài sản, tên thiết bị, serial number..."
                className="w-full pl-10 pr-4 py-2.5 bg-slate-900/80 border border-slate-700 focus:border-sky-500 focus:ring-1 focus:ring-sky-500/20 rounded-xl text-xs text-slate-100 placeholder-slate-500 outline-none"
              />
            </div>

            {/* Status Filter */}
            <div className="sm:col-span-3">
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setSkip(0);
                }}
                className="w-full py-2.5 px-3 bg-slate-900/80 border border-slate-700 focus:border-sky-500 rounded-xl text-xs text-slate-200 outline-none"
              >
                <option value="">Tất cả Trạng thái</option>
                <option value="IN_STOCK">Trong kho (In Stock)</option>
                <option value="ASSIGNED">Đã cấp phát</option>
                <option value="IN_MAINTENANCE">Đang bảo trì</option>
                <option value="DAMAGED">Hỏng hóc</option>
                <option value="RETIRED">Đã thanh lý</option>
                <option value="LOST">Mất mát</option>
              </select>
            </div>

            {/* Category Filter */}
            <div className="sm:col-span-3">
              <select
                value={categoryFilter}
                onChange={(e) => {
                  setCategoryFilter(e.target.value);
                  setSkip(0);
                }}
                className="w-full py-2.5 px-3 bg-slate-900/80 border border-slate-700 focus:border-sky-500 rounded-xl text-xs text-slate-200 outline-none"
              >
                <option value="">Tất cả Loại tài sản</option>
                <option value="Laptop">Laptop</option>
                <option value="Desktop PC">Desktop PC</option>
                <option value="Monitor">Màn hình (Monitor)</option>
                <option value="Printer">Máy in (Printer)</option>
                <option value="Network Switch">Thiết bị mạng (Switch)</option>
                <option value="Keyboard">Bàn phím (Keyboard)</option>
              </select>
            </div>
          </form>

          {(search || statusFilter || categoryFilter) && (
            <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-700/50">
              <span className="text-slate-400">Đang áp dụng bộ lọc nâng cao</span>
              <button
                onClick={handleResetFilters}
                className="text-sky-400 hover:text-sky-300 font-semibold underline flex items-center space-x-1"
              >
                <X className="w-3.5 h-3.5" />
                <span>Xóa bộ lọc</span>
              </button>
            </div>
          )}
        </div>

        {/* Table / List Area */}
        <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl shadow-xl overflow-hidden">
          {isLoading ? (
            <div className="p-12 flex flex-col items-center justify-center space-y-3">
              <Loader2 className="w-8 h-8 text-sky-400 animate-spin" />
              <span className="text-xs text-slate-400">Đang tải danh sách tài sản...</span>
            </div>
          ) : assets.length === 0 ? (
            <div className="p-12 text-center space-y-3">
              <Boxes className="w-12 h-12 text-slate-600 mx-auto" />
              <div className="text-base font-semibold text-slate-300">Không tìm thấy tài sản phù hợp</div>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Vui lòng thử thay đổi từ khóa tìm kiếm hoặc xóa bỏ các bộ lọc đang áp dụng.
              </p>
              {(search || statusFilter || categoryFilter) && (
                <button
                  onClick={handleResetFilters}
                  className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-xs font-semibold rounded-xl text-slate-200 transition-colors"
                >
                  Xóa bộ lọc
                </button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900/80 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-700/80">
                  <tr>
                    <th className="py-3.5 px-4">Mã TS</th>
                    <th className="py-3.5 px-4">Tên Tài Sản</th>
                    <th className="py-3.5 px-4">Loại</th>
                    <th className="py-3.5 px-4">Serial Number</th>
                    <th className="py-3.5 px-4">Trạng Thái</th>
                    <th className="py-3.5 px-4">Vị Trí / Phòng Ban</th>
                    <th className="py-3.5 px-4">Người Sử Dụng</th>
                    <th className="py-3.5 px-4 text-right">Thao Tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/60">
                  {assets.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-700/40 transition-colors">
                      <td className="py-3.5 px-4 font-bold text-sky-400 font-mono">
                        {item.asset_code}
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-white">
                        <div>{item.name}</div>
                        {(item.brand || item.model) && (
                          <div className="text-[11px] text-slate-400 font-normal">
                            {[item.brand, item.model].filter(Boolean).join(' - ')}
                          </div>
                        )}
                      </td>
                      <td className="py-3.5 px-4 font-medium text-slate-300">
                        {item.category}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-400">
                        {item.serial_number || '—'}
                      </td>
                      <td className="py-3.5 px-4">
                        {getStatusBadge(item.status)}
                      </td>
                      <td className="py-3.5 px-4 text-slate-300">
                        <div>{item.department?.name || '—'}</div>
                        {item.location && (
                          <div className="text-[11px] text-slate-400">{item.location}</div>
                        )}
                      </td>
                      <td className="py-3.5 px-4">
                        {item.current_user ? (
                          <div className="font-semibold text-slate-200">
                            {item.current_user.full_name}
                          </div>
                        ) : (
                          <span className="text-slate-500 italic">Chưa cấp</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            onClick={() => openDetailModal(item)}
                            className="p-1.5 rounded-lg bg-slate-700/60 hover:bg-slate-600 text-slate-300 hover:text-white transition-colors"
                            title="Xem chi tiết"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          {canEdit && (
                            <button
                              onClick={() => openEditModal(item)}
                              className="p-1.5 rounded-lg bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 border border-sky-500/30 transition-colors"
                              title="Sửa thông tin"
                            >
                              <Edit3 className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </td>
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
                trên tổng số <span className="font-semibold text-white">{total}</span> tài sản
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

      {/* CREATE ASSET MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
          <div className="w-full max-w-lg bg-slate-800 border border-slate-700 rounded-2xl shadow-2xl p-6 text-slate-100 my-8">
            <div className="flex items-center justify-between pb-4 border-b border-slate-700">
              <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                <Plus className="w-5 h-5 text-sky-400" />
                <span>Thêm tài sản mới</span>
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
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">
                    Mã tài sản <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.asset_code}
                    onChange={(e) => setFormData({ ...formData, asset_code: e.target.value })}
                    placeholder="VD: LAP-003"
                    className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-sky-500 outline-none text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">
                    Loại tài sản <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    placeholder="VD: Laptop, Monitor..."
                    className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-sky-500 outline-none text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">
                  Tên tài sản <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="VD: Laptop Apple MacBook Air M2"
                  className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-sky-500 outline-none text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Thương hiệu (Brand)</label>
                  <input
                    type="text"
                    value={formData.brand}
                    onChange={(e) => setFormData({ ...formData, brand: e.target.value })}
                    placeholder="VD: Apple, Dell..."
                    className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-sky-500 outline-none text-white"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Model</label>
                  <input
                    type="text"
                    value={formData.model}
                    onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                    placeholder="VD: Air M2 2023"
                    className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-sky-500 outline-none text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Số Serial</label>
                  <input
                    type="text"
                    value={formData.serial_number}
                    onChange={(e) => setFormData({ ...formData, serial_number: e.target.value })}
                    placeholder="SN-XXXXX"
                    className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-sky-500 outline-none text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Trạng thái ban đầu</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-sky-500 outline-none text-white"
                  >
                    <option value="IN_STOCK">Trong kho (In Stock)</option>
                    <option value="ASSIGNED">Đã cấp phát</option>
                    <option value="IN_MAINTENANCE">Đang bảo trì</option>
                    <option value="DAMAGED">Hỏng hóc</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">Vị trí lưu trữ / Lắp đặt</label>
                <input
                  type="text"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  placeholder="VD: Kho IT Tầng 2"
                  className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-sky-500 outline-none text-white"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">Mô tả / Ghi chú</label>
                <textarea
                  rows={2}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Thông tin ghi chú chi tiết..."
                  className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-sky-500 outline-none text-white"
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
                  disabled={formSubmitting}
                  className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-sky-500 hover:bg-sky-400 text-white font-semibold shadow-lg shadow-sky-500/20 disabled:opacity-60"
                >
                  {formSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Đang lưu...</span>
                    </>
                  ) : (
                    <span>Lưu tài sản</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EDIT ASSET MODAL */}
      {showEditModal && selectedAsset && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
          <div className="w-full max-w-lg bg-slate-800 border border-slate-700 rounded-2xl shadow-2xl p-6 text-slate-100 my-8">
            <div className="flex items-center justify-between pb-4 border-b border-slate-700">
              <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                <Edit3 className="w-5 h-5 text-sky-400" />
                <span>Chỉnh sửa tài sản: {selectedAsset.asset_code}</span>
              </h3>
              <button
                onClick={() => setShowEditModal(false)}
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

            <form onSubmit={handleEditSubmit} className="space-y-4 mt-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-400 mb-1">Mã tài sản (Cố định)</label>
                  <input
                    type="text"
                    disabled
                    value={formData.asset_code}
                    className="w-full p-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-500 font-mono cursor-not-allowed"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Loại tài sản</label>
                  <input
                    type="text"
                    required
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-sky-500 outline-none text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">Tên tài sản</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-sky-500 outline-none text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Thương hiệu</label>
                  <input
                    type="text"
                    value={formData.brand}
                    onChange={(e) => setFormData({ ...formData, brand: e.target.value })}
                    className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-sky-500 outline-none text-white"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Model</label>
                  <input
                    type="text"
                    value={formData.model}
                    onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                    className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-sky-500 outline-none text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Số Serial</label>
                  <input
                    type="text"
                    value={formData.serial_number}
                    onChange={(e) => setFormData({ ...formData, serial_number: e.target.value })}
                    className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-sky-500 outline-none text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Trạng thái</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-sky-500 outline-none text-white"
                  >
                    <option value="IN_STOCK">Trong kho (In Stock)</option>
                    <option value="ASSIGNED">Đã cấp phát</option>
                    <option value="IN_MAINTENANCE">Đang bảo trì</option>
                    <option value="DAMAGED">Hỏng hóc</option>
                    <option value="RETIRED">Đã thanh lý</option>
                    <option value="LOST">Mất mát</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">Vị trí lưu trữ / Lắp đặt</label>
                <input
                  type="text"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-sky-500 outline-none text-white"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">Mô tả / Ghi chú</label>
                <textarea
                  rows={2}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:border-sky-500 outline-none text-white"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-700">
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="px-4 py-2.5 rounded-xl bg-slate-700 hover:bg-slate-600 text-slate-200 font-semibold"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-sky-500 hover:bg-sky-400 text-white font-semibold shadow-lg shadow-sky-500/20 disabled:opacity-60"
                >
                  {formSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Đang cập nhật...</span>
                    </>
                  ) : (
                    <span>Cập nhật thông tin</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* DETAIL MODAL */}
      {showDetailModal && selectedAsset && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
          <div className="w-full max-w-lg bg-slate-800 border border-slate-700 rounded-2xl shadow-2xl p-6 text-slate-100 my-8 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-700">
              <div className="flex items-center space-x-2">
                <Boxes className="w-5 h-5 text-sky-400" />
                <span className="font-mono text-sky-400 font-bold text-base">
                  {selectedAsset.asset_code}
                </span>
              </div>
              <button
                onClick={() => setShowDetailModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div>
              <h3 className="text-xl font-bold text-white leading-snug">{selectedAsset.name}</h3>
              <div className="mt-2 flex items-center space-x-2">
                {getStatusBadge(selectedAsset.status)}
                <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-700 text-slate-300">
                  {selectedAsset.category}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs bg-slate-900/60 p-4 rounded-xl border border-slate-700/60">
              <div>
                <div className="text-slate-400 uppercase font-medium text-[10px]">Thương hiệu / Model</div>
                <div className="font-semibold text-slate-200 mt-0.5">
                  {[selectedAsset.brand, selectedAsset.model].filter(Boolean).join(' ') || '—'}
                </div>
              </div>
              <div>
                <div className="text-slate-400 uppercase font-medium text-[10px]">Số Serial</div>
                <div className="font-mono font-semibold text-slate-200 mt-0.5">
                  {selectedAsset.serial_number || '—'}
                </div>
              </div>
              <div>
                <div className="text-slate-400 uppercase font-medium text-[10px]">Phòng ban quản lý</div>
                <div className="font-semibold text-slate-200 mt-0.5 flex items-center space-x-1.5">
                  <Building2 className="w-3.5 h-3.5 text-slate-400" />
                  <span>{selectedAsset.department?.name || '—'}</span>
                </div>
              </div>
              <div>
                <div className="text-slate-400 uppercase font-medium text-[10px]">Người đang giữ</div>
                <div className="font-semibold text-slate-200 mt-0.5 flex items-center space-x-1.5">
                  <UserIcon className="w-3.5 h-3.5 text-sky-400" />
                  <span>{selectedAsset.current_user?.full_name || 'Chưa cấp phát'}</span>
                </div>
              </div>
              <div className="col-span-2">
                <div className="text-slate-400 uppercase font-medium text-[10px]">Vị trí lắp đặt / kho</div>
                <div className="font-semibold text-slate-200 mt-0.5">
                  {selectedAsset.location || '—'}
                </div>
              </div>
            </div>

            {selectedAsset.description && (
              <div className="text-xs space-y-1">
                <div className="text-slate-400 uppercase font-medium text-[10px]">Mô tả chi tiết</div>
                <div className="p-3 bg-slate-900/40 border border-slate-700/40 rounded-xl text-slate-300">
                  {selectedAsset.description}
                </div>
              </div>
            )}

            <div className="flex items-center justify-between text-xs text-slate-400 pt-3 border-t border-slate-700">
              <div className="flex items-center space-x-1.5">
                <QrCode className="w-4 h-4 text-indigo-400" />
                <span className="font-mono text-[11px]">{selectedAsset.qr_code_url}</span>
              </div>
              <button
                onClick={() => setShowDetailModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-700 hover:bg-slate-600 text-slate-200 font-semibold"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function AssetsPage() {
  return (
    <ProtectedRoute>
      <AssetsContent />
    </ProtectedRoute>
  );
}
