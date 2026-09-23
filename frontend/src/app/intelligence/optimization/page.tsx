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
  const field = (label: string, name: string, type = 'number', required = true, step?: string) => <label className="grid gap-1 text-sm text-slate-300">{label}<input name={name} type={type} step={step} required={required} min={type === 'number' ? '0' : undefined} className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white" /></label>;
  const form = (children: React.ReactNode, action: (data: FormData) => Promise<void>, noValidate = false) => <form noValidate={noValidate} onSubmit={e => run(e, action)} className="grid gap-4 rounded-xl border border-slate-700 bg-slate-800 p-5 md:grid-cols-2">{children}<button disabled={busy} className="rounded-lg bg-sky-600 px-4 py-2 font-semibold text-white disabled:opacity-50 md:col-span-2">{busy ? 'Đang tính…' : 'Simulate'}</button></form>;

  return <ProtectedRoute><Navbar /><main className="mx-auto max-w-6xl space-y-6 px-4 py-8 text-white">
    <div><h1 className="text-2xl font-bold">What-if & Optimization</h1><p className="mt-1 text-sm text-slate-400">Mô phỏng và đề xuất chỉ đọc; kết quả không tự cập nhật dữ liệu.</p></div>
    {!isAllowed ? <p className="rounded-lg border border-amber-500/40 p-4 text-amber-300">Khu vực này chỉ dành cho ADMIN, IT Asset Manager và Manager.</p> : <>
      <nav className="flex flex-wrap gap-2">{tabs.map(([id, label]) => <button key={id} onClick={() => setTab(id)} className={`rounded-lg px-3 py-2 text-sm ${tab === id ? 'bg-sky-600' : 'bg-slate-800 text-slate-300'}`}>{label}</button>)}</nav>
      {error && <div role="alert" className="rounded-lg border border-rose-500/40 bg-rose-950/30 p-3 text-rose-300">{error}</div>}
      {tab === 'allocation' && <>{form(<>
        <label className="grid gap-1 text-sm text-slate-300">Phòng ban<select name="department_id" required className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2">{departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</select></label>
        {field('Danh mục tài sản', 'asset_category', 'text')}{field('Số lượng cần', 'requested_quantity')}
      </>, async d => setAllocation(await simulateAllocation({ department_id: Number(d.get('department_id')), asset_category: String(d.get('asset_category')), requested_quantity: Number(d.get('requested_quantity')) })))}
      {allocation && <Result><h2 className="font-semibold">{allocation.enough ? 'Đủ tài sản' : 'Chưa đủ tài sản'}</h2><p>Có sẵn {allocation.available_quantity}; cần {allocation.requested_quantity}; thiếu {allocation.shortage_quantity}.</p><ul>{allocation.candidates.map(a => <li key={a.asset_id}>{a.asset_code} · {a.name} · {a.brand} {a.model}</li>)}</ul><p className="text-amber-300">Ứng viên chỉ là đề xuất và chưa được cấp phát.</p><Notes items={[...allocation.assumptions, ...allocation.warnings]} /></Result>}</>}
      {tab === 'priority' && <Result>{recommendations?.items.length ? recommendations.items.map(a => <article key={a.asset_id} className="border-b border-slate-700 py-3"><b>{a.name} ({a.asset_code})</b> — {a.priority_level}, score {a.replacement_recommendation_score}/100<p className="text-sm text-slate-300">Risk {a.risk_score}; repair {a.repair_cost.toLocaleString('vi-VN')} VND; incidents {a.incident_count}; maintenance {a.maintenance_count}; age {a.age_years ?? 'N/A'} years</p><ul className="text-sm text-slate-400">{a.reasons.map(r => <li key={r}>• {r}</li>)}</ul></article>) : <p>{recommendations ? 'Chưa có tài sản.' : 'Đang tải…'}</p>}<p className="mt-3 text-xs text-slate-400">Điểm ưu tiên là heuristic, không bảo đảm tối ưu và không dự báo tiết kiệm tài chính.</p></Result>}
      {tab === 'capacity' && <>{form(<>{field('SLA hiện tại (ngày)', 'current_sla_days', 'number', true, 'any')}{field('SLA mục tiêu (ngày)', 'target_sla_days', 'number', true, 'any')}{field('Số incident dự kiến', 'expected_incidents')}{field('Incident / kỹ thuật viên / ngày', 'incidents_per_technician_per_day', 'number', true, 'any')}{field('Số kỹ thuật viên hiện tại (tùy chọn)', 'current_technician_count', 'number', false)}</>, async d => setCapacity(await simulateCapacity({ current_sla_days: Number(d.get('current_sla_days')), target_sla_days: Number(d.get('target_sla_days')), expected_incidents: Number(d.get('expected_incidents')), incidents_per_technician_per_day: Number(d.get('incidents_per_technician_per_day')), ...(d.get('current_technician_count') ? { current_technician_count: Number(d.get('current_technician_count')) } : {}) })))}{capacity && <Result><p>Ước tính cần {capacity.estimated_required_technicians} kỹ thuật viên; chênh lệch {capacity.estimated_gap ?? 'N/A'}.</p><Notes items={[...capacity.assumptions, ...capacity.warnings]} /></Result>}</>}
      {tab === 'depreciation' && <>{form(<>
        {field('Số lượng', 'quantity')}
        {field('Giá mỗi tài sản (VND)', 'unit_cost', 'number', true, 'any')}
        {field('Thời gian sử dụng (năm)', 'useful_life_years', 'number', true, 'any')}
        {field('Thời gian mô phỏng (năm)', 'simulation_horizon_years')}
        <fieldset className="grid gap-2 text-sm text-slate-300 md:col-span-2">
          <legend className="mb-1">Giá trị còn lại — chọn một</legend>
          <p className="text-xs text-slate-400">Chỉ sử dụng một trong hai cách.</p>
          <label className="flex items-center gap-2"><input type="radio" name="residual_value_mode" value="fixed" required checked={residualValueMode === 'fixed'} onChange={() => setResidualValueMode('fixed')} />Giá trị cố định</label>
          <label className="flex items-center gap-2"><input type="radio" name="residual_value_mode" value="rate" required checked={residualValueMode === 'rate'} onChange={() => setResidualValueMode('rate')} />Tỷ lệ giá trị còn lại</label>
          {residualValueMode === 'fixed' && <label className="grid gap-1">Giá trị còn lại (VND)<input name="residual_value" type="number" min="0" step="any" required className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white" /></label>}
          {residualValueMode === 'rate' && <label className="grid gap-1">Tỷ lệ giá trị còn lại (0–1)<input name="residual_value_rate" type="number" min="0" max="1" step="any" required className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white" /></label>}
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
      }, true)}{simulation && <Result><p>Tổng chi phí: {simulation.total_initial_cost.toLocaleString('vi-VN')} VND · Khấu hao năm: {simulation.annual_depreciation.toLocaleString('vi-VN')} VND · Giá trị còn lại: {simulation.residual_value.toLocaleString('vi-VN')} VND</p><ul>{simulation.estimated_book_value_by_year.map(y => <li key={y.year}>Năm {y.year} — Khấu hao: {y.depreciation_expense.toLocaleString('vi-VN')} VND · Giá trị sổ sách cuối năm: {y.estimated_book_value.toLocaleString('vi-VN')} VND</li>)}</ul><Notes items={[...simulation.assumptions, ...simulation.warnings]} /></Result>}</>}
    </>}
  </main></ProtectedRoute>;
}
function Result({ children }: { children: React.ReactNode }) { return <section className="mt-4 space-y-2 rounded-xl border border-slate-700 bg-slate-900 p-5 text-sm text-slate-200">{children}</section>; }
function Notes({ items }: { items: string[] }) { return <ul className="mt-2 text-xs text-slate-400">{items.map(x => <li key={x}>• {x}</li>)}</ul>; }
export default function OptimizationPage() { return <OptimizationContent />; }
