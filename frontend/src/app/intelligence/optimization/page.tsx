'use client';

import { FormEvent, useEffect, useState } from 'react';
import { Navbar } from '@/components/Navbar';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { fetchApi, getReplacementRecommendations, simulateAllocation, simulateCapacity, simulateReplacement } from '@/lib/api';
import type { AllocationResponse, CapacityResponse, ReplacementRecommendationsResponse, ReplacementSimulationResponse } from '@/types/optimization';
import { useAuth } from '@/lib/auth-context';

type Tab = 'allocation' | 'priority' | 'capacity' | 'depreciation';
type ResidualValueMode = '' | 'fixed' | 'rate';
type Department = { id: number; name: string; code: string };

function OptimizationContent() {
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>('allocation');
  const [departments, setDepartments] = useState<Department[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [allocation, setAllocation] = useState<AllocationResponse | null>(null);
  const [capacity, setCapacity] = useState<CapacityResponse | null>(null);
  const [simulation, setSimulation] = useState<ReplacementSimulationResponse | null>(null);
  const [residualValueMode, setResidualValueMode] = useState<ResidualValueMode>('');
  const [recommendations, setRecommendations] = useState<ReplacementRecommendationsResponse | null>(null);

  useEffect(() => { fetchApi<Department[]>('/departments').then(setDepartments).catch(e => setError(e.message)); }, []);
  useEffect(() => {
    if (tab === 'priority') getReplacementRecommendations().then(setRecommendations).catch(e => setError(e.message));
  }, [tab]);
  const run = async (event: FormEvent<HTMLFormElement>, action: (data: FormData) => Promise<void>) => {
    event.preventDefault(); setBusy(true); setError('');
    try { await action(new FormData(event.currentTarget)); } catch (e) { setError(e instanceof Error ? e.message : 'Không thể chạy mô phỏng.'); }
    finally { setBusy(false); }
  };
  const isAllowed = user && ['ADMIN', 'IT_ASSET_MANAGER', 'MANAGER'].includes(user.role);
  const tabs: [Tab, string][] = [['allocation', 'Phân bổ tài sản'], ['priority', 'Ưu tiên thay thế'], ['capacity', 'Năng lực kỹ thuật viên'], ['depreciation', 'Mô phỏng khấu hao']];
  const field = (label: string, name: string, type = 'number', required = true, step?: string) => <label className="grid gap-1 text-sm font-medium text-slate-700">{label}<input name={name} type={type} step={step} required={required} min={type === 'number' ? '0' : undefined} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-900 focus:bg-white focus:border-indigo-500 outline-none transition-all" /></label>;
  const form = (children: React.ReactNode, action: (data: FormData) => Promise<void>, noValidate = false) => <form noValidate={noValidate} onSubmit={e => run(e, action)} className="grid gap-4 rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm md:grid-cols-2">{children}<button disabled={busy} className="rounded-xl bg-indigo-600 hover:bg-indigo-700 px-4 py-2.5 font-semibold text-white transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50 md:col-span-2">{busy ? 'Đang tính…' : 'Simulate'}</button></form>;

  return <ProtectedRoute><div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col"><Navbar /><main className="mx-auto max-w-6xl w-full space-y-6 px-4 py-8 text-slate-800">
    <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm"><h1 className="text-2xl font-bold text-slate-900 tracking-tight">What-if & Optimization</h1><p className="mt-1 text-sm text-slate-500">Mô phỏng và đề xuất chỉ đọc; kết quả không tự cập nhật dữ liệu.</p></div>
    {!isAllowed ? <p className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-800 shadow-sm font-medium">Khu vực này chỉ dành cho ADMIN, IT Asset Manager và Manager.</p> : <>
      <nav className="flex flex-wrap gap-2">{tabs.map(([id, label]) => <button key={id} onClick={() => setTab(id)} className={`rounded-xl px-4 py-2 text-xs font-semibold transition-all ${tab === id ? 'bg-indigo-600 text-white shadow-sm' : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 shadow-sm'}`}>{label}</button>)}</nav>
      {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800 font-medium shadow-sm">{error}</div>}
      {tab === 'allocation' && <>{form(<>
        <label className="grid gap-1 text-sm font-medium text-slate-700">Phòng ban<select name="department_id" required className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-900 focus:bg-white focus:border-indigo-500 outline-none transition-all">{departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</select></label>
        {field('Danh mục tài sản', 'asset_category', 'text')}{field('Số lượng cần', 'requested_quantity')}
      </>, async d => setAllocation(await simulateAllocation({ department_id: Number(d.get('department_id')), asset_category: String(d.get('asset_category')), requested_quantity: Number(d.get('requested_quantity')) })))}
      {allocation && <Result><h2 className="font-semibold text-slate-900 text-base">{allocation.enough ? 'Đủ tài sản' : 'Chưa đủ tài sản'}</h2><p className="text-slate-700">Có sẵn <strong className="text-indigo-600">{allocation.available_quantity}</strong>; cần <strong className="text-slate-900">{allocation.requested_quantity}</strong>; thiếu <strong className="text-rose-600">{allocation.shortage_quantity}</strong>.</p><ul className="space-y-1 font-mono text-xs text-slate-700">{allocation.candidates.map(a => <li key={a.asset_id}>• {a.asset_code} · {a.name} · {a.brand} {a.model}</li>)}</ul><p className="text-amber-800 text-xs font-medium">Ứng viên chỉ là đề xuất và chưa được cấp phát.</p><Notes items={[...allocation.assumptions, ...allocation.warnings]} /></Result>}</>}
      {tab === 'priority' && <Result>{recommendations?.items.length ? recommendations.items.map(a => <article key={a.asset_id} className="border-b border-slate-100 py-3 space-y-1"><b className="text-slate-900">{a.name} ({a.asset_code})</b> — <span className="px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 font-semibold text-xs border border-indigo-200">{a.priority_level}</span>, score <strong className="text-indigo-600">{a.replacement_recommendation_score}/100</strong><p className="text-xs text-slate-600">Risk {a.risk_score}; repair {a.repair_cost.toLocaleString('vi-VN')} VND; incidents {a.incident_count}; maintenance {a.maintenance_count}; age {a.age_years ?? 'N/A'} years</p><ul className="text-xs text-slate-500">{a.reasons.map(r => <li key={r}>• {r}</li>)}</ul></article>) : <p className="text-slate-500">{recommendations ? 'Chưa có tài sản.' : 'Đang tải…'}</p>}<p className="mt-3 text-xs text-slate-400 italic">Điểm ưu tiên là heuristic, không bảo đảm tối ưu và không dự báo tiết kiệm tài chính.</p></Result>}
      {tab === 'capacity' && <>{form(<>{field('SLA hiện tại (ngày)', 'current_sla_days', 'number', true, 'any')}{field('SLA mục tiêu (ngày)', 'target_sla_days', 'number', true, 'any')}{field('Số incident dự kiến', 'expected_incidents')}{field('Incident / kỹ thuật viên / ngày', 'incidents_per_technician_per_day', 'number', true, 'any')}{field('Số kỹ thuật viên hiện tại (tùy chọn)', 'current_technician_count', 'number', false)}</>, async d => setCapacity(await simulateCapacity({ current_sla_days: Number(d.get('current_sla_days')), target_sla_days: Number(d.get('target_sla_days')), expected_incidents: Number(d.get('expected_incidents')), incidents_per_technician_per_day: Number(d.get('incidents_per_technician_per_day')), ...(d.get('current_technician_count') ? { current_technician_count: Number(d.get('current_technician_count')) } : {}) })))}{capacity && <Result><p className="font-semibold text-slate-900">Ước tính cần <span className="text-indigo-600">{capacity.estimated_required_technicians}</span> kỹ thuật viên; chênh lệch <span className="text-amber-700">{capacity.estimated_gap ?? 'N/A'}</span>.</p><Notes items={[...capacity.assumptions, ...capacity.warnings]} /></Result>}</>}
      {tab === 'depreciation' && <>{form(<>
        {field('Số lượng', 'quantity')}
        {field('Giá mỗi tài sản (VND)', 'unit_cost', 'number', true, 'any')}
        {field('Thời gian sử dụng (năm)', 'useful_life_years', 'number', true, 'any')}
        {field('Thời gian mô phỏng (năm)', 'simulation_horizon_years')}
        <fieldset className="grid gap-2 text-sm font-medium text-slate-700 md:col-span-2">
          <legend className="mb-1 font-semibold text-slate-900">Giá trị còn lại — chọn một</legend>
          <p className="text-xs text-slate-500 font-normal">Chỉ sử dụng một trong hai cách.</p>
          <label className="flex items-center gap-2 font-normal text-slate-800"><input type="radio" name="residual_value_mode" value="fixed" required checked={residualValueMode === 'fixed'} onChange={() => setResidualValueMode('fixed')} />Giá trị cố định</label>
          <label className="flex items-center gap-2 font-normal text-slate-800"><input type="radio" name="residual_value_mode" value="rate" required checked={residualValueMode === 'rate'} onChange={() => setResidualValueMode('rate')} />Tỷ lệ giá trị còn lại</label>
          {residualValueMode === 'fixed' && <label className="grid gap-1 font-normal text-slate-700">Giá trị còn lại (VND)<input name="residual_value" type="number" min="0" step="any" required className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-900 focus:bg-white focus:border-indigo-500 outline-none" /></label>}
          {residualValueMode === 'rate' && <label className="grid gap-1 font-normal text-slate-700">Tỷ lệ giá trị còn lại (0–1)<input name="residual_value_rate" type="number" min="0" max="1" step="any" required className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-900 focus:bg-white focus:border-indigo-500 outline-none" /></label>}
        </fieldset>
      </>, async d => {
        const quantity = Number(d.get('quantity'));
        const unitCost = Number(d.get('unit_cost'));
        const usefulLife = Number(d.get('useful_life_years'));
        const horizon = Number(d.get('simulation_horizon_years'));
        const residualValue = d.get('residual_value');
        const residualRate = d.get('residual_value_rate');
        const mode = d.get('residual_value_mode');

        if (!String(d.get('unit_cost') ?? '').trim()) throw new Error('Hãy nhập giá mỗi tài sản.');
        if (!Number.isInteger(quantity) || quantity <= 0 || quantity > 1_000_000) throw new Error('Số lượng phải là số nguyên từ 1 đến 1.000.000.');
        if (!Number.isFinite(unitCost) || unitCost < 0 || unitCost > 1e15) throw new Error('Giá mỗi tài sản phải từ 0 đến 1.000.000.000.000.000 VND.');
        if (!Number.isFinite(usefulLife) || usefulLife <= 0 || usefulLife > 1000) throw new Error('Thời gian sử dụng phải lớn hơn 0 và không vượt quá 1.000 năm.');
        if (!Number.isInteger(horizon) || horizon <= 0 || horizon > 1000) throw new Error('Thời gian mô phỏng phải là số năm nguyên từ 1 đến 1.000.');
        if (mode === 'fixed') {
          const value = Number(residualValue);
          if (residualValue === null || !String(residualValue).trim() || !Number.isFinite(value) || value < 0 || value > 1e15) throw new Error('Giá trị còn lại phải nằm trong khoảng 0 đến 1.000.000.000.000.000 VND.');
          if (value > unitCost) throw new Error('Giá trị còn lại không được lớn hơn giá mỗi tài sản.');
        } else if (mode === 'rate') {
          const rate = Number(residualRate);
          if (residualRate === null || !String(residualRate).trim() || !Number.isFinite(rate) || rate < 0 || rate > 1) throw new Error('Tỷ lệ giá trị còn lại phải nằm trong khoảng 0 đến 1.');
        } else {
          throw new Error('Hãy chọn giá trị cố định hoặc tỷ lệ giá trị còn lại.');
        }

        const result = await simulateReplacement({
          quantity, unit_cost: unitCost, useful_life_years: usefulLife,
          simulation_horizon_years: horizon,
          ...(mode === 'fixed' ? { residual_value: Number(residualValue) } : {}),
          ...(mode === 'rate' ? { residual_value_rate: Number(residualRate) } : {}),
        });
        setSimulation(result);
      }, true)}{simulation && <Result><p className="font-semibold text-slate-900">Tổng chi phí: <span className="text-indigo-600">{simulation.total_initial_cost.toLocaleString('vi-VN')} VND</span> · Khấu hao năm: <span className="text-amber-700">{simulation.annual_depreciation.toLocaleString('vi-VN')} VND</span> · Giá trị còn lại: <span className="text-emerald-600">{simulation.residual_value.toLocaleString('vi-VN')} VND</span></p><ul className="space-y-1 text-xs text-slate-700">{simulation.estimated_book_value_by_year.map(y => <li key={y.year}>Năm {y.year} — Khấu hao: {y.depreciation_expense.toLocaleString('vi-VN')} VND · Giá trị sổ sách cuối năm: <strong>{y.estimated_book_value.toLocaleString('vi-VN')} VND</strong></li>)}</ul><Notes items={[...simulation.assumptions, ...simulation.warnings]} /></Result>}</>}
    </>}
  </main></div></ProtectedRoute>;
}
function Result({ children }: { children: React.ReactNode }) { return <section className="mt-4 space-y-2 rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm text-sm text-slate-800">{children}</section>; }
function Notes({ items }: { items: string[] }) { return <ul className="mt-2 text-xs text-slate-500 space-y-0.5">{items.map(x => <li key={x}>• {x}</li>)}</ul>; }
export default function OptimizationPage() { return <OptimizationContent />; }
