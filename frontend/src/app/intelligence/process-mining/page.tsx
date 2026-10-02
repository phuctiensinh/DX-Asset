'use client';

import { Fragment, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import Link from 'next/link';
import { AlertCircle, Activity, BarChart3, ChevronLeft, ChevronRight, Clock3, GitBranch, RefreshCw, Shield, X } from 'lucide-react';
import { Navbar } from '@/components/Navbar';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { useAuth } from '@/lib/auth-context';
import {
  getProcessMiningBottlenecks,
  getProcessMiningCase,
  getProcessMiningCases,
  getProcessMiningSummary,
  getProcessMiningVariants,
} from '@/lib/api';
import type {
  ProcessEventSource,
  ProcessEventTimestampQuality,
  ProcessMiningBottleneck,
  ProcessMiningCaseDetail,
  ProcessMiningCases,
  ProcessMiningFilters,
  ProcessMiningSummary,
  ProcessMiningVariants,
} from '@/types/process-mining';

const PAGE_SIZE = 10;

function utcBoundary(value: string): string | undefined {
  if (!value) return undefined;
  return `${value}T00:00:00.000Z`;
}

function formatDate(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

function formatCount(value: number): string {
  return new Intl.NumberFormat('vi-VN').format(value);
}

function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) return 'Chưa đủ dữ liệu';
  const wholeSeconds = Math.max(0, Math.floor(seconds));
  const days = Math.floor(wholeSeconds / 86400);
  const hours = Math.floor((wholeSeconds % 86400) / 3600);
  const minutes = Math.floor((wholeSeconds % 3600) / 60);
  const remainder = wholeSeconds % 60;
  const parts: string[] = [];
  if (days) parts.push(`${days} ngày`);
  if (hours) parts.push(`${hours} giờ`);
  if (minutes && parts.length < 2) parts.push(`${minutes} phút`);
  if (parts.length === 0) parts.push(`${remainder} giây`);
  return parts.join(' ');
}

function apiStatus(error: unknown): number | undefined {
  return error instanceof Error ? (error as Error & { status?: number }).status : undefined;
}

function processMiningErrorMessage(error: unknown): string {
  if (apiStatus(error) === 404) {
    return 'Backend hiện chưa đăng ký đầy đủ Process Mining API (HTTP 404). Hãy khởi động lại FastAPI từ phiên bản mã nguồn hiện tại.';
  }
  return 'Không thể tải dữ liệu Process Mining. Vui lòng thử lại.';
}

function ProcessMiningContent() {
  const { logout } = useAuth();
  const logoutRef = useRef(logout);
  logoutRef.current = logout;

  const [summary, setSummary] = useState<ProcessMiningSummary | null>(null);
  const [variants, setVariants] = useState<ProcessMiningVariants | null>(null);
  const [bottlenecks, setBottlenecks] = useState<ProcessMiningBottleneck[]>([]);
  const [cases, setCases] = useState<ProcessMiningCases | null>(null);
  const [detail, setDetail] = useState<ProcessMiningCaseDetail | null>(null);
  const [selectedCase, setSelectedCase] = useState<number | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [casesLoading, setCasesLoading] = useState(false);
  const [bottlenecksLoading, setBottlenecksLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [denied, setDenied] = useState(false);
  const [accessGranted, setAccessGranted] = useState<boolean | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);
  const [minSample, setMinSample] = useState(5);
  const [caseType, setCaseType] = useState('');
  const [source, setSource] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const filters = useMemo<ProcessMiningFilters>(() => ({
    ...(caseType ? { case_type: caseType as 'INCIDENT' | 'MAINTENANCE' } : {}),
    ...(source ? { source: source as ProcessEventSource } : {}),
    ...(dateFrom ? { date_from: utcBoundary(dateFrom) } : {}),
    ...(dateTo ? { date_to: utcBoundary(dateTo) } : {}),
  }), [caseType, source, dateFrom, dateTo]);

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      setError(null);
      setDenied(false);
      setAccessGranted(null);
      try {
        // Request summary first so an RBAC denial stops the remaining API calls.
        const summaryResult = await getProcessMiningSummary(filters);
        if (!active) return;
        setSummary(summaryResult);
        setAccessGranted(true);
        const variantResult = await getProcessMiningVariants(filters);
        if (!active) return;
        setVariants(variantResult);
      } catch (requestError) {
        if (!active) return;
        if (apiStatus(requestError) === 403) {
          setDenied(true);
          setAccessGranted(false);
          setSummary(null);
          setVariants(null);
          setBottlenecks([]);
          setCases(null);
          return;
        }
        if (apiStatus(requestError) === 401) {
          logoutRef.current();
          return;
        }
        setError(processMiningErrorMessage(requestError));
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => { active = false; };
  }, [filters, retryKey]);

  useEffect(() => {
    if (accessGranted !== true) return;
    let active = true;
    setCasesLoading(true);
    getProcessMiningCases(filters, page, pageSize).then(result => {
      if (active) setCases(result);
    }).catch(requestError => {
      if (!active) return;
      if (apiStatus(requestError) === 403) {
        setDenied(true);
        setAccessGranted(false);
      } else if (apiStatus(requestError) === 401) {
        logoutRef.current();
      } else {
        setError(apiStatus(requestError) === 404 ? processMiningErrorMessage(requestError) : 'Không thể tải danh sách case. Vui lòng thử lại.');
      }
    }).finally(() => {
      if (active) setCasesLoading(false);
    });
    return () => { active = false; };
  }, [accessGranted, filters, page, pageSize, retryKey]);

  useEffect(() => {
    if (accessGranted !== true) return;
    let active = true;
    setBottlenecksLoading(true);
    getProcessMiningBottlenecks(filters, minSample).then(result => {
      if (active) setBottlenecks(result);
    }).catch(requestError => {
      if (!active) return;
      if (apiStatus(requestError) === 403) {
        setDenied(true);
        setAccessGranted(false);
      } else if (apiStatus(requestError) === 401) {
        logoutRef.current();
      } else {
        setError(apiStatus(requestError) === 404 ? processMiningErrorMessage(requestError) : 'Không thể tải dữ liệu bottleneck. Vui lòng thử lại.');
      }
    }).finally(() => {
      if (active) setBottlenecksLoading(false);
    });
    return () => { active = false; };
  }, [accessGranted, filters, minSample, retryKey]);

  async function openCase(caseId: number) {
    setSelectedCase(caseId);
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    try {
      setDetail(await getProcessMiningCase(caseId));
    } catch (requestError) {
      if (apiStatus(requestError) === 403) {
        setDetailError('Bạn không có quyền xem dữ liệu Process Mining.');
      } else if (apiStatus(requestError) === 401) {
        logoutRef.current();
      } else if (apiStatus(requestError) === 404) {
        setDetailError('Không tìm thấy case này trong Process Mining API.');
      } else {
        setDetailError('Không thể tải chi tiết case. Vui lòng thử lại.');
      }
    } finally {
      setDetailLoading(false);
    }
  }

  function closeDetail() {
    setSelectedCase(null);
    setDetail(null);
    setDetailError(null);
  }

  function updateFilter(setter: (value: string) => void, value: string) {
    setPage(1);
    setter(value);
  }

  const maxPage = Math.max(1, Math.ceil((cases?.total ?? 0) / pageSize));

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-slate-50 text-slate-800">
        <Navbar />
        <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
          <header className="flex flex-col gap-4 rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between sm:p-6">
            <div>
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-indigo-600"><Activity className="h-4 w-4" />Process Analytics</div>
              <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl tracking-tight">Process Mining</h1>
              <p className="mt-2 max-w-2xl text-sm text-slate-500">Phân tích quy trình xử lý sự cố và bảo trì dựa trên event log thực tế.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link href="/intelligence" className="rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm text-slate-700 hover:bg-slate-50 font-semibold shadow-sm transition-all">Asset Intelligence</Link>
              <button type="button" onClick={() => setRetryKey(value => value + 1)} disabled={loading} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50 shadow-md shadow-indigo-600/20 transition-all"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />Làm mới</button>
            </div>
          </header>

          {denied ? (
            <section role="alert" className="rounded-2xl border border-amber-200 bg-amber-50 p-8 text-center shadow-sm">
              <Shield className="mx-auto mb-3 h-9 w-9 text-amber-600" />
              <h2 className="text-lg font-semibold text-amber-900">Không có quyền truy cập</h2>
              <p className="mt-2 text-sm text-amber-800">Bạn không có quyền xem dữ liệu Process Mining. Hãy liên hệ quản trị viên nếu bạn cần quyền này.</p>
            </section>
          ) : (
            <>
              {error && <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 shadow-sm"><span className="inline-flex items-center gap-2"><AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />{error}</span><button onClick={() => setRetryKey(value => value + 1)} className="rounded-lg border border-rose-200 bg-white px-3 py-1.5 font-semibold text-rose-700 hover:bg-rose-100">Thử lại</button></div>}

              <section aria-labelledby="overview-title" className="space-y-3">
                <SectionHeading id="overview-title" icon={<BarChart3 className="h-4 w-4 text-indigo-600" />} title="Overview" />
                {loading && !summary ? <LoadingGrid count={6} /> : summary ? <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  <Metric title="Tổng số Case" value={summary.total_cases} />
                  <Metric title="Case hoàn thành" value={summary.completed_cases} tone="emerald" />
                  <Metric title="Case chưa hoàn thành" value={summary.incomplete_cases} tone="amber" />
                  <Metric title="Tổng số Event" value={summary.total_events} />
                  <Metric title="Live Events" value={summary.live_events} tone="sky" />
                  <Metric title="Backfill Events" value={summary.backfill_events} tone="violet" />
                </div> : <EmptyState>Chưa có dữ liệu tổng quan.</EmptyState>}
              </section>

              <section aria-labelledby="quality-title" className="space-y-3">
                <SectionHeading id="quality-title" icon={<Shield className="h-4 w-4 text-purple-600" />} title="Data Quality" />
                {summary ? <div className="grid gap-4 rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm sm:grid-cols-2 lg:grid-cols-3">
                  <QualityGroup title="Source coverage">
                    <div className="flex flex-wrap gap-2 items-center"><SourceBadge source="LIVE" /> <span className="text-sm text-slate-700 font-medium">{formatCount(summary.data_quality.live_case_count)} case · {formatCount(summary.data_quality.live_events)} event</span></div>
                    <div className="mt-2 flex flex-wrap gap-2 items-center"><SourceBadge source="BACKFILL" /> <span className="text-sm text-slate-700 font-medium">{formatCount(summary.data_quality.backfill_case_count)} case · {formatCount(summary.data_quality.backfill_events)} event</span></div>
                    <p className="mt-2 text-xs text-slate-500">Nguồn được giữ riêng biệt; BACKFILL là dữ liệu lịch sử được tái dựng.</p>
                  </QualityGroup>
                  <QualityGroup title="Timestamp quality">
                    <QualityCount label="ACTION_TIME" value={summary.data_quality.action_time_events} />
                    <QualityCount label="LEGACY_FIELD" value={summary.data_quality.legacy_field_events} />
                    <QualityCount label="AMBIGUOUS" value={summary.data_quality.ambiguous_timestamp_events} />
                  </QualityGroup>
                  <QualityGroup title="Coverage gaps">
                    <QualityCount label="Thiếu event tạo case" value={summary.data_quality.cases_without_creation_event} />
                    <QualityCount label="Thiếu event hoàn thành" value={summary.data_quality.cases_without_completion_event} />
                    <QualityCount label="Case chưa hoàn thành" value={summary.data_quality.incomplete_cases} />
                    <QualityCount label="Mixed source" value={summary.data_quality.cases_with_mixed_sources} />
                  </QualityGroup>
                  <p className="text-xs leading-relaxed text-slate-500 sm:col-span-2 lg:col-span-3">{summary.data_quality.cohort_note}</p>
                </div> : loading ? <LoadingPanel /> : <EmptyState>Chưa có dữ liệu chất lượng.</EmptyState>}
              </section>

              <section aria-labelledby="flow-title" className="space-y-3">
                <SectionHeading id="flow-title" icon={<GitBranch className="h-4 w-4 text-indigo-600" />} title="Observed Flow" />
                {loading && !summary ? <LoadingPanel /> : summary?.observed_flow.length ? <div className="grid gap-3 md:grid-cols-2">
                  {summary.observed_flow.map((edge, index) => <article key={`${edge.from_event}-${edge.to_event}-${index}`} className="rounded-2xl border border-slate-200/90 bg-white p-4 shadow-sm">
                    <div className="flex flex-wrap items-center gap-2"><EventTypeBadge>{edge.from_event}</EventTypeBadge><span aria-hidden="true" className="text-slate-400 font-bold">→</span><EventTypeBadge>{edge.to_event}</EventTypeBadge></div>
                    <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-sm text-slate-700"><span>Observations: <strong>{formatCount(edge.count)}</strong></span><span>Median: <strong>{edge.median_duration === null ? 'Chưa đủ timestamp' : formatDuration(edge.median_duration)}</strong></span></div>
                  </article>)}
                </div> : <EmptyState>{summary ? 'Chưa có event edge để hiển thị trong phạm vi lọc.' : 'Chưa có dữ liệu flow.'}</EmptyState>}
              </section>

              <section aria-labelledby="variants-title" className="space-y-3">
                <SectionHeading id="variants-title" icon={<GitBranch className="h-4 w-4 text-purple-600" />} title="Variants" />
                {loading && !variants ? <LoadingPanel /> : variants?.variants.length ? <div className="grid gap-3 lg:grid-cols-2">
                  {variants.variants.map((variant, index) => <article key={variant.variant_id} className="rounded-2xl border border-slate-200/90 bg-white p-4 shadow-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2"><div><p className="text-xs uppercase tracking-wide text-slate-500 font-semibold">Variant {index + 1}</p><p className="mt-1 font-mono text-xs text-indigo-600 font-bold">{variant.variant_id}</p></div><span className="rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700">{formatCount(variant.case_count)} case · {variant.percentage.toFixed(1)}%</span></div>
                    <div className="mt-4 flex flex-wrap items-center gap-2">{variant.event_sequence.map((event, eventIndex) => <Fragment key={`${variant.variant_id}-${eventIndex}`}><EventTypeBadge>{event}</EventTypeBadge>{eventIndex < variant.event_sequence.length - 1 && <span aria-hidden="true" className="text-slate-400 font-bold">→</span>}</Fragment>)}</div>
                    <p className="mt-3 text-xs text-slate-400 italic">Source coverage riêng cho từng variant không có trong API response.</p>
                  </article>)}
                </div> : <EmptyState>{variants ? 'Chưa có variant trong phạm vi lọc.' : 'Chưa có dữ liệu variant.'}</EmptyState>}
              </section>

              <section aria-labelledby="bottlenecks-title" className="space-y-3">
                <div className="flex flex-wrap items-end justify-between gap-3"><SectionHeading id="bottlenecks-title" icon={<Clock3 className="h-4 w-4 text-amber-600" />} title="Bottlenecks" /><label className="flex items-center gap-2 text-xs text-slate-500 font-medium">Min sample
                  <select value={minSample} onChange={event => setMinSample(Number(event.target.value))} className="rounded-xl border border-slate-200 bg-white px-2.5 py-1.5 text-slate-700 shadow-sm focus:border-indigo-500 outline-none" aria-label="Bottleneck minimum sample"><option value={1}>1</option><option value={3}>3</option><option value={5}>5</option><option value={10}>10</option></select>
                </label></div>
                {loading || bottlenecksLoading ? <LoadingPanel /> : bottlenecks.length ? <div className="overflow-x-auto rounded-2xl border border-slate-200/90 bg-white shadow-sm"><table className="min-w-full divide-y divide-slate-200 text-left text-sm"><thead className="bg-slate-50 text-xs uppercase text-slate-500 font-semibold"><tr><th className="px-4 py-3">Transition</th><th className="px-4 py-3">Samples</th><th className="px-4 py-3">Median</th><th className="px-4 py-3">Average</th></tr></thead><tbody className="divide-y divide-slate-100 text-slate-700">{bottlenecks.map((item, index) => <tr key={`${item.from_event}-${item.to_event}-${index}`} className="hover:bg-slate-50/80"><td className="whitespace-nowrap px-4 py-3"><EventTypeBadge>{item.from_event}</EventTypeBadge><span className="mx-2 text-slate-400 font-bold">→</span><EventTypeBadge>{item.to_event}</EventTypeBadge></td><td className="px-4 py-3 font-semibold text-slate-900">{formatCount(item.count)}</td><td className="px-4 py-3 font-semibold text-amber-700">{formatDuration(item.median_duration)}</td><td className="px-4 py-3 text-slate-600">{formatDuration(item.average_duration)}</td></tr>)}</tbody></table></div> : <EmptyState>{summary ? `Chưa có đủ event để phân tích bottleneck (ngưỡng mẫu: ${minSample}).` : 'Chưa có dữ liệu bottleneck.'}</EmptyState>}
              </section>

              <section aria-labelledby="cases-title" className="space-y-3">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                  <SectionHeading id="cases-title" icon={<Activity className="h-4 w-4 text-sky-600" />} title="Case Explorer" />
                </div>
                <div className="grid gap-3 rounded-2xl border border-slate-200/90 bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-5">
                  <label className="grid gap-1 text-xs text-slate-500 font-medium">Case Type<select value={caseType} onChange={event => updateFilter(setCaseType, event.target.value)} className={inputClass}><option value="">Tất cả</option><option value="INCIDENT">INCIDENT</option><option value="MAINTENANCE">MAINTENANCE</option></select></label>
                  <label className="grid gap-1 text-xs text-slate-500 font-medium">Source<select value={source} onChange={event => updateFilter(setSource, event.target.value)} className={inputClass}><option value="">Tất cả</option><option value="LIVE">LIVE</option><option value="BACKFILL">BACKFILL</option></select></label>
                  <label className="grid gap-1 text-xs text-slate-500 font-medium">Từ ngày (UTC)<input type="date" value={dateFrom} onChange={event => updateFilter(setDateFrom, event.target.value)} className={inputClass} /></label>
                  <label className="grid gap-1 text-xs text-slate-500 font-medium">Đến trước ngày (UTC)<input type="date" value={dateTo} onChange={event => updateFilter(setDateTo, event.target.value)} className={inputClass} /></label>
                  <label className="grid gap-1 text-xs text-slate-500 font-medium">Số dòng<select value={pageSize} onChange={event => { setPage(1); setPageSize(Number(event.target.value)); }} className={inputClass}><option value={5}>5</option><option value={10}>10</option><option value={20}>20</option></select></label>
                  <p className="text-xs leading-relaxed text-slate-400 sm:col-span-2 lg:col-span-5">Ngày được gửi dưới dạng thời điểm UTC có timezone. “Đến trước ngày” là ranh giới loại trừ theo API.</p>
                </div>
                {casesLoading || (accessGranted !== true && !cases) ? <LoadingPanel /> : cases?.items.length ? <>
                  <div className="overflow-x-auto rounded-2xl border border-slate-200/90 bg-white shadow-sm"><table className="min-w-[900px] divide-y divide-slate-200 text-left text-sm"><thead className="bg-slate-50 text-xs uppercase text-slate-500 font-semibold"><tr><th className="px-4 py-3">Case ID</th><th className="px-4 py-3">Type</th><th className="px-4 py-3">Created</th><th className="px-4 py-3">Events</th><th className="px-4 py-3">Source</th><th className="px-4 py-3">Last Event</th><th className="px-4 py-3">Completion</th><th className="px-4 py-3">Processing</th><th className="px-4 py-3">Action</th></tr></thead><tbody className="divide-y divide-slate-100 text-slate-700">{cases.items.map(item => <tr key={item.case_id} className="hover:bg-slate-50/80"><td className="px-4 py-3 font-mono font-bold text-indigo-600">CASE-{String(item.case_id).padStart(3, '0')}</td><td className="px-4 py-3"><EventTypeBadge>{item.case_type}</EventTypeBadge></td><td className="whitespace-nowrap px-4 py-3 text-slate-600">{formatDate(item.created_at)}</td><td className="px-4 py-3 text-slate-900 font-medium">{formatCount(item.event_count)}</td><td className="px-4 py-3"><div className="flex flex-wrap gap-1.5">{item.source_coverage.length ? item.source_coverage.map(value => <SourceBadge key={value} source={value} />) : <span className="text-slate-400">Chưa có event</span>}</div></td><td className="whitespace-nowrap px-4 py-3 text-slate-600">{formatDate(item.last_event_at)}</td><td className="px-4 py-3"><CompletionBadge completed={item.completed} /></td><td className="px-4 py-3 text-slate-600">{formatDuration(item.processing_duration)}</td><td className="px-4 py-3"><button onClick={() => void openCase(item.case_id)} className="rounded-xl border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 transition-colors">Xem chi tiết</button></td></tr>)}</tbody></table></div>
                  <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200/90 bg-white px-4 py-3 text-sm text-slate-600 shadow-sm"><span>{formatCount(cases.total)} case · Trang {page} / {maxPage}</span><div className="flex gap-2"><button onClick={() => setPage(value => Math.max(1, value - 1))} disabled={page <= 1 || loading} className="inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-3 py-1.5 disabled:opacity-40 hover:bg-slate-50 shadow-sm font-medium"><ChevronLeft className="h-4 w-4" />Trước</button><button onClick={() => setPage(value => Math.min(maxPage, value + 1))} disabled={page >= maxPage || loading} className="inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-3 py-1.5 disabled:opacity-40 hover:bg-slate-50 shadow-sm font-medium">Sau<ChevronRight className="h-4 w-4" /></button></div></div>
                </> : <EmptyState>{casesLoading ? 'Đang tải case…' : 'Không có case phù hợp với bộ lọc.'}</EmptyState>}
              </section>
            </>
          )}
        </main>
        {selectedCase !== null && <CaseDialog caseId={selectedCase} detail={detail} selected={cases?.items.find(item => item.case_id === selectedCase) ?? null} loading={detailLoading} error={detailError} onClose={closeDetail} />}
      </div>
    </ProtectedRoute>
  );
}

function CaseDialog({ caseId, detail, selected, loading, error, onClose }: {
  caseId: number;
  detail: ProcessMiningCaseDetail | null;
  selected: ProcessMiningCases['items'][number] | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
}) {
  const conformance = detail?.conformance;
  const conformanceLabel = !conformance || conformance.eligible_cases === 0
    ? 'Chưa đủ dữ liệu'
    : conformance.deviating_cases > 0 ? 'Có deviation' : 'Conformant';
  return <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 backdrop-blur-sm p-0 sm:items-center sm:p-4" role="presentation" onClick={onClose}>
    <section role="dialog" aria-modal="true" aria-labelledby="case-dialog-title" className="max-h-[94vh] w-full max-w-4xl overflow-y-auto rounded-t-2xl border border-slate-200/90 bg-white p-5 shadow-2xl text-slate-800 sm:rounded-2xl sm:p-6" onClick={event => event.stopPropagation()}>
      <div className="flex items-start justify-between gap-4"><div><p className="text-xs uppercase tracking-wide text-indigo-600 font-semibold">Case Detail</p><h2 id="case-dialog-title" className="mt-1 text-xl font-bold text-slate-900">CASE-{String(caseId).padStart(3, '0')}</h2></div><button onClick={onClose} aria-label="Đóng chi tiết" className="rounded-xl border border-slate-200 p-2 text-slate-400 hover:text-slate-600"><X className="h-4 w-4" /></button></div>
      {loading ? <LoadingPanel /> : error ? <div role="alert" className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</div> : detail ? <div className="mt-5 space-y-6">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <DetailMetric label="Case Type" value={detail.case_type} />
          <DetailMetric label="Incident ID" value={detail.incident_id === null ? '—' : String(detail.incident_id)} />
          <DetailMetric label="Maintenance ID" value={detail.maintenance_id === null ? '—' : String(detail.maintenance_id)} />
          <DetailMetric label="Created" value={formatDate(selected?.created_at)} />
          <DetailMetric label="Processing time" value={formatDuration(detail.processing_time)} />
          <DetailMetric label="First action" value={formatDuration(detail.first_action_time)} />
          <DetailMetric label="Rework" value={detail.rework_events > 0 ? `${detail.rework_events} event(s)` : 'Không ghi nhận'} />
          <DetailMetric label="Conformance" value={conformanceLabel} />
        </div>
        <div className="flex flex-wrap items-center gap-2"><span className="text-xs text-slate-500 font-medium">Source coverage</span>{detail.source_coverage.length ? detail.source_coverage.map(sourceValue => <SourceBadge key={sourceValue} source={sourceValue} />) : <span className="text-sm text-slate-400">Chưa có event source.</span>}</div>
        <p className="-mt-4 text-xs text-slate-400">Đánh giá dựa trên các transition trạng thái đã được ghi nhận. {conformance?.note}</p>
        <div><h3 className="mb-3 text-sm font-bold text-slate-900">Event Timeline <span className="ml-1 font-normal text-slate-400">({detail.events.length} events)</span></h3>
          {detail.events.length ? <ol className="space-y-0">{detail.events.map((event, index) => <li key={event.id} className="relative flex gap-3 pb-5 last:pb-0"><div className="flex w-5 shrink-0 flex-col items-center"><span className="mt-1 h-3 w-3 rounded-full border-2 border-indigo-600 bg-white" />{index < detail.events.length - 1 && <span className="mt-1 w-px flex-1 bg-slate-200" />}</div><article className="min-w-0 flex-1 rounded-2xl border border-slate-200 bg-slate-50 p-4"><div className="flex flex-wrap items-center justify-between gap-2"><EventTypeBadge>{event.event_type}</EventTypeBadge><span className="text-xs text-slate-500 font-mono">#{event.sequence} · {formatDate(event.occurred_at)}</span></div>{event.from_status !== null && event.to_status !== null && <p className="mt-3 text-sm font-semibold text-slate-900">{event.from_status} <span className="mx-1 text-slate-400">→</span> {event.to_status}</p>}<div className="mt-3 flex flex-wrap gap-2"><SourceBadge source={event.source} /><QualityBadge quality={event.timestamp_quality} /></div>{(event.performed_by_id !== null || event.target_user_id !== null) && <p className="mt-3 text-xs text-slate-500">{event.performed_by_id !== null && <>Performed by ID: {event.performed_by_id}</>}{event.performed_by_id !== null && event.target_user_id !== null && ' · '}{event.target_user_id !== null && <>Target user ID: {event.target_user_id}</>}</p>}</article></li>)}</ol> : <EmptyState>Case này chưa có event được ghi nhận.</EmptyState>}
        </div>
        {conformance?.deviations.length ? <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4"><h3 className="text-sm font-bold text-amber-900">Observed deviations</h3><ul className="mt-2 space-y-2 text-sm text-amber-800">{conformance.deviations.map(deviation => <li key={deviation.event_id}>{deviation.from_status} → {deviation.to_status}: {deviation.reason}</li>)}</ul></div> : null}
      </div> : <EmptyState>Không có dữ liệu case.</EmptyState>}
    </section>
  </div>;
}

function SectionHeading({ id, icon, title }: { id: string; icon: ReactNode; title: string }) {
  return <h2 id={id} className="flex items-center gap-2 text-lg font-bold text-slate-900">{icon}{title}</h2>;
}

function Metric({ title, value, tone = 'slate' }: { title: string; value: number; tone?: 'slate' | 'emerald' | 'amber' | 'sky' | 'violet' }) {
  const styles = { slate: 'text-slate-900', emerald: 'text-emerald-700', amber: 'text-amber-700', sky: 'text-indigo-600', violet: 'text-purple-700' };
  return <article className="rounded-2xl border border-slate-200/90 bg-white p-4 shadow-sm"><p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{title}</p><p className={`mt-2 text-2xl font-bold tabular-nums ${styles[tone]}`}>{formatCount(value)}</p></article>;
}

function DetailMetric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-slate-200 bg-slate-50 p-3"><p className="text-xs text-slate-500 font-medium">{label}</p><p className="mt-1 break-words text-sm font-semibold text-slate-900">{value}</p></div>;
}

function QualityGroup({ title, children }: { title: string; children: ReactNode }) {
  return <div><h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">{title}</h3>{children}</div>;
}

function QualityCount({ label, value }: { label: string; value: number }) {
  if (label === 'ACTION_TIME' || label === 'LEGACY_FIELD' || label === 'AMBIGUOUS') {
    return <div className="mb-2 flex items-center justify-between gap-3"><QualityBadge quality={label} /><span className="text-sm tabular-nums text-slate-900 font-semibold">{formatCount(value)}</span></div>;
  }
  return <p className="mb-1 flex justify-between gap-3 text-sm text-slate-600 font-medium"><span>{label}</span><span className="tabular-nums text-slate-900 font-bold">{formatCount(value)}</span></p>;
}

function SourceBadge({ source }: { source: ProcessEventSource }) {
  const style = source === 'LIVE' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-purple-200 bg-purple-50 text-purple-700';
  return <span title={source === 'BACKFILL' ? 'Event được tái dựng từ dữ liệu lịch sử, không phải event ghi trực tiếp tại thời điểm thao tác.' : undefined} className={`inline-flex rounded-full border px-2.5 py-0.5 text-[10px] font-bold tracking-wide ${style}`}>{source}</span>;
}

function QualityBadge({ quality }: { quality: ProcessEventTimestampQuality | string }) {
  const style = quality === 'ACTION_TIME' ? 'border-indigo-200 bg-indigo-50 text-indigo-700' : quality === 'LEGACY_FIELD' ? 'border-amber-200 bg-amber-50 text-amber-800' : 'border-rose-200 bg-rose-50 text-rose-700';
  return <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-[10px] font-bold tracking-wide ${style}`}>{quality}</span>;
}

function EventTypeBadge({ children }: { children: ReactNode }) {
  return <span className="inline-flex rounded-lg border border-slate-200 bg-slate-100 px-2.5 py-1 font-mono text-[11px] font-semibold text-slate-800">{children}</span>;
}

function CompletionBadge({ completed }: { completed: boolean }) {
  return <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold ${completed ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-amber-200 bg-amber-50 text-amber-800'}`}>{completed ? 'Hoàn thành' : 'Chưa hoàn thành'}</span>;
}

function LoadingGrid({ count }: { count: number }) {
  return <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-label="Đang tải dữ liệu">{Array.from({ length: count }, (_, index) => <div key={index} className="h-24 animate-pulse rounded-2xl border border-slate-200 bg-white shadow-sm" />)}</div>;
}

function LoadingPanel() {
  return <div className="h-28 animate-pulse rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-400 shadow-sm">Đang tải dữ liệu…</div>;
}

function EmptyState({ children }: { children: ReactNode }) {
  return <div className="rounded-2xl border border-dashed border-slate-200 bg-white px-4 py-8 text-center text-sm text-slate-400 shadow-sm">{children}</div>;
}

const inputClass = 'rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none focus:bg-white focus:border-indigo-500 transition-all';

export default function ProcessMiningPage() {
  return <ProcessMiningContent />;
}
