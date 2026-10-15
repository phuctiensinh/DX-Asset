'use client';

import { Fragment, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import Link from 'next/link';
import {
  AlertCircle,
  Activity,
  BarChart3,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock3,
  GitBranch,
  HelpCircle,
  ListChecks,
  RefreshCw,
  Shield,
  X,
} from 'lucide-react';
import { Navbar } from '@/components/Navbar';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { useAuth } from '@/lib/auth-context';
import { maintenanceStatusLabel } from '@/lib/labels';
import {
  getProcessMiningBottlenecks,
  getProcessMiningCase,
  getProcessMiningCases,
  getProcessMiningSummary,
  getProcessMiningVariants,
} from '@/lib/api';
import type {
  ProcessCaseType,
  ProcessEventSource,
  ProcessMiningBottleneck,
  ProcessMiningCaseDetail,
  ProcessMiningCases,
  ProcessMiningEvent,
  ProcessMiningFilters,
  ProcessMiningSummary,
  ProcessMiningVariants,
} from '@/types/process-mining';

// ---------------------------------------------------------------------------
// Vietnamese labels for internal codes. The API keeps stable machine codes
// (INCIDENT_CREATED, IN_PROGRESS, ...); users only ever see these labels.
// ---------------------------------------------------------------------------

const EVENT_LABELS: Record<string, string> = {
  INCIDENT_CREATED: 'Tạo phiếu sự cố',
  INCIDENT_STATUS_CHANGED: 'Cập nhật trạng thái sự cố',
  TECHNICIAN_ASSIGNED: 'Phân công kỹ thuật viên',
  MAINTENANCE_CREATED: 'Tạo phiếu bảo trì',
  MAINTENANCE_STATUS_CHANGED: 'Cập nhật trạng thái bảo trì',
};

const STATUS_LABELS: Record<string, string> = {
  OPEN: 'Mới tạo',
  IN_REVIEW: 'Đang xem xét',
  IN_PROGRESS: 'Đang xử lý',
  WAITING_FOR_INFO: 'Chờ thông tin',
  RESOLVED: 'Đã khắc phục',
  CLOSED: 'Đã đóng',
  CANCELLED: 'Đã hủy',
  SCHEDULED: 'Đã lên lịch',
  COMPLETED: 'Hoàn thành',
};

const CASE_TYPE_LABELS: Record<ProcessCaseType, string> = {
  INCIDENT: 'Sự cố',
  MAINTENANCE: 'Bảo trì',
};

const SOURCE_LABELS: Record<ProcessEventSource, string> = {
  LIVE: 'Ghi nhận trực tiếp',
  BACKFILL: 'Tái dựng từ lịch sử',
};

const eventLabel = (code: string) => EVENT_LABELS[code] ?? 'Bước khác';
const statusLabel = (code: string | null) => (code ? STATUS_LABELS[code] ?? 'Không xác định' : 'Không xác định');

const PAGE_SIZE_OPTIONS = [5, 10, 20];
const VISIBLE_VARIANTS = 5;

// Dates are picked as whole local days; the API takes UTC instants with an exclusive end
function dayStart(value: string): string {
  return `${value}T00:00:00.000Z`;
}

function nextDayStart(value: string): string {
  const date = new Date(`${value}T00:00:00.000Z`);
  date.setUTCDate(date.getUTCDate() + 1);
  return date.toISOString();
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

function percent(part: number, total: number): string {
  return total > 0 ? `${Math.round((part / total) * 100)}%` : '0%';
}

// Collapse repeated consecutive steps: [A, B, B, B] -> [{A,1}, {B,3}]
function compressSteps(sequence: string[]): { code: string; times: number }[] {
  const steps: { code: string; times: number }[] = [];
  for (const code of sequence) {
    const last = steps[steps.length - 1];
    if (last && last.code === code) last.times += 1;
    else steps.push({ code, times: 1 });
  }
  return steps;
}

function apiStatus(error: unknown): number | undefined {
  return error instanceof Error ? (error as Error & { status?: number }).status : undefined;
}

function loadErrorMessage(error: unknown, what: string): string {
  if (apiStatus(error) === 404) {
    return 'Chức năng phân tích quy trình chưa sẵn sàng trên máy chủ. Vui lòng liên hệ quản trị viên.';
  }
  return `Không thể tải ${what}. Vui lòng thử lại.`;
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
  const [minSample, setMinSample] = useState(3);
  const [showAllVariants, setShowAllVariants] = useState(false);
  const [caseType, setCaseType] = useState('');
  const [source, setSource] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const dateRangeInvalid = Boolean(dateFrom && dateTo && dateFrom > dateTo);

  const filters = useMemo<ProcessMiningFilters>(() => ({
    ...(caseType ? { case_type: caseType as ProcessCaseType } : {}),
    ...(source ? { source: source as ProcessEventSource } : {}),
    ...(dateFrom && !dateRangeInvalid ? { date_from: dayStart(dateFrom) } : {}),
    ...(dateTo && !dateRangeInvalid ? { date_to: nextDayStart(dateTo) } : {}),
  }), [caseType, source, dateFrom, dateTo, dateRangeInvalid]);

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
        setError(loadErrorMessage(requestError, 'dữ liệu phân tích'));
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
        setError(loadErrorMessage(requestError, 'danh sách phiếu'));
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
        setError(loadErrorMessage(requestError, 'dữ liệu thời gian xử lý'));
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
        setDetailError('Bạn không có quyền xem dữ liệu phân tích quy trình.');
      } else if (apiStatus(requestError) === 401) {
        logoutRef.current();
      } else if (apiStatus(requestError) === 404) {
        setDetailError('Không tìm thấy phiếu này.');
      } else {
        setDetailError('Không thể tải hành trình của phiếu. Vui lòng thử lại.');
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

  function resetFilters() {
    setPage(1);
    setCaseType('');
    setSource('');
    setDateFrom('');
    setDateTo('');
  }

  const maxPage = Math.max(1, Math.ceil((cases?.total ?? 0) / pageSize));
  const hasFilters = Boolean(caseType || source || dateFrom || dateTo);
  const sortedBottlenecks = useMemo(
    () => [...bottlenecks].sort((a, b) => b.median_duration - a.median_duration),
    [bottlenecks],
  );
  const slowestMedian = sortedBottlenecks[0]?.median_duration ?? 0;
  const visibleVariants = variants ? (showAllVariants ? variants.variants : variants.variants.slice(0, VISIBLE_VARIANTS)) : [];

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-slate-50 text-slate-800">
        <Navbar />
        <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
          <header className="flex flex-col gap-4 rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between sm:p-6">
            <div>
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-indigo-600"><Activity className="h-4 w-4" />Phân tích vận hành</div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Phân tích quy trình xử lý</h1>
              <p className="mt-2 max-w-2xl text-sm text-slate-500">Xem các phiếu sự cố và bảo trì đã đi qua những bước nào, mất bao lâu và thường bị chậm ở đâu, dựa trên nhật ký thao tác thực tế trong hệ thống.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link href="/intelligence" className="rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-semibold text-slate-700 shadow-sm transition-all hover:bg-slate-50">Phân tích tài sản</Link>
              <button type="button" onClick={() => setRetryKey(value => value + 1)} disabled={loading} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-md shadow-indigo-600/20 transition-all hover:bg-indigo-700 disabled:opacity-50"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />Làm mới</button>
            </div>
          </header>

          {denied ? (
            <section role="alert" className="rounded-2xl border border-amber-200 bg-amber-50 p-8 text-center shadow-sm">
              <Shield className="mx-auto mb-3 h-9 w-9 text-amber-600" />
              <h2 className="text-lg font-semibold text-amber-900">Không có quyền truy cập</h2>
              <p className="mt-2 text-sm text-amber-800">Bạn không có quyền xem trang phân tích quy trình. Hãy liên hệ quản trị viên nếu bạn cần quyền này.</p>
            </section>
          ) : (
            <>
              <HowToRead />

              <section aria-label="Bộ lọc" className="grid gap-3 rounded-2xl border border-slate-200/90 bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-5">
                <label className="grid gap-1 text-xs font-medium text-slate-500">Loại phiếu
                  <select value={caseType} onChange={event => updateFilter(setCaseType, event.target.value)} className={inputClass}>
                    <option value="">Tất cả</option>
                    <option value="INCIDENT">Sự cố</option>
                    <option value="MAINTENANCE">Bảo trì</option>
                  </select>
                </label>
                <label className="grid gap-1 text-xs font-medium text-slate-500">Nguồn dữ liệu
                  <select value={source} onChange={event => updateFilter(setSource, event.target.value)} className={inputClass}>
                    <option value="">Tất cả</option>
                    <option value="LIVE">{SOURCE_LABELS.LIVE}</option>
                    <option value="BACKFILL">{SOURCE_LABELS.BACKFILL}</option>
                  </select>
                </label>
                <label className="grid gap-1 text-xs font-medium text-slate-500">Từ ngày
                  <input type="date" value={dateFrom} onChange={event => updateFilter(setDateFrom, event.target.value)} className={inputClass} />
                </label>
                <label className="grid gap-1 text-xs font-medium text-slate-500">Đến ngày
                  <input type="date" value={dateTo} onChange={event => updateFilter(setDateTo, event.target.value)} className={inputClass} />
                </label>
                <div className="flex items-end">
                  <button type="button" onClick={resetFilters} disabled={!hasFilters} className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-40">Xóa bộ lọc</button>
                </div>
                {dateRangeInvalid && <p role="alert" className="text-xs font-medium text-rose-700 sm:col-span-2 lg:col-span-5">&quot;Từ ngày&quot; phải trước hoặc bằng &quot;Đến ngày&quot;. Bộ lọc ngày đang tạm bỏ qua.</p>}
              </section>

              {error && <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 shadow-sm"><span className="inline-flex items-center gap-2"><AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />{error}</span><button onClick={() => setRetryKey(value => value + 1)} className="rounded-lg border border-rose-200 bg-white px-3 py-1.5 font-semibold text-rose-700 hover:bg-rose-100">Thử lại</button></div>}

              {/* 1. OVERVIEW */}
              <section aria-labelledby="overview-title" className="space-y-3">
                <SectionHeading id="overview-title" icon={<BarChart3 className="h-4 w-4 text-indigo-600" />} title="Tổng quan" />
                {loading && !summary ? <LoadingGrid count={6} /> : summary ? (
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    <Metric title="Số phiếu được phân tích" value={formatCount(summary.total_cases)} hint={`Gồm ${formatCount(summary.total_events)} bước thao tác đã ghi nhận`} />
                    <Metric title="Đã hoàn tất" value={formatCount(summary.completed_cases)} tone="emerald" hint={`${percent(summary.completed_cases, summary.total_cases)} tổng số phiếu`} />
                    <Metric title="Chưa hoàn tất" value={formatCount(summary.incomplete_cases)} tone="amber" hint="Đang xử lý hoặc chưa ghi nhận bước kết thúc" />
                    <Metric title="Thời gian xử lý điển hình" value={formatDuration(summary.processing_time.median)} hint="Từ lúc tạo phiếu đến khi hoàn tất. Một nửa số phiếu nhanh hơn mức này." />
                    <Metric title="Thời gian phản hồi điển hình" value={formatDuration(summary.first_action_time.median)} hint="Từ lúc tạo phiếu đến khi có người bắt đầu xử lý." />
                    <Metric title="Thời gian bảo trì điển hình" value={formatDuration(summary.maintenance_duration.median)} hint="Từ lúc bắt đầu đến khi hoàn thành một đợt bảo trì." />
                  </div>
                ) : <EmptyState>Chưa có dữ liệu tổng quan.</EmptyState>}
              </section>

              {/* 2. COMMON PATHS */}
              <section aria-labelledby="variants-title" className="space-y-3">
                <SectionHeading id="variants-title" icon={<GitBranch className="h-4 w-4 text-purple-600" />} title="Các luồng xử lý thường gặp" description="Mỗi luồng là một chuỗi bước mà các phiếu đã đi qua theo đúng thứ tự. Luồng nào nhiều phiếu nhất là cách làm phổ biến nhất trong thực tế." />
                {loading && !variants ? <LoadingPanel /> : variants?.variants.length ? (
                  <>
                    <div className="grid gap-3 lg:grid-cols-2">
                      {visibleVariants.map((variant, index) => (
                        <article key={variant.variant_id} className="rounded-2xl border border-slate-200/90 bg-white p-4 shadow-sm">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <h3 className="font-bold text-slate-900">Luồng {index + 1}</h3>
                              {index === 0 && <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">Phổ biến nhất</span>}
                            </div>
                            <span className="text-sm font-semibold text-indigo-700">{formatCount(variant.case_count)} phiếu · {variant.percentage.toFixed(1)}%</span>
                          </div>
                          <div className="mt-2 h-1.5 rounded-full bg-slate-100"><div className="h-1.5 rounded-full bg-indigo-500" style={{ width: `${Math.max(2, variant.percentage)}%` }} /></div>
                          <ol className="mt-4 flex flex-wrap items-center gap-2">
                            {compressSteps(variant.event_sequence).map((step, stepIndex, steps) => (
                              <Fragment key={`${variant.variant_id}-${stepIndex}`}>
                                <li className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-800">
                                  <span className="flex h-4 w-4 items-center justify-center rounded-full bg-indigo-100 text-[10px] font-bold text-indigo-700">{stepIndex + 1}</span>
                                  {eventLabel(step.code)}
                                  {step.times > 1 && <span className="text-[11px] font-semibold text-slate-500">× {step.times} lần</span>}
                                </li>
                                {stepIndex < steps.length - 1 && <span aria-hidden="true" className="font-bold text-slate-400">→</span>}
                              </Fragment>
                            ))}
                          </ol>
                        </article>
                      ))}
                    </div>
                    {variants.variants.length > VISIBLE_VARIANTS && (
                      <button type="button" onClick={() => setShowAllVariants(value => !value)} className="text-sm font-semibold text-indigo-600 hover:text-indigo-800">
                        {showAllVariants ? 'Thu gọn' : `Xem thêm ${variants.variants.length - VISIBLE_VARIANTS} luồng khác`}
                      </button>
                    )}
                  </>
                ) : <EmptyState>{variants ? 'Chưa có luồng xử lý nào trong phạm vi lọc.' : 'Chưa có dữ liệu luồng xử lý.'}</EmptyState>}
              </section>

              {/* 3. SLOW STEPS */}
              <section aria-labelledby="bottlenecks-title" className="space-y-3">
                <div className="flex flex-wrap items-end justify-between gap-3">
                  <SectionHeading id="bottlenecks-title" icon={<Clock3 className="h-4 w-4 text-amber-600" />} title="Bước chuyển nào mất nhiều thời gian nhất?" description="Thời gian chờ giữa hai bước liên tiếp, xếp từ chậm nhất. Đây là nơi nên ưu tiên cải thiện." />
                  <label className="flex items-center gap-2 text-xs font-medium text-slate-500">Chỉ tính khi có ít nhất
                    <select value={minSample} onChange={event => setMinSample(Number(event.target.value))} className="rounded-xl border border-slate-200 bg-white px-2.5 py-1.5 text-slate-700 shadow-sm outline-none focus:border-indigo-500">
                      {[1, 3, 5, 10].map(value => <option key={value} value={value}>{value} lượt</option>)}
                    </select>
                  </label>
                </div>
                {loading || bottlenecksLoading ? <LoadingPanel /> : sortedBottlenecks.length ? (
                  <div className="divide-y divide-slate-100 rounded-2xl border border-slate-200/90 bg-white shadow-sm">
                    {sortedBottlenecks.map((item, index) => (
                      <article key={`${item.from_event}-${item.to_event}-${index}`} className="p-4">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="text-sm font-semibold text-slate-900">
                            {eventLabel(item.from_event)} <span className="mx-1 text-slate-400">→</span> {eventLabel(item.to_event)}
                          </p>
                          {index === 0 && sortedBottlenecks.length > 1 && <span className="rounded-full border border-rose-200 bg-rose-50 px-2 py-0.5 text-[11px] font-semibold text-rose-700">Chậm nhất</span>}
                        </div>
                        <div className="mt-2 h-2 rounded-full bg-slate-100"><div className={`h-2 rounded-full ${index === 0 ? 'bg-rose-500' : 'bg-amber-400'}`} style={{ width: `${slowestMedian > 0 ? Math.max(3, (item.median_duration / slowestMedian) * 100) : 3}%` }} /></div>
                        <p className="mt-2 text-xs text-slate-600">
                          Thường mất <strong className="text-slate-900">{formatDuration(item.median_duration)}</strong>
                          {' · '}Trung bình {formatDuration(item.average_duration)}
                          {' · '}Dựa trên {formatCount(item.count)} lượt
                        </p>
                      </article>
                    ))}
                  </div>
                ) : <EmptyState>{summary ? `Chưa có bước chuyển nào đủ ${minSample} lượt để thống kê. Hãy giảm ngưỡng ở góc phải.` : 'Chưa có dữ liệu thời gian xử lý.'}</EmptyState>}
              </section>

              {/* 4. TICKET LIST */}
              <section aria-labelledby="cases-title" className="space-y-3">
                <div className="flex flex-wrap items-end justify-between gap-3">
                  <SectionHeading id="cases-title" icon={<ListChecks className="h-4 w-4 text-sky-600" />} title="Danh sách phiếu" description="Bấm “Xem hành trình” để xem từng bước một phiếu đã đi qua." />
                  <label className="flex items-center gap-2 text-xs font-medium text-slate-500">Hiển thị
                    <select value={pageSize} onChange={event => { setPage(1); setPageSize(Number(event.target.value)); }} className="rounded-xl border border-slate-200 bg-white px-2.5 py-1.5 text-slate-700 shadow-sm outline-none focus:border-indigo-500">
                      {PAGE_SIZE_OPTIONS.map(value => <option key={value} value={value}>{value} dòng</option>)}
                    </select>
                  </label>
                </div>
                {casesLoading || (accessGranted !== true && !cases) ? <LoadingPanel /> : cases?.items.length ? <>
                  <div className="overflow-x-auto rounded-2xl border border-slate-200/90 bg-white shadow-sm">
                    <table className="min-w-[860px] divide-y divide-slate-200 text-left text-sm">
                      <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-500">
                        <tr><th className="px-4 py-3">Mã phiếu</th><th className="px-4 py-3">Nội dung</th><th className="px-4 py-3">Loại</th><th className="px-4 py-3">Ngày tạo</th><th className="px-4 py-3">Số bước</th><th className="px-4 py-3">Tình trạng</th><th className="px-4 py-3">Tổng thời gian</th><th className="px-4 py-3"><span className="sr-only">Thao tác</span></th></tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 text-slate-700">
                        {cases.items.map(item => (
                          <tr key={item.case_id} className="hover:bg-slate-50/80">
                            <td className="whitespace-nowrap px-4 py-3 font-mono text-xs font-bold text-indigo-600">{item.reference_code ?? '—'}</td>
                            <td className="max-w-[260px] truncate px-4 py-3 text-slate-800" title={item.title ?? undefined}>{item.title ?? '—'}</td>
                            <td className="px-4 py-3"><CaseTypeBadge type={item.case_type} /></td>
                            <td className="whitespace-nowrap px-4 py-3 text-slate-600">{formatDate(item.created_at)}</td>
                            <td className="px-4 py-3 font-medium text-slate-900">{formatCount(item.event_count)}</td>
                            <td className="px-4 py-3"><CompletionBadge completed={item.completed} /></td>
                            <td className="whitespace-nowrap px-4 py-3 text-slate-600">{item.completed ? formatDuration(item.processing_duration) : '—'}</td>
                            <td className="px-4 py-3"><button onClick={() => void openCase(item.case_id)} className="whitespace-nowrap rounded-xl border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 transition-colors hover:bg-indigo-100">Xem hành trình</button></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200/90 bg-white px-4 py-3 text-sm text-slate-600 shadow-sm">
                    <span>{formatCount(cases.total)} phiếu · Trang {page} / {maxPage}</span>
                    <div className="flex gap-2">
                      <button onClick={() => setPage(value => Math.max(1, value - 1))} disabled={page <= 1 || loading} className="inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-3 py-1.5 font-medium shadow-sm hover:bg-slate-50 disabled:opacity-40"><ChevronLeft className="h-4 w-4" />Trước</button>
                      <button onClick={() => setPage(value => Math.min(maxPage, value + 1))} disabled={page >= maxPage || loading} className="inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-3 py-1.5 font-medium shadow-sm hover:bg-slate-50 disabled:opacity-40">Sau<ChevronRight className="h-4 w-4" /></button>
                    </div>
                  </div>
                </> : <EmptyState>{casesLoading ? 'Đang tải danh sách phiếu…' : 'Không có phiếu nào phù hợp với bộ lọc.'}</EmptyState>}
              </section>

              {/* 5. DATA RELIABILITY (for people who want to check the numbers) */}
              {summary && <DataReliability summary={summary} />}
            </>
          )}
        </main>
        {selectedCase !== null && <CaseDialog detail={detail} createdAt={cases?.items.find(item => item.case_id === selectedCase)?.created_at ?? null} loading={detailLoading} error={detailError} onClose={closeDetail} />}
      </div>
    </ProtectedRoute>
  );
}

function HowToRead() {
  return (
    <details className="group rounded-2xl border border-indigo-100 bg-indigo-50/50 p-4 text-sm text-slate-700 shadow-sm">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 font-semibold text-indigo-800">
        <span className="inline-flex items-center gap-2"><HelpCircle className="h-4 w-4" />Cách đọc trang này</span>
        <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
      </summary>
      <ul className="mt-3 list-disc space-y-1.5 pl-5 leading-relaxed">
        <li><strong>Phiếu</strong>: một phiếu sự cố (báo hỏng) hoặc một phiếu bảo trì.</li>
        <li><strong>Bước</strong>: một thao tác được hệ thống ghi lại, ví dụ tạo phiếu, phân công kỹ thuật viên, đổi trạng thái.</li>
        <li><strong>Luồng xử lý</strong>: thứ tự các bước một phiếu đã đi qua. Nhiều phiếu đi cùng một thứ tự sẽ được gộp thành một luồng.</li>
        <li><strong>Thời gian điển hình</strong>: một nửa số phiếu nhanh hơn mức này, một nửa chậm hơn. Con số này ít bị ảnh hưởng bởi vài phiếu bất thường hơn so với thời gian trung bình.</li>
        <li><strong>Bước chuyển chậm</strong>: khoảng chờ dài giữa hai bước, cho biết quy trình đang bị nghẽn ở đâu.</li>
      </ul>
    </details>
  );
}

function DataReliability({ summary }: { summary: ProcessMiningSummary }) {
  const quality = summary.data_quality;
  return (
    <details className="group rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2">
        <span className="flex items-center gap-2 text-lg font-bold text-slate-900"><Shield className="h-4 w-4 text-purple-600" />Độ tin cậy của dữ liệu</span>
        <ChevronDown className="h-4 w-4 text-slate-500 transition-transform group-open:rotate-180" />
      </summary>
      <p className="mt-2 text-sm text-slate-500">Dành cho người cần kiểm chứng số liệu: dữ liệu đến từ đâu và có thiếu sót gì không.</p>
      <div className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        <QualityGroup title="Nguồn dữ liệu">
          <QualityRow label={SOURCE_LABELS.LIVE} value={`${formatCount(quality.live_events)} bước`} />
          <QualityRow label={SOURCE_LABELS.BACKFILL} value={`${formatCount(quality.backfill_events)} bước`} />
          <p className="mt-2 text-xs leading-relaxed text-slate-500">&quot;Ghi nhận trực tiếp&quot; được lưu ngay khi người dùng thao tác. &quot;Tái dựng từ lịch sử&quot; được tạo lại từ dữ liệu cũ (trước khi có nhật ký thao tác) nên có thể thiếu bước.</p>
        </QualityGroup>
        <QualityGroup title="Độ chính xác của thời gian">
          <QualityRow label="Chính xác" value={formatCount(quality.action_time_events)} />
          <QualityRow label="Ước lượng từ dữ liệu cũ" value={formatCount(quality.legacy_field_events)} />
          <QualityRow label="Không chắc chắn" value={formatCount(quality.ambiguous_timestamp_events)} />
        </QualityGroup>
        <QualityGroup title="Phiếu có dữ liệu chưa đầy đủ">
          <QualityRow label="Thiếu bước tạo phiếu" value={formatCount(quality.cases_without_creation_event)} />
          <QualityRow label="Thiếu bước kết thúc" value={formatCount(quality.cases_without_completion_event)} />
          <QualityRow label="Có cả hai nguồn dữ liệu" value={formatCount(quality.cases_with_mixed_sources)} />
        </QualityGroup>
      </div>
    </details>
  );
}

function CaseDialog({ detail, createdAt, loading, error, onClose }: {
  detail: ProcessMiningCaseDetail | null;
  createdAt: string | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
}) {
  const conformance = detail?.conformance;
  const conformanceLabel = !conformance || conformance.eligible_cases === 0
    ? 'Chưa đủ dữ liệu'
    : conformance.deviations.length > 0 ? `Có ${conformance.deviations.length} bước sai quy trình` : 'Đúng quy trình';
  return <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 p-0 backdrop-blur-sm sm:items-center sm:p-4" role="presentation" onClick={onClose}>
    <section role="dialog" aria-modal="true" aria-labelledby="case-dialog-title" className="max-h-[94vh] w-full max-w-3xl overflow-y-auto rounded-t-2xl border border-slate-200/90 bg-white p-5 text-slate-800 shadow-2xl sm:rounded-2xl sm:p-6" onClick={event => event.stopPropagation()}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">Hành trình xử lý phiếu</p>
          <h2 id="case-dialog-title" className="mt-1 flex flex-wrap items-center gap-2 text-xl font-bold text-slate-900">
            <span className="font-mono">{detail?.reference_code ?? 'Đang tải…'}</span>
            {detail && <CaseTypeBadge type={detail.case_type} />}
          </h2>
          {detail?.title && <p className="mt-1 text-sm text-slate-600">{detail.title}</p>}
        </div>
        <button onClick={onClose} aria-label="Đóng" className="rounded-xl border border-slate-200 p-2 text-slate-400 hover:text-slate-600"><X className="h-4 w-4" /></button>
      </div>
      {loading ? <div className="mt-5"><LoadingPanel /></div> : error ? <div role="alert" className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</div> : detail ? <div className="mt-5 space-y-6">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <DetailMetric label="Ngày tạo phiếu" value={formatDate(createdAt)} />
          <DetailMetric label="Tổng thời gian xử lý" value={detail.processing_time === null ? 'Chưa hoàn tất' : formatDuration(detail.processing_time)} />
          <DetailMetric label="Thời gian đến khi được xử lý" value={formatDuration(detail.first_action_time)} />
          <DetailMetric label="Số lần bị mở lại" value={detail.rework_events > 0 ? `${detail.rework_events} lần` : 'Không có'} hint="Phiếu đã khắc phục nhưng phải xử lý lại" />
          <DetailMetric label="Tuân thủ quy trình" value={detail.case_type === 'INCIDENT' ? conformanceLabel : 'Không áp dụng'} hint="So với các bước chuyển trạng thái hợp lệ của phiếu sự cố" />
          <DetailMetric label="Số bước đã ghi nhận" value={formatCount(detail.events.length)} />
        </div>

        <div>
          <h3 className="mb-3 text-sm font-bold text-slate-900">Các bước đã diễn ra</h3>
          {detail.events.length ? <ol>{detail.events.map((event, index) => <TimelineItem key={event.id} event={event} isLast={index === detail.events.length - 1} />)}</ol> : <EmptyState>Phiếu này chưa có bước nào được ghi nhận.</EmptyState>}
        </div>

        {conformance?.deviations.length ? <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <h3 className="text-sm font-bold text-amber-900">Bước không đúng quy trình chuẩn</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-800">{conformance.deviations.map(deviation => <li key={deviation.event_id}>Chuyển từ &quot;{statusLabel(deviation.from_status)}&quot; sang &quot;{statusLabel(deviation.to_status)}&quot; không nằm trong các bước chuyển được phép.</li>)}</ul>
        </div> : null}
      </div> : <EmptyState>Không có dữ liệu phiếu.</EmptyState>}
    </section>
  </div>;
}

function TimelineItem({ event, isLast }: { event: ProcessMiningEvent; isLast: boolean }) {
  const hasStatusChange = event.from_status !== null || event.to_status !== null;
  // The same code (IN_PROGRESS, CANCELLED) means different things for incidents and maintenance
  const label = (code: string | null) => (event.event_type.startsWith('MAINTENANCE_') ? maintenanceStatusLabel(code) : statusLabel(code));
  return <li className="relative flex gap-3 pb-4 last:pb-0">
    <div className="flex w-5 shrink-0 flex-col items-center"><span className="mt-1 h-3 w-3 rounded-full border-2 border-indigo-600 bg-white" />{!isLast && <span className="mt-1 w-px flex-1 bg-slate-200" />}</div>
    <article className="min-w-0 flex-1 rounded-2xl border border-slate-200 bg-slate-50 p-3.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-semibold text-slate-900">{eventLabel(event.event_type)}</span>
        <span className="text-xs text-slate-500">{formatDate(event.occurred_at)}</span>
      </div>
      {hasStatusChange && <p className="mt-1.5 text-sm text-slate-700">
        {event.from_status ? <>{label(event.from_status)} <span className="mx-1 text-slate-400">→</span> </> : 'Trạng thái: '}
        <strong>{label(event.to_status)}</strong>
      </p>}
      {(event.performed_by_name || event.target_user_name) && <p className="mt-1.5 text-xs text-slate-500">
        {event.performed_by_name && <>Người thực hiện: <span className="font-medium text-slate-700">{event.performed_by_name}</span></>}
        {event.performed_by_name && event.target_user_name && ' · '}
        {event.target_user_name && <>Giao cho: <span className="font-medium text-slate-700">{event.target_user_name}</span></>}
      </p>}
      {(event.source === 'BACKFILL' || event.timestamp_quality !== 'ACTION_TIME') && <div className="mt-2 flex flex-wrap gap-1.5">
        {event.source === 'BACKFILL' && <NoteBadge title="Bước này được tạo lại từ dữ liệu cũ, không ghi trực tiếp lúc thao tác.">{SOURCE_LABELS.BACKFILL}</NoteBadge>}
        {event.timestamp_quality !== 'ACTION_TIME' && <NoteBadge title="Thời điểm của bước này không được ghi chính xác.">Thời gian ước lượng</NoteBadge>}
      </div>}
    </article>
  </li>;
}

function SectionHeading({ id, icon, title, description }: { id: string; icon: ReactNode; title: string; description?: string }) {
  return <div>
    <h2 id={id} className="flex items-center gap-2 text-lg font-bold text-slate-900">{icon}{title}</h2>
    {description && <p className="mt-1 max-w-3xl text-sm text-slate-500">{description}</p>}
  </div>;
}

function Metric({ title, value, hint, tone = 'slate' }: { title: string; value: string; hint?: string; tone?: 'slate' | 'emerald' | 'amber' }) {
  const styles = { slate: 'text-slate-900', emerald: 'text-emerald-700', amber: 'text-amber-700' };
  return <article className="rounded-2xl border border-slate-200/90 bg-white p-4 shadow-sm">
    <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</p>
    <p className={`mt-2 text-2xl font-bold tabular-nums ${styles[tone]}`}>{value}</p>
    {hint && <p className="mt-1 text-xs leading-relaxed text-slate-500">{hint}</p>}
  </article>;
}

function DetailMetric({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return <div className="rounded-xl border border-slate-200 bg-slate-50 p-3" title={hint}>
    <p className="text-xs font-medium text-slate-500">{label}</p>
    <p className="mt-1 break-words text-sm font-semibold text-slate-900">{value}</p>
  </div>;
}

function QualityGroup({ title, children }: { title: string; children: ReactNode }) {
  return <div><h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">{title}</h3>{children}</div>;
}

function QualityRow({ label, value }: { label: string; value: string }) {
  return <p className="mb-1 flex justify-between gap-3 text-sm font-medium text-slate-600"><span>{label}</span><span className="tabular-nums font-bold text-slate-900">{value}</span></p>;
}

function CaseTypeBadge({ type }: { type: ProcessCaseType }) {
  const style = type === 'INCIDENT' ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-sky-200 bg-sky-50 text-sky-700';
  return <span className={`inline-flex whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold ${style}`}>{CASE_TYPE_LABELS[type] ?? 'Khác'}</span>;
}

function NoteBadge({ title, children }: { title: string; children: ReactNode }) {
  return <span title={title} className="inline-flex rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-800">{children}</span>;
}

function CompletionBadge({ completed }: { completed: boolean }) {
  return <span className={`inline-flex whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold ${completed ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-amber-200 bg-amber-50 text-amber-800'}`}>{completed ? 'Hoàn tất' : 'Chưa hoàn tất'}</span>;
}

function LoadingGrid({ count }: { count: number }) {
  return <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-label="Đang tải dữ liệu">{Array.from({ length: count }, (_, index) => <div key={index} className="h-28 animate-pulse rounded-2xl border border-slate-200 bg-white shadow-sm" />)}</div>;
}

function LoadingPanel() {
  return <div className="h-28 animate-pulse rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-400 shadow-sm">Đang tải dữ liệu…</div>;
}

function EmptyState({ children }: { children: ReactNode }) {
  return <div className="rounded-2xl border border-dashed border-slate-200 bg-white px-4 py-8 text-center text-sm text-slate-400 shadow-sm">{children}</div>;
}

const inputClass = 'rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none transition-all focus:border-indigo-500 focus:bg-white';

export default function ProcessMiningPage() {
  return <ProcessMiningContent />;
}
