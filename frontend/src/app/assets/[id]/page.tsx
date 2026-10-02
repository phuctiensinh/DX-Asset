'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { Navbar } from '@/components/Navbar';
import { fetchApi, getAssetIntelligenceDetail } from '@/lib/api';
import { AssetIntelligenceDetailResponse } from '@/types/intelligence';
import Link from 'next/link';
import {
  Boxes,
  ArrowLeft,
  BrainCircuit,
  AlertTriangle,
  Clock,
  Wrench,
  DollarSign,
  Shield,
  QrCode,
  Building2,
  User as UserIcon,
  Tag,
  Calendar,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  Loader2,
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

function AssetDetailPageContent() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();

  const [asset, setAsset] = useState<Asset | null>(null);
  const [intelligence, setIntelligence] = useState<AssetIntelligenceDetailResponse | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<number | null>(null);

  const assetIdStr = params?.id as string;
  const assetId = parseInt(assetIdStr, 10);

  const loadData = async () => {
    if (isNaN(assetId)) {
      setError('Mã ID tài sản không hợp lệ.');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setErrorCode(null);

      // Fetch basic asset detail
      const assetData = await fetchApi<Asset>(`/assets/${assetId}`);
      setAsset(assetData);

      // Fetch intelligence detail
      try {
        const intelData = await getAssetIntelligenceDetail(assetId);
        setIntelligence(intelData);
      } catch (intelErr: any) {
        // Intelligence detail call fails if employee lacks permission for company-wide analytics
        console.warn('Intelligence details unavailable or restricted:', intelErr);
      }
    } catch (err: any) {
      const status = err?.status || (err?.message?.includes('403') ? 403 : err?.message?.includes('404') ? 404 : 500);
      setErrorCode(status);
      if (status === 403) {
        setError('Bạn không có quyền xem thông tin chi tiết tài sản này (403 Forbidden).');
      } else if (status === 404) {
        setError(`Không tìm thấy tài sản với ID #${assetId} trong hệ thống (404 Not Found).`);
      } else {
        setError(err?.message || 'Không thể tải dữ liệu chi tiết tài sản.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [assetIdStr]);

  const formatVND = (amount: number) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
  };

  const getStatusBadge = (statusStr: string) => {
    switch (statusStr) {
      case 'IN_STOCK':
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 shadow-sm">Trong kho (In Stock)</span>;
      case 'ASSIGNED':
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 shadow-sm">Đã cấp phát</span>;
      case 'IN_MAINTENANCE':
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200 shadow-sm">Đang bảo trì</span>;
      case 'DAMAGED':
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200 shadow-sm">Hỏng hóc (Damaged)</span>;
      case 'RETIRED':
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200 shadow-sm">Đã thanh lý</span>;
      case 'LOST':
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200 shadow-sm">Mất mát</span>;
      default:
        return <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">{statusStr}</span>;
    }
  };

  const getRiskBadgeStyle = (level?: string) => {
    switch (level) {
      case 'LOW':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'MEDIUM':
        return 'bg-amber-50 text-amber-800 border-amber-200';
      case 'HIGH':
        return 'bg-orange-50 text-orange-700 border-orange-200';
      case 'CRITICAL':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        {/* Top Navigation Control */}
        <div className="flex items-center justify-between">
          <button
            onClick={() => router.back()}
            className="inline-flex items-center space-x-2 px-3.5 py-2 bg-white hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-semibold rounded-xl transition-all shadow-sm"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Quay lại</span>
          </button>

          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center space-x-2 px-3.5 py-2 bg-white hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-semibold rounded-xl transition-all shadow-sm disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-indigo-600' : ''}`} />
            <span>Tải lại</span>
          </button>
        </div>

        {/* Loading State */}
        {loading && !asset && (
          <div className="p-12 bg-white border border-slate-200/90 rounded-2xl flex flex-col items-center justify-center space-y-3 shadow-sm">
            <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
            <span className="text-xs text-slate-500">Đang tải thông tin tài sản #{assetId}...</span>
          </div>
        )}

        {/* Error States */}
        {error && !loading && (
          <div className="p-8 bg-white border border-slate-200/90 rounded-2xl text-center space-y-4 max-w-2xl mx-auto my-8 shadow-sm">
            <div className="p-4 rounded-full bg-rose-50 border border-rose-200 text-rose-600 inline-block">
              {errorCode === 403 ? <Shield className="w-10 h-10" /> : <AlertTriangle className="w-10 h-10" />}
            </div>
            <h2 className="text-xl font-bold text-slate-900">
              {errorCode === 403 ? 'Không có quyền truy cập' : errorCode === 404 ? 'Không tìm thấy tài sản' : 'Lỗi tải dữ liệu'}
            </h2>
            <p className="text-slate-600 text-xs sm:text-sm">{error}</p>
            <div className="flex items-center justify-center space-x-3 pt-2">
              <button
                onClick={loadData}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold transition-colors shadow-md shadow-indigo-600/20"
              >
                Thử lại
              </button>
              <Link
                href="/assets"
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition-colors"
              >
                Danh sách tài sản
              </Link>
            </div>
          </div>
        )}

        {/* Asset Detail Main Content */}
        {asset && !loading && (
          <div className="space-y-6">
            {/* Asset Header Banner */}
            <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
                <div className="space-y-1">
                  <div className="flex items-center space-x-3">
                    <span className="font-mono text-indigo-700 font-extrabold text-base bg-indigo-50 px-3 py-1 rounded-lg border border-indigo-200 shadow-sm">
                      {asset.asset_code}
                    </span>
                    {getStatusBadge(asset.status)}
                    <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
                      {asset.category}
                    </span>
                  </div>
                  <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight pt-1">{asset.name}</h1>
                </div>

                {intelligence && (
                  <div className="flex items-center space-x-3 bg-slate-50 border border-slate-200 p-3 rounded-xl shrink-0">
                    <div className="text-right">
                      <div className="text-[10px] text-slate-500 uppercase font-semibold">Risk Level</div>
                      <div className="text-xs font-bold text-slate-900 mt-0.5">Score: {intelligence.health_risk.risk_score}/100</div>
                    </div>
                    <span className={`px-3 py-1.5 rounded-lg text-xs font-extrabold border ${getRiskBadgeStyle(intelligence.health_risk.risk_level)}`}>
                      {intelligence.health_risk.risk_level}
                    </span>
                  </div>
                )}
              </div>

              {/* Quick Metadata Row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                <div>
                  <span className="text-slate-500 text-[10px] uppercase font-medium">Thương hiệu / Model</span>
                  <div className="font-semibold text-slate-900 mt-0.5">
                    {[asset.brand, asset.model].filter(Boolean).join(' ') || '—'}
                  </div>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] uppercase font-medium">Số Serial</span>
                  <div className="font-mono font-semibold text-slate-900 mt-0.5">
                    {asset.serial_number || '—'}
                  </div>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] uppercase font-medium">Phòng ban</span>
                  <div className="font-semibold text-slate-900 mt-0.5 flex items-center space-x-1">
                    <Building2 className="w-3.5 h-3.5 text-slate-400" />
                    <span>{asset.department?.name || 'Chưa gán'}</span>
                  </div>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] uppercase font-medium">Người giữ tài sản</span>
                  <div className="font-semibold text-slate-900 mt-0.5 flex items-center space-x-1">
                    <UserIcon className="w-3.5 h-3.5 text-indigo-600" />
                    <span>{asset.current_user?.full_name || 'Trong kho (Chưa cấp)'}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Asset Intelligence & Health Section */}
            {intelligence && (
              <div className="bg-white border border-purple-200 rounded-2xl p-6 shadow-sm space-y-5">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center space-x-2 text-purple-700 font-semibold text-base">
                    <BrainCircuit className="w-5 h-5 text-purple-600" />
                    <span>Báo cáo Trí tuệ & Chỉ số Sức khỏe Tài sản (Asset Intelligence)</span>
                  </div>
                  <span className="text-xs text-slate-400">Rule-Based Analytical Metrics</span>
                </div>

                {/* 5 KPI Cards for Intelligence */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                  <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
                    <span className="text-[10px] font-semibold uppercase text-emerald-700">Điểm Sức khỏe</span>
                    <div className="text-2xl font-extrabold text-emerald-700">
                      {intelligence.health_risk.health_score}%
                    </div>
                    <div className="text-[10px] text-slate-500">100 - Risk Score</div>
                  </div>

                  <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
                    <span className="text-[10px] font-semibold uppercase text-rose-700">Số Lượt Sự cố</span>
                    <div className="text-2xl font-extrabold text-slate-900">
                      {intelligence.metrics.incident_count}
                    </div>
                    <div className="text-[10px] text-slate-500">Trong lịch sử</div>
                  </div>

                  <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
                    <span className="text-[10px] font-semibold uppercase text-amber-700">Lượt Bảo trì</span>
                    <div className="text-2xl font-extrabold text-slate-900">
                      {intelligence.metrics.maintenance_count}
                    </div>
                    <div className="text-[10px] text-slate-500">Đợt xử lý</div>
                  </div>

                  <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
                    <span className="text-[10px] font-semibold uppercase text-indigo-700">MTTR Sửa chữa</span>
                    <div className="text-2xl font-extrabold text-indigo-700">
                      {intelligence.metrics.mttr_hours !== null ? `${intelligence.metrics.mttr_hours}h` : 'N/A'}
                    </div>
                    <div className="text-[10px] text-slate-500">Thời gian trung bình</div>
                  </div>

                  <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1 col-span-2 sm:col-span-1">
                    <span className="text-[10px] font-semibold uppercase text-emerald-700">Tổng Chi phí Sửa</span>
                    <div className="text-base sm:text-lg font-extrabold text-emerald-700 truncate">
                      {formatVND(intelligence.metrics.total_repair_cost)}
                    </div>
                    <div className="text-[10px] text-slate-500">Không trùng lặp</div>
                  </div>
                </div>

                {/* Warning Reasons Section */}
                {intelligence.health_risk.warning_reasons.length > 0 ? (
                  <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-2">
                    <div className="flex items-center space-x-2 text-amber-800 text-xs font-bold">
                      <AlertCircle className="w-4 h-4 shrink-0 text-amber-600" />
                      <span>Các nguyên nhân cảnh báo rủi ro bất thường:</span>
                    </div>
                    <ul className="list-disc list-inside text-xs text-amber-900 space-y-1 pl-1">
                      {intelligence.health_risk.warning_reasons.map((reason, idx) => (
                        <li key={idx}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center space-x-2">
                    <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
                    <span>Tài sản vận hành bình thường, không có dấu hiệu cảnh báo bất thường.</span>
                  </div>
                )}
              </div>
            )}

            {/* Technical Information Details Card */}
            <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm space-y-4">
              <div className="border-b border-slate-100 pb-3">
                <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
                  <Boxes className="w-5 h-5 text-indigo-600" />
                  <span>Thông tin Kỹ thuật & Quản lý Chi tiết</span>
                </h3>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                  <div className="font-semibold text-indigo-600 uppercase text-[11px]">Thông số Thiết bị</div>
                  <div className="space-y-1 text-slate-700">
                    <div><span className="text-slate-500">Mã tài sản:</span> <span className="font-mono text-slate-900 font-bold">{asset.asset_code}</span></div>
                    <div><span className="text-slate-500">Tên thiết bị:</span> <span className="text-slate-900 font-medium">{asset.name}</span></div>
                    <div><span className="text-slate-500">Danh mục:</span> {asset.category}</div>
                    <div><span className="text-slate-500">Thương hiệu:</span> {asset.brand || '—'}</div>
                    <div><span className="text-slate-500">Model:</span> {asset.model || '—'}</div>
                    <div><span className="text-slate-500">Số Serial:</span> <span className="font-mono text-slate-900">{asset.serial_number || '—'}</span></div>
                  </div>
                </div>

                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                  <div className="font-semibold text-indigo-600 uppercase text-[11px]">Vị trí & Phân bổ</div>
                  <div className="space-y-1 text-slate-700">
                    <div><span className="text-slate-500">Trạng thái:</span> {getStatusBadge(asset.status)}</div>
                    <div><span className="text-slate-500">Phòng ban:</span> {asset.department?.name || '—'}</div>
                    <div><span className="text-slate-500">Vị trí kho/lắp đặt:</span> {asset.location || '—'}</div>
                    <div><span className="text-slate-500">Người giữ hiện tại:</span> {asset.current_user?.full_name || 'Chưa cấp phát'}</div>
                    {asset.current_user && (
                      <div><span className="text-slate-500">Email người giữ:</span> <span className="font-mono text-slate-800">{asset.current_user.email}</span></div>
                    )}
                  </div>
                </div>
              </div>

              {asset.description && (
                <div className="space-y-1 text-xs">
                  <span className="text-slate-500 uppercase text-[10px] font-semibold">Mô tả & Ghi chú chi tiết</span>
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-700">
                    {asset.description}
                  </div>
                </div>
              )}

              {asset.qr_code_url && (
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2">
                    <QrCode className="w-5 h-5 text-indigo-600" />
                    <span className="text-slate-700 font-mono text-[11px]">{asset.qr_code_url}</span>
                  </div>
                  <span className="text-[10px] text-slate-500">Mã QR Định danh</span>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default function AssetDetailPage() {
  return (
    <ProtectedRoute>
      <AssetDetailPageContent />
    </ProtectedRoute>
  );
}
