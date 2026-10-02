'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/lib/auth-context';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { Navbar } from '@/components/Navbar';
import { fetchApi } from '@/lib/api';
import Link from 'next/link';
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
  UserCheck,
  Calendar,
  QrCode,
  Laptop,
  BrainCircuit,
  Activity,
  Shield,
} from 'lucide-react';
import { getAssetIntelligenceDetail } from '@/lib/api';
import { AssetIntelligenceDetailResponse } from '@/types/intelligence';

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

  // Intelligence State in Detail Modal
  const [intelDetail, setIntelDetail] = useState<AssetIntelligenceDetailResponse | null>(null);
  const [intelLoading, setIntelLoading] = useState<boolean>(false);

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

  const openDetailModal = async (asset: Asset) => {
    setSelectedAsset(asset);
    setIntelDetail(null);
    setShowDetailModal(true);

    try {
      setIntelLoading(true);
      const data = await getAssetIntelligenceDetail(asset.id);
      setIntelDetail(data);
    } catch {
      // Ignore if user cannot access intelligence
    } finally {
      setIntelLoading(false);
    }
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
        return <span className="whitespace-nowrap inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 shadow-sm">Trong kho (In Stock)</span>;
      case 'ASSIGNED':
        return <span className="whitespace-nowrap inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-200 shadow-sm">Đã cấp phát</span>;
      case 'IN_MAINTENANCE':
        return <span className="whitespace-nowrap inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-800 border border-amber-200 shadow-sm">Đang bảo trì</span>;
      case 'DAMAGED':
        return <span className="whitespace-nowrap inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200 shadow-sm">Hỏng hóc</span>;
      case 'RETIRED':
        return <span className="whitespace-nowrap inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-700 border border-slate-200 shadow-sm">Đã thanh lý</span>;
      case 'LOST':
        return <span className="whitespace-nowrap inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-purple-50 text-purple-700 border border-purple-200 shadow-sm">Mất mát</span>;
      default:
        return <span className="whitespace-nowrap inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-700 border border-slate-200 shadow-sm">{statusStr}</span>;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm">
          <div>
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 font-bold">
                <Boxes className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
                  Quản lý Tài sản Doanh nghiệp
                </h1>
                <p className="text-xs text-slate-500 mt-0.5">
                  Tổng số tài sản trong hệ thống: <span className="font-bold text-indigo-600">{total}</span>
                </p>
              </div>
            </div>
          </div>

          {canEdit && (
            <button
              onClick={openCreateModal}
              className="flex items-center justify-center space-x-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-xl shadow-md shadow-indigo-500/20 transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>Thêm tài sản mới</span>
            </button>
          )}
        </div>

        {/* Global Notifications */}
        {successMsg && (
          <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center space-x-2 shadow-sm">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {error && (
          <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-semibold flex items-center space-x-2 shadow-sm">
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Search & Filter Toolbar */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 sm:p-5 shadow-sm space-y-4">
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
                className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 focus:border-indigo-500 focus:bg-white rounded-xl text-xs text-slate-900 placeholder-slate-400 outline-none transition-all font-medium"
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
                className="w-full py-2.5 px-3 bg-slate-50 border border-slate-200 focus:border-indigo-500 rounded-xl text-xs text-slate-800 font-medium outline-none"
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
                className="w-full py-2.5 px-3 bg-slate-50 border border-slate-200 focus:border-indigo-500 rounded-xl text-xs text-slate-800 font-medium outline-none"
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
            <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-100">
              <span className="text-slate-500">Đang áp dụng bộ lọc nâng cao</span>
              <button
                onClick={handleResetFilters}
                className="text-indigo-600 hover:text-indigo-700 font-semibold underline flex items-center space-x-1"
              >
                <X className="w-3.5 h-3.5" />
                <span>Xóa bộ lọc</span>
              </button>
            </div>
          )}
        </div>

        {/* Table / List Area */}
        <div className="bg-white border border-slate-200/90 rounded-2xl shadow-sm overflow-hidden">
          {isLoading ? (
            <div className="p-12 flex flex-col items-center justify-center space-y-3">
              <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
              <span className="text-xs text-slate-500">Đang tải danh sách tài sản...</span>
            </div>
          ) : assets.length === 0 ? (
            <div className="p-12 text-center space-y-3">
              <Boxes className="w-12 h-12 text-slate-300 mx-auto" />
              <div className="text-base font-bold text-slate-800">Không tìm thấy tài sản phù hợp</div>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Vui lòng thử thay đổi từ khóa tìm kiếm hoặc xóa bỏ các bộ lọc đang áp dụng.
              </p>
              {(search || statusFilter || categoryFilter) && (
                <button
                  onClick={handleResetFilters}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-xs font-semibold rounded-xl text-slate-700 transition-colors"
                >
                  Xóa bộ lọc
                </button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-700">
                <thead className="bg-slate-50 text-slate-500 font-bold uppercase tracking-wider border-b border-slate-200">
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
                <tbody className="divide-y divide-slate-100">
                  {assets.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3.5 px-4 font-extrabold text-indigo-600 font-mono">
                        {item.asset_code}
                      </td>
                      <td className="py-3.5 px-4 font-bold text-slate-900">
                        <div>{item.name}</div>
                        {(item.brand || item.model) && (
                          <div className="text-[11px] text-slate-500 font-normal">
                            {[item.brand, item.model].filter(Boolean).join(' - ')}
                          </div>
                        )}
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-slate-700">
                        {item.category}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-500">
                        {item.serial_number || '—'}
                      </td>
                      <td className="py-3.5 px-4">
                        {getStatusBadge(item.status)}
                      </td>
                      <td className="py-3.5 px-4 text-slate-700 font-medium">
                        <div>{item.department?.name || '—'}</div>
                        {item.location && (
                          <div className="text-[11px] text-slate-500">{item.location}</div>
                        )}
                      </td>
                      <td className="py-3.5 px-4">
                        {item.current_user ? (
                          <div className="font-bold text-slate-900">
                            {item.current_user.full_name}
                          </div>
                        ) : (
                          <span className="text-slate-400 italic">Chưa cấp</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end space-x-2">
                          <Link
                            href={`/assignments?search=${encodeURIComponent(item.asset_code)}`}
                            className="p-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-600 border border-indigo-200 transition-colors"
                            title="Xem lịch sử cấp phát"
                          >
                            <UserCheck className="w-4 h-4" />
                          </Link>
                          <button
                            onClick={() => openDetailModal(item)}
                            className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors"
                            title="Xem chi tiết"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          {canEdit && (
                            <button
                              onClick={() => openEditModal(item)}
                              className="p-1.5 rounded-lg bg-sky-50 hover:bg-sky-100 text-sky-700 border border-sky-200 transition-colors"
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
            <div className="px-4 py-3.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-600 font-medium">
              <div>
                Hiển thị <span className="font-bold text-slate-900">{skip + 1}</span> -{' '}
                <span className="font-bold text-slate-900">
                  {Math.min(skip + limit, total)}
                </span>{' '}
                trên tổng số <span className="font-bold text-slate-900">{total}</span> tài sản
              </div>
              <div className="flex items-center space-x-2">
                <button
                  disabled={skip === 0}
                  onClick={() => setSkip(Math.max(0, skip - limit))}
                  className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-100 text-slate-700 font-semibold shadow-sm"
                >
                  Trang trước
                </button>
                <button
                  disabled={skip + limit >= total}
                  onClick={() => setSkip(skip + limit)}
                  className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-100 text-slate-700 font-semibold shadow-sm"
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm overflow-y-auto">
          <div className="w-full max-w-lg bg-white border border-slate-200 rounded-2xl shadow-xl p-6 text-slate-900 my-8">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <h3 className="text-lg font-bold text-slate-900 flex items-center space-x-2">
                <Plus className="w-5 h-5 text-indigo-600" />
                <span>Thêm tài sản mới</span>
              </h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="mt-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center space-x-2 font-semibold">
                <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-600" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="space-y-4 mt-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Mã tài sản <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.asset_code}
                    onChange={(e) => setFormData({ ...formData, asset_code: e.target.value })}
                    placeholder="VD: LAP-003"
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:border-indigo-500 outline-none text-slate-900 font-mono"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Loại tài sản <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    placeholder="VD: Laptop, Monitor..."
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:border-indigo-500 outline-none text-slate-900"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Tên tài sản <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="VD: Laptop Apple MacBook Air M2"
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:border-indigo-500 outline-none text-slate-900"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Thương hiệu (Brand)</label>
                  <input
                    type="text"
                    value={formData.brand}
                    onChange={(e) => setFormData({ ...formData, brand: e.target.value })}
                    placeholder="VD: Apple, Dell..."
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:border-indigo-500 outline-none text-slate-900"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Model</label>
                  <input
                    type="text"
                    value={formData.model}
                    onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                    placeholder="VD: Air M2 2023"
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:border-indigo-500 outline-none text-slate-900"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Số Serial</label>
                  <input
                    type="text"
                    value={formData.serial_number}
                    onChange={(e) => setFormData({ ...formData, serial_number: e.target.value })}
                    placeholder="SN-XXXXX"
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:border-indigo-500 outline-none text-slate-900 font-mono"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Trạng thái ban đầu</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:border-indigo-500 outline-none text-slate-900"
                  >
                    <option value="IN_STOCK">Trong kho (In Stock)</option>
                    <option value="ASSIGNED">Đã cấp phát</option>
                    <option value="IN_MAINTENANCE">Đang bảo trì</option>
                    <option value="DAMAGED">Hỏng hóc</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Vị trí lưu trữ / Lắp đặt</label>
                <input
                  type="text"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  placeholder="VD: Kho IT Tầng 2"
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:border-indigo-500 outline-none text-slate-900"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Mô tả / Ghi chú</label>
                <textarea
                  rows={2}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Thông tin ghi chú chi tiết..."
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:border-indigo-500 outline-none text-slate-900"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold shadow-md shadow-indigo-500/20 disabled:opacity-60"
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm overflow-y-auto">
          <div className="w-full max-w-lg bg-white border border-slate-200 rounded-2xl shadow-xl p-6 text-slate-900 my-8">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <h3 className="text-lg font-bold text-slate-900 flex items-center space-x-2">
                <Edit3 className="w-5 h-5 text-indigo-600" />
                <span>Chỉnh sửa tài sản: {selectedAsset.asset_code}</span>
              </h3>
              <button
                onClick={() => setShowEditModal(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="mt-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center space-x-2 font-semibold">
                <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-600" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleEditSubmit} className="space-y-4 mt-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-500 mb-1">Mã tài sản (Cố định)</label>
                  <input
                    type="text"
                    disabled
                    value={formData.asset_code}
                    className="w-full p-2.5 bg-slate-100 border border-slate-200 rounded-xl text-slate-500 font-mono cursor-not-allowed font-bold"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Loại tài sản</label>
                  <input
                    type="text"
                    required
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:border-indigo-500 outline-none text-slate-900"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Tên tài sản</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:border-indigo-500 outline-none text-slate-900"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Thương hiệu</label>
                  <input
                    type="text"
                    value={formData.brand}
                    onChange={(e) => setFormData({ ...formData, brand: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:border-indigo-500 outline-none text-slate-900"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Model</label>
                  <input
                    type="text"
                    value={formData.model}
                    onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:border-indigo-500 outline-none text-slate-900"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Số Serial</label>
                  <input
                    type="text"
                    value={formData.serial_number}
                    onChange={(e) => setFormData({ ...formData, serial_number: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:border-indigo-500 outline-none text-slate-900 font-mono"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Trạng thái</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:border-indigo-500 outline-none text-slate-900"
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
                <label className="block font-semibold text-slate-700 mb-1">Vị trí lưu trữ / Lắp đặt</label>
                <input
                  type="text"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:border-indigo-500 outline-none text-slate-900"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Mô tả / Ghi chú</label>
                <textarea
                  rows={2}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:border-indigo-500 outline-none text-slate-900"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold shadow-md shadow-indigo-500/20 disabled:opacity-60"
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm overflow-y-auto">
          <div className="w-full max-w-lg bg-white border border-slate-200 rounded-2xl shadow-xl p-6 text-slate-900 my-8 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center space-x-2">
                <Boxes className="w-5 h-5 text-indigo-600" />
                <span className="font-mono text-indigo-600 font-extrabold text-base">
                  {selectedAsset.asset_code}
                </span>
              </div>
              <button
                onClick={() => setShowDetailModal(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div>
              <h3 className="text-xl font-extrabold text-slate-900 leading-snug">{selectedAsset.name}</h3>
              <div className="mt-2 flex items-center space-x-2">
                {getStatusBadge(selectedAsset.status)}
                <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
                  {selectedAsset.category}
                </span>
              </div>
            </div>


            <div className="grid grid-cols-2 gap-4 text-xs bg-slate-50 p-4 rounded-xl border border-slate-200/90 text-slate-700">
              <div>
                <div className="text-slate-400 font-bold uppercase text-[10px]">Thương hiệu / Model</div>
                <div className="font-bold text-slate-900 mt-0.5">
                  {[selectedAsset.brand, selectedAsset.model].filter(Boolean).join(' ') || '—'}
                </div>
              </div>
              <div>
                <div className="text-slate-400 font-bold uppercase text-[10px]">Số Serial</div>
                <div className="font-mono font-bold text-slate-900 mt-0.5">
                  {selectedAsset.serial_number || '—'}
                </div>
              </div>
              <div>
                <div className="text-slate-400 font-bold uppercase text-[10px]">Phòng ban quản lý</div>
                <div className="font-bold text-slate-900 mt-0.5 flex items-center space-x-1.5">
                  <Building2 className="w-3.5 h-3.5 text-slate-400" />
                  <span>{selectedAsset.department?.name || '—'}</span>
                </div>
              </div>
              <div>
                <div className="text-slate-400 font-bold uppercase text-[10px]">Người đang giữ</div>
                <div className="font-bold text-slate-900 mt-0.5 flex items-center space-x-1.5">
                  <UserIcon className="w-3.5 h-3.5 text-indigo-600" />
                  <span>{selectedAsset.current_user?.full_name || 'Chưa cấp phát'}</span>
                </div>
              </div>
              <div className="col-span-2">
                <div className="text-slate-400 font-bold uppercase text-[10px]">Vị trí lắp đặt / kho</div>
                <div className="font-bold text-slate-900 mt-0.5">
                  {selectedAsset.location || '—'}
                </div>
              </div>
            </div>

            {selectedAsset.description && (
              <div className="text-xs space-y-1">
                <div className="text-slate-400 font-bold uppercase text-[10px]">Mô tả chi tiết</div>
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-700 font-medium">
                  {selectedAsset.description}
                </div>
              </div>
            )}

            {/* Asset Intelligence & Risk Health Card */}
            {intelLoading ? (
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-center text-xs text-slate-500 animate-pulse font-medium">
                Đang phân tích trí tuệ tài sản (Asset Intelligence)...
              </div>
            ) : intelDetail ? (
              <div className="p-4 bg-indigo-50/40 border border-indigo-100 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2 text-indigo-700 text-xs font-bold">
                    <BrainCircuit className="w-4 h-4 text-indigo-600" />
                    <span>Asset Intelligence & Risk Health</span>
                  </div>
                  <span
                    className={`px-2.5 py-0.5 rounded-md text-[10px] font-extrabold border ${
                      intelDetail.health_risk.risk_level === 'LOW'
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : intelDetail.health_risk.risk_level === 'MEDIUM'
                        ? 'bg-amber-50 text-amber-800 border-amber-200'
                        : intelDetail.health_risk.risk_level === 'HIGH'
                        ? 'bg-orange-50 text-orange-800 border-orange-200'
                        : 'bg-rose-50 text-rose-700 border-rose-200'
                    }`}
                  >
                    Risk: {intelDetail.health_risk.risk_level} ({intelDetail.health_risk.risk_score}/100)
                  </span>
                </div>

                <div className="grid grid-cols-4 gap-2 text-center text-xs">
                  <div className="p-2 bg-white rounded-lg border border-slate-200">
                    <div className="text-[10px] text-slate-500 font-medium">Sức khỏe</div>
                    <div className="font-extrabold text-emerald-600 text-sm mt-0.5">
                      {intelDetail.health_risk.health_score}%
                    </div>
                  </div>
                  <div className="p-2 bg-white rounded-lg border border-slate-200">
                    <div className="text-[10px] text-slate-500 font-medium">Sự cố</div>
                    <div className="font-extrabold text-slate-900 text-sm mt-0.5">
                      {intelDetail.metrics.incident_count}
                    </div>
                  </div>
                  <div className="p-2 bg-white rounded-lg border border-slate-200">
                    <div className="text-[10px] text-slate-500 font-medium">MTTR</div>
                    <div className="font-extrabold text-indigo-600 text-sm mt-0.5">
                      {intelDetail.metrics.mttr_hours !== null ? `${intelDetail.metrics.mttr_hours}h` : 'N/A'}
                    </div>
                  </div>
                  <div className="p-2 bg-white rounded-lg border border-slate-200">
                    <div className="text-[10px] text-slate-500 font-medium">Chi phí sửa</div>
                    <div className="font-extrabold text-amber-700 text-xs mt-0.5 truncate">
                      {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(intelDetail.metrics.total_repair_cost)}
                    </div>
                  </div>
                </div>

                {intelDetail.health_risk.warning_reasons.length > 0 && (
                  <div className="text-[11px] text-amber-800 bg-amber-50 border border-amber-200 p-2.5 rounded-lg space-y-1">
                    <div className="font-bold flex items-center space-x-1">
                      <AlertCircle className="w-3.5 h-3.5 shrink-0 text-amber-600" />
                      <span>Cảnh báo rủi ro bất thường:</span>
                    </div>
                    <ul className="list-disc list-inside space-y-0.5 pl-1 text-[10px]">
                      {intelDetail.health_risk.warning_reasons.map((r, idx) => (
                        <li key={idx}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : null}

            <div className="flex items-center justify-between text-xs text-slate-500 pt-3 border-t border-slate-100">
              <div className="flex items-center space-x-1.5">
                <QrCode className="w-4 h-4 text-indigo-600" />
                <span className="font-mono text-[11px]">{selectedAsset.qr_code_url}</span>
              </div>
              <button
                onClick={() => setShowDetailModal(false)}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs shadow-sm"
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
