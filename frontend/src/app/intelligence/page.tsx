'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { Navbar } from '@/components/Navbar';
import {
  getIntelligenceSummary,
  getRiskMatrix,
  getTopFailures,
  getTopCostly,
} from '@/lib/api';
import {
  IntelligenceSummaryResponse,
  RiskMatrixItem,
  TopFailureItem,
  TopCostlyItem,
  RiskLevel,
} from '@/types/intelligence';
import Link from 'next/link';
import {
  BrainCircuit,
  AlertTriangle,
  Clock,
  Wrench,
  DollarSign,
  Boxes,
  Shield,
  RefreshCw,
  Search,
  Filter,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';

function IntelligenceContent() {
  const { user } = useAuth();
  const [summary, setSummary] = useState<IntelligenceSummaryResponse | null>(null);
  const [riskMatrix, setRiskMatrix] = useState<RiskMatrixItem[]>([]);
  const [totalMatrix, setTotalMatrix] = useState<number>(0);
  const [topFailures, setTopFailures] = useState<TopFailureItem[]>([]);
  const [topCostly, setTopCostly] = useState<TopCostlyItem[]>([]);

  const [loading, setLoading] = useState<boolean>(true);
  const [matrixLoading, setMatrixLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Filters for Risk Matrix
  const [selectedRiskLevel, setSelectedRiskLevel] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState<string>('');

  const isAllowed = user && ['ADMIN', 'IT_ASSET_MANAGER', 'MANAGER'].includes(user.role);

  // Debounce search query
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 300);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Initial load: Fetch all 4 endpoints once on mount
  const loadAllIntelligenceData = async () => {
    if (!isAllowed) return;

    try {
      setLoading(true);
      setError(null);

      const [summaryRes, matrixRes, failuresRes, costlyRes] = await Promise.all([
        getIntelligenceSummary(),
        getRiskMatrix({
          risk_level: selectedRiskLevel || undefined,
          search: debouncedSearchQuery || undefined,
          limit: 20,
          offset: 0,
        }),
        getTopFailures(5),
        getTopCostly(5),
      ]);

      setSummary(summaryRes);
      setRiskMatrix(matrixRes.items || []);
      setTotalMatrix(matrixRes.total || 0);
      setTopFailures(failuresRes || []);
      setTopCostly(costlyRes || []);
    } catch (err: any) {
      setError(err?.message || 'Không thể tải dữ liệu Trí tuệ Tài sản (Asset Intelligence).');
    } finally {
      setLoading(false);
    }
  };

  // On mount, load initial data
  useEffect(() => {
    loadAllIntelligenceData();
  }, [isAllowed]);

  // When filters change, ONLY re-fetch the risk matrix without clearing summary KPI cards
  useEffect(() => {
    if (!summary) return; // Skip during initial load

    const filterMatrix = async () => {
      try {
        setMatrixLoading(true);
        const matrixRes = await getRiskMatrix({
          risk_level: selectedRiskLevel || undefined,
          search: debouncedSearchQuery || undefined,
          limit: 20,
          offset: 0,
        });
        setRiskMatrix(matrixRes.items || []);
        setTotalMatrix(matrixRes.total || 0);
      } catch (err: any) {
        console.error('Lỗi lọc danh sách ma trận rủi ro:', err);
      } finally {
        setMatrixLoading(false);
      }
    };

    filterMatrix();
  }, [selectedRiskLevel, debouncedSearchQuery]);

  const formatVND = (amount: number) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
  };

  const getRiskBadgeStyle = (level: RiskLevel | string) => {
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

  if (!isAllowed) {
    return (
      <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col">
        <Navbar />
        <main className="flex-1 max-w-4xl w-full mx-auto p-8 flex flex-col items-center justify-center text-center">
          <div className="p-4 rounded-full bg-rose-50 border border-rose-200 text-rose-600 mb-4 shadow-sm">
            <Shield className="w-12 h-12" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 mb-2">Quyền truy cập bị từ chối</h2>
          <p className="text-slate-600 text-sm max-w-md mb-6">
            Bảng điều khiển Trí tuệ Tài sản toàn hệ thống (Asset Intelligence Dashboard) chỉ dành cho người quản trị (Admin), IT Manager hoặc Manager.
          </p>
          <Link
            href="/dashboard"
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-semibold transition-colors shadow-md shadow-indigo-600/20"
          >
            Quay lại Bảng điều khiển
          </Link>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        {/* Banner Header */}
        <div className="relative overflow-hidden bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm">
          <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-purple-50 border border-purple-200 text-purple-700 text-xs font-semibold mb-3">
                <BrainCircuit className="w-3.5 h-3.5 text-purple-600" />
                <span>Phase 13 — Asset Intelligence Analytics (PostgreSQL Real-Time Data)</span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
                Trí tuệ Tài sản & Phân tích Rủi ro
              </h1>
              <p className="text-slate-500 text-sm mt-1">
                Đánh giá sức khỏe thiết bị, phát hiện lỗi lặp lại, tối ưu MTTR và chi phí sửa chữa từ dữ liệu vận hành thực tế.
              </p>
              <div className="flex items-center space-x-2 mt-3">
                <Link href="/intelligence/optimization" className="inline-flex rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 transition-colors">What-if & Optimization →</Link>
                <Link href="/intelligence/process-mining" className="inline-flex rounded-lg border border-purple-200 bg-purple-50 px-3 py-2 text-xs font-semibold text-purple-700 hover:bg-purple-100 transition-colors">Process Mining →</Link>
              </div>
            </div>

            <button
              onClick={loadAllIntelligenceData}
              disabled={loading}
              className="flex items-center space-x-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700 text-xs font-semibold rounded-xl transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-purple-600' : ''}`} />
              <span>Làm mới chỉ số</span>
            </button>
          </div>
        </div>

        {/* Error Notification */}
        {error && (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-center justify-between gap-3 text-rose-800 text-sm shadow-sm">
            <div className="flex items-center space-x-3">
              <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              onClick={loadAllIntelligenceData}
              className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold shrink-0"
            >
              Thử lại
            </button>
          </div>
        )}

        {/* Skeleton Loading */}
        {loading && !summary && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-28 bg-white border border-slate-200 rounded-2xl animate-pulse p-4 shadow-sm"></div>
              ))}
            </div>
            <div className="h-64 bg-white border border-slate-200 rounded-2xl animate-pulse shadow-sm"></div>
          </div>
        )}

        {summary && (
          <div className="space-y-6">
            {/* 5 Key Metric Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              {/* Analyzed Assets */}
              <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm relative overflow-hidden group hover:border-purple-300 transition-all">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Tài sản Phân tích</span>
                  <div className="p-2.5 rounded-xl bg-purple-50 text-purple-700 border border-purple-200">
                    <Boxes className="w-5 h-5" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-extrabold text-slate-900 tracking-tight">{summary.total_assets_analyzed}</div>
                  <p className="text-xs text-slate-500 mt-1">{summary.assets_with_incidents} thiết bị từng hỏng</p>
                </div>
              </div>

              {/* Total Repair Cost */}
              <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm relative overflow-hidden group hover:border-emerald-300 transition-all">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Tổng Chi phí Sửa</span>
                  <div className="p-2.5 rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <DollarSign className="w-5 h-5" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-xl font-extrabold text-emerald-600 tracking-tight">{formatVND(summary.total_repair_cost)}</div>
                  <p className="text-xs text-slate-500 mt-1">Không trùng lặp chi phí</p>
                </div>
              </div>

              {/* Average MTTR */}
              <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm relative overflow-hidden group hover:border-indigo-300 transition-all">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">MTTR Trung bình</span>
                  <div className="p-2.5 rounded-xl bg-indigo-50 text-indigo-700 border border-indigo-200">
                    <Clock className="w-5 h-5" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-extrabold text-indigo-600 tracking-tight">
                    {summary.avg_mttr_hours !== null ? `${summary.avg_mttr_hours}h` : 'N/A'}
                  </div>
                  <p className="text-xs text-slate-500 mt-1">Thời gian sửa hoàn tất</p>
                </div>
              </div>

              {/* High & Critical Risk Assets */}
              <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm relative overflow-hidden group hover:border-rose-300 transition-all">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Rủi ro Cao / Nguy hiểm</span>
                  <div className="p-2.5 rounded-xl bg-rose-50 text-rose-700 border border-rose-200">
                    <AlertTriangle className="w-5 h-5" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-extrabold text-rose-600 tracking-tight">
                    {summary.high_risk_count + summary.critical_risk_count}
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    {summary.high_risk_count} High, {summary.critical_risk_count} Critical
                  </p>
                </div>
              </div>

              {/* Warning Assets */}
              <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm relative overflow-hidden group hover:border-amber-300 transition-all">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Tài sản Cảnh báo</span>
                  <div className="p-2.5 rounded-xl bg-amber-50 text-amber-800 border border-amber-200">
                    <AlertCircle className="w-5 h-5" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-extrabold text-amber-600 tracking-tight">{summary.total_warning_assets}</div>
                  <p className="text-xs text-slate-500 mt-1">Có lý do bất thường</p>
                </div>
              </div>
            </div>

            {/* Risk Level Distribution Breakdown & Formula Disclaimer */}
            <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                <div className="flex items-center space-x-2 text-purple-700 font-semibold text-base">
                  <BrainCircuit className="w-5 h-5 text-purple-600" />
                  <span>Phân bổ Mức độ Rủi ro Tài sản (Risk Level Distribution)</span>
                </div>
                <div className="text-xs text-slate-400 flex items-center space-x-1">
                  <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
                  <span>Analytical Rule-Based Score (0 - 100)</span>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {[
                  { key: 'LOW', label: 'LOW (0 - 15)', count: summary.risk_distribution.LOW || 0, color: 'bg-emerald-500', text: 'text-emerald-700', border: 'border-emerald-200 bg-emerald-50/40' },
                  { key: 'MEDIUM', label: 'MEDIUM (16 - 40)', count: summary.risk_distribution.MEDIUM || 0, color: 'bg-amber-500', text: 'text-amber-800', border: 'border-amber-200 bg-amber-50/40' },
                  { key: 'HIGH', label: 'HIGH (41 - 70)', count: summary.risk_distribution.HIGH || 0, color: 'bg-orange-500', text: 'text-orange-700', border: 'border-orange-200 bg-orange-50/40' },
                  { key: 'CRITICAL', label: 'CRITICAL (> 70)', count: summary.risk_distribution.CRITICAL || 0, color: 'bg-rose-500', text: 'text-rose-700', border: 'border-rose-200 bg-rose-50/40' },
                ].map((item) => {
                  const pct = summary.total_assets_analyzed > 0 ? Math.round((item.count / summary.total_assets_analyzed) * 100) : 0;
                  return (
                    <div
                      key={item.key}
                      onClick={() => setSelectedRiskLevel(selectedRiskLevel === item.key ? '' : item.key)}
                      className={`p-4 border ${item.border} rounded-xl space-y-2 cursor-pointer transition-all hover:scale-[1.02] shadow-sm ${
                        selectedRiskLevel === item.key ? 'ring-2 ring-purple-600' : ''
                      }`}
                    >
                      <div className="flex justify-between items-center text-xs">
                        <span className="font-semibold text-slate-700">{item.label}</span>
                        <span className={`font-bold ${item.text}`}>{pct}%</span>
                      </div>
                      <div className="text-2xl font-bold text-slate-900">{item.count}</div>
                      <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                        <div className={`h-full ${item.color}`} style={{ width: `${pct}%` }}></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Top 5 Frequent Failures & Top 5 Costly Assets Cards */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Top Failures Card */}
              <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center space-x-2 text-rose-700 font-semibold text-base">
                    <Wrench className="w-5 h-5 text-rose-600" />
                    <span>Top 5 Tài sản Tần suất Lỗi Cao nhất</span>
                  </div>
                </div>

                {topFailures.length === 0 ? (
                  <p className="text-xs text-slate-500 text-center py-6">Chưa có tài sản phát sinh sự cố.</p>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {topFailures.map((item, idx) => (
                      <div key={item.asset_id} className="py-3 flex items-center justify-between gap-3 hover:bg-slate-50 px-2 rounded-lg transition-colors">
                        <div className="flex items-center space-x-3">
                          <span className="w-6 h-6 rounded-full bg-rose-50 border border-rose-200 text-rose-700 text-xs font-bold flex items-center justify-center shrink-0">
                            {idx + 1}
                          </span>
                          <div>
                            <Link href={`/assets/${item.asset_id}`} className="font-semibold text-slate-900 hover:text-indigo-600 text-xs sm:text-sm">
                              {item.asset_name}
                            </Link>
                            <div className="text-[11px] text-slate-500 font-mono">
                              {item.asset_code} &bull; {item.category}
                            </div>
                          </div>
                        </div>

                        <div className="text-right shrink-0">
                          <span className="px-2.5 py-1 rounded-lg bg-rose-50 text-rose-700 border border-rose-200 text-xs font-bold">
                            {item.incident_count} sự cố
                          </span>
                          {item.top_category && (
                            <div className="text-[10px] text-slate-500 mt-1">Lỗi chính: {item.top_category}</div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Top Costly Assets Card */}
              <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center space-x-2 text-emerald-700 font-semibold text-base">
                    <DollarSign className="w-5 h-5 text-emerald-600" />
                    <span>Top 5 Tài sản Chi phí Sửa chữa Cao nhất</span>
                  </div>
                </div>

                {topCostly.length === 0 ? (
                  <p className="text-xs text-slate-500 text-center py-6">Chưa có chi phí sửa chữa ghi nhận.</p>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {topCostly.map((item, idx) => (
                      <div key={item.asset_id} className="py-3 flex items-center justify-between gap-3 hover:bg-slate-50 px-2 rounded-lg transition-colors">
                        <div className="flex items-center space-x-3">
                          <span className="w-6 h-6 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-bold flex items-center justify-center shrink-0">
                            {idx + 1}
                          </span>
                          <div>
                            <Link href={`/assets/${item.asset_id}`} className="font-semibold text-slate-900 hover:text-indigo-600 text-xs sm:text-sm">
                              {item.asset_name}
                            </Link>
                            <div className="text-[11px] text-slate-500 font-mono">
                              {item.asset_code} &bull; {item.category}
                            </div>
                          </div>
                        </div>

                        <div className="text-right shrink-0">
                          <div className="text-xs sm:text-sm font-extrabold text-emerald-700">
                            {formatVND(item.total_repair_cost)}
                          </div>
                          <div className="text-[10px] text-slate-500 mt-0.5">{item.maintenance_count} lượt bảo trì</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Risk Matrix & Anomaly Alert Table */}
            <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
                <div>
                  <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
                    <Shield className="w-5 h-5 text-purple-600" />
                    <span>Ma trận Rủi ro & Danh sách Cảnh báo (Asset Risk Matrix)</span>
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Hiển thị tổng số {totalMatrix} tài sản phù hợp bộ lọc
                  </p>
                </div>

                {/* Filter Controls */}
                <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
                  <div className="relative flex-1 sm:w-64">
                    <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      placeholder="Tìm mã hoặc tên tài sản..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-9 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:bg-white focus:border-purple-500 transition-all"
                    />
                  </div>

                  <select
                    value={selectedRiskLevel}
                    onChange={(e) => setSelectedRiskLevel(e.target.value)}
                    className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700 focus:outline-none focus:bg-white focus:border-purple-500 transition-all"
                  >
                    <option value="">Tất cả Mức rủi ro</option>
                    <option value="CRITICAL">🔴 CRITICAL (&gt;70)</option>
                    <option value="HIGH">🟠 HIGH (41-70)</option>
                    <option value="LOW">🟢 LOW (0-15)</option>
                  </select>

                  {matrixLoading && (
                    <RefreshCw className="w-4 h-4 animate-spin text-purple-600" />
                  )}
                </div>
              </div>

              {riskMatrix.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-8">Không tìm thấy tài sản nào phù hợp điều kiện lọc.</p>
              ) : (
                <div className={`overflow-x-auto transition-opacity duration-200 ${matrixLoading ? 'opacity-50 pointer-events-none' : 'opacity-100'}`}>
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-200 text-slate-500 uppercase font-semibold bg-slate-50">
                        <th className="py-3 px-3">Mã / Tên tài sản</th>
                        <th className="py-3 px-3">Danh mục</th>
                        <th className="py-3 px-3 text-center">Risk Level</th>
                        <th className="py-3 px-3 text-center">Score</th>
                        <th className="py-3 px-3">Lý do Cảnh báo</th>
                        <th className="py-3 px-3 text-center">Sự cố</th>
                        <th className="py-3 px-3 text-right">Chi phí Sửa</th>
                        <th className="py-3 px-3 text-center">Hành động</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-700">
                      {riskMatrix.map((item) => (
                        <tr key={item.asset_id} className="hover:bg-slate-50/80 transition-colors">
                          <td className="py-3 px-3">
                            <div className="font-semibold text-slate-900">{item.asset_name}</div>
                            <div className="text-[11px] text-slate-500 font-mono">{item.asset_code}</div>
                          </td>

                          <td className="py-3 px-3 text-slate-600">{item.category}</td>

                          <td className="py-3 px-3 text-center">
                            <span className={`px-2.5 py-1 rounded-lg text-[11px] font-bold border ${getRiskBadgeStyle(item.risk_level)}`}>
                              {item.risk_level}
                            </span>
                          </td>

                          <td className="py-3 px-3 text-center font-bold text-slate-900">
                            {item.risk_score}
                          </td>

                          <td className="py-3 px-3 max-w-xs">
                            {item.warning_reasons.length > 0 ? (
                              <ul className="list-disc list-inside text-[11px] text-amber-800 space-y-0.5">
                                {item.warning_reasons.map((r, i) => (
                                  <li key={i} className="line-clamp-1">{r}</li>
                                ))}
                              </ul>
                            ) : (
                              <span className="text-slate-400 italic text-[11px]">Bình thường</span>
                            )}
                          </td>

                          <td className="py-3 px-3 text-center font-semibold text-slate-700">
                            {item.incident_count}
                          </td>

                          <td className="py-3 px-3 text-right font-mono font-semibold text-emerald-600">
                            {formatVND(item.total_repair_cost)}
                          </td>

                          <td className="py-3 px-3 text-center">
                            <Link
                              href={`/assets/${item.asset_id}`}
                              className="px-2.5 py-1 rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 text-[11px] font-semibold transition-colors inline-flex items-center space-x-1"
                            >
                              <span>Chi tiết</span>
                              <ArrowRight className="w-3 h-3" />
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default function IntelligencePage() {
  return (
    <ProtectedRoute>
      <IntelligenceContent />
    </ProtectedRoute>
  );
}
