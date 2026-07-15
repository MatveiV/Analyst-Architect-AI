import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  listBuildProjects, createBuildProject, estimateProjectTasks,
  createEconomicEstimate, addEconomicActual, getProjectReport,
  exportBusinessCase, exportBusinessCasePdf, listDocuments,
} from '../api';
import {
  SectionHeader, EmptyState, Spinner, NeedsReviewBadge, Tabs, toast,
} from '../components/ui';
import { useI18n } from '../i18n';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, Legend, ResponsiveContainer,
} from 'recharts';

interface Doc { id: string; title: string; doc_type: string; }
interface Project {
  id: string; document_id: string; name: string; description: string;
  status: string; created_at: string;
}

const STATUS_META: Record<string, { icon: string; color: string }> = {
  draft:       { icon: '📝', color: 'text-slate-muted bg-ink-muted border-slate-border' },
  estimated:   { icon: '📊', color: 'text-blue-400 bg-blue-500/10 border-blue-500/30' },
  approved:    { icon: '✅', color: 'text-green-400 bg-ok-bg border-green-500/30' },
  in_progress: { icon: '⚙️', color: 'text-yellow-400 bg-warn-bg border-yellow-500/30' },
  delivered:   { icon: '🚀', color: 'text-purple-400 bg-purple-500/10 border-purple-500/30' },
};

function money(n: number) {
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(n) + ' ₽';
}

/* ── Client-side economic formulas (mirrors backend economics_service.py) ──── */
const RATE_FIELDS: Record<string, string> = {
  backend: 'rate_backend', frontend: 'rate_frontend', qa: 'rate_qa',
  devops: 'rate_devops', analyst: 'rate_analyst',
};
function clientComputePreview(rates: typeof RATES_DEFAULTS, hoursByRole?: Record<string, number>) {
  if (!hoursByRole || Object.keys(hoursByRole).length === 0) return null;
  const capex = Object.entries(hoursByRole).reduce((sum, [role, hours]) => {
    const rf = RATE_FIELDS[role] || 'rate_analyst';
    return sum + hours * (rates as any)[rf];
  }, 0);
  const opexMonthly = rates.hosting_cost_monthly + rates.llm_cost_monthly
    + rates.support_hours_monthly * rates.rate_backend;
  const benefitMonthly = rates.time_saved_hours_monthly * rates.avg_employee_rate;
  const netMonthly = benefitMonthly - opexMonthly;
  const payback = netMonthly > 0 ? capex / netMonthly : -1;
  const roi = capex > 0 ? ((netMonthly * 12 - capex) / capex * 100) : 0;
  return { capex, opexMonthly, benefitMonthly, netMonthly, payback, roi };
}

/* ── Chart data for break-even analysis ─────────────────────────────────── */
function buildChartData(eco: any) {
  const m: any[] = [];
  let cumCost = eco.capex;
  let cumBenefit = 0;
  for (let i = 1; i <= 12; i++) {
    cumCost += eco.opexMonthly;
    cumBenefit += eco.benefitMonthly;
    m.push({
      month: `${i}`,
      'Cum. Cost': Math.round(cumCost),
      'Cum. Benefit': Math.round(cumBenefit),
      'Break-even': cumBenefit >= cumCost ? Math.round(cumBenefit) : null,
    });
  }
  return m;
}

const RATES_DEFAULTS = {
  rate_backend: 2500, rate_frontend: 2200, rate_qa: 1800,
  rate_devops: 2800, rate_analyst: 2500,
  hosting_cost_monthly: 5000, llm_cost_monthly: 3000, support_hours_monthly: 8,
  time_saved_hours_monthly: 100, avg_employee_rate: 2500,
};

export default function EconomicsPage() {
  const { lang } = useI18n();
  const [projects, setProjects] = useState<Project[]>([]);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Project | null>(null);
  const [report, setReport] = useState<any>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ document_id: '', name: '', description: '' });
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [tab, setTab] = useState('estimate');

  const [rates, setRates] = useState({ ...RATES_DEFAULTS });
  const [preview, setPreview] = useState<{ capex: number; opexMonthly: number; benefitMonthly: number; netMonthly: number; payback: number; roi: number } | null>(null);
  const [chartData, setChartData] = useState<any[]>([]);
  const [hoursByRole, setHoursByRole] = useState<Record<string, number> | null>(null);

  // Live preview: recompute whenever rates or hoursByRole changes
  useEffect(() => {
    const pv = clientComputePreview(rates, hoursByRole || undefined);
    setPreview(pv);
  }, [rates, hoursByRole]);
  const [actualForm, setActualForm] = useState({
    actual_capex: 0, actual_opex_monthly: 0, actual_benefit_monthly: 0,
    actual_time_saved_hours_monthly: 0, notes: '',
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [pRes, dRes] = await Promise.all([listBuildProjects(), listDocuments()]);
      setProjects(pRes.data);
      setDocs(dRes.data.filter((d: Doc) => d.doc_type !== 'kb_article'));
    } catch { toast(lang === 'ru' ? 'Ошибка загрузки' : 'Load error', 'error'); }
    finally { setLoading(false); }
  }, [lang]);

  useEffect(() => { load(); }, [load]);

  const selectProject = useCallback(async (p: Project) => {
    setSelected(p);
    setReport(null);
    setPreview(null);
    setChartData([]);
    try {
      const r = await getProjectReport(p.id);
      setReport(r.data);
      if (r.data.latest_economic_estimate) {
        const e = r.data.latest_economic_estimate;
        setActualForm({
          actual_capex: e.capex, actual_opex_monthly: e.opex_monthly,
          actual_benefit_monthly: e.benefit_monthly, actual_time_saved_hours_monthly: 0, notes: '',
        });
        setChartData(buildChartData(e));
      }
      // Restore rates from the saved estimate for live preview
      if (r.data.latest_economic_estimate) {
        const e = r.data.latest_economic_estimate;
        setRates({
          rate_backend: e.rate_backend, rate_frontend: e.rate_frontend,
          rate_qa: e.rate_qa, rate_devops: e.rate_devops, rate_analyst: e.rate_analyst,
          hosting_cost_monthly: e.hosting_cost_monthly, llm_cost_monthly: e.llm_cost_monthly,
          support_hours_monthly: e.support_hours_monthly,
          time_saved_hours_monthly: e.time_saved_hours_monthly, avg_employee_rate: e.avg_employee_rate,
        });
      }
      // Compute preview from task estimate hours
      if (r.data.latest_task_estimate) {
        try {
          const tj = JSON.parse(r.data.latest_task_estimate.tasks_json);
          setHoursByRole(tj.total_hours_by_role || null);
        } catch {}
      }
    } catch { toast(lang === 'ru' ? 'Ошибка загрузки отчёта' : 'Report load error', 'error'); }
  }, [lang]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.document_id || !form.name.trim()) return;
    setCreating(true);
    try {
      await createBuildProject(form);
      toast(lang === 'ru' ? 'Проект создан' : 'Project created', 'success');
      setShowForm(false); setForm({ document_id: '', name: '', description: '' });
      load();
    } catch (err: any) { toast(err?.response?.data?.detail || 'Error', 'error'); }
    finally { setCreating(false); }
  };

  const handleEstimateTasks = async () => {
    if (!selected) return;
    setBusy('tasks');
    try {
      await estimateProjectTasks(selected.id);
      toast(lang === 'ru' ? 'Декомпозиция готова' : 'Decomposition ready', 'success');
      const r = await getProjectReport(selected.id);
      setReport(r.data);
      if (r.data.latest_task_estimate) {
        try {
          const tj = JSON.parse(r.data.latest_task_estimate.tasks_json);
          setHoursByRole(tj.total_hours_by_role || null);
        } catch {}
      }
      load();
    } catch { toast(lang === 'ru' ? 'Ошибка декомпозиции' : 'Decomposition error', 'error'); }
    finally { setBusy(null); }
  };

  const handleCalcEconomics = async () => {
    if (!selected) return;
    setBusy('economics');
    try {
      const res = await createEconomicEstimate(selected.id, rates);
      toast(lang === 'ru' ? 'Экономика рассчитана' : 'Economics calculated', 'success');
      const r = await getProjectReport(selected.id);
      setReport(r.data);
      setActualForm(p => ({
        ...p, actual_capex: res.data.capex, actual_opex_monthly: res.data.opex_monthly,
        actual_benefit_monthly: res.data.benefit_monthly,
      }));
      setChartData(buildChartData(res.data));
      load();
    } catch (err: any) {
      toast(err?.response?.data?.detail || (lang === 'ru' ? 'Сначала запустите декомпозицию задач' : 'Run task estimation first'), 'error');
    } finally { setBusy(null); }
  };

  const handleAddActual = async () => {
    if (!selected) return;
    setBusy('actual');
    try {
      await addEconomicActual(selected.id, actualForm);
      toast(lang === 'ru' ? 'Факт сохранён' : 'Actuals saved', 'success');
      const r = await getProjectReport(selected.id);
      setReport(r.data);
      load();
    } catch { toast(lang === 'ru' ? 'Ошибка сохранения' : 'Save error', 'error'); }
    finally { setBusy(null); }
  };

  const handleExport = async (fmt: 'docx' | 'pdf') => {
    if (!selected) return;
    try {
      const fn = fmt === 'pdf' ? exportBusinessCasePdf : exportBusinessCase;
      const res = await fn(selected.id);
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a'); a.href = url;
      a.download = `business_case_${selected.name.slice(0, 30)}.${fmt}`; a.click();
      URL.revokeObjectURL(url);
    } catch { toast(lang === 'ru' ? 'Ошибка экспорта' : 'Export error', 'error'); }
  };

  const TABS = [
    { key: 'estimate', label: lang === 'ru' ? '📊 Оценка задач' : '📊 Task Estimate' },
    { key: 'economics', label: lang === 'ru' ? '💰 Экономика' : '💰 Economics' },
    { key: 'actuals', label: lang === 'ru' ? '📈 План/Факт' : '📈 Plan/Actual' },
  ];

  return (
    <div>
      <SectionHeader
        title={lang === 'ru' ? 'Экономика проектов' : 'Project Economics'}
        subtitle={lang === 'ru'
          ? 'ROI, срок окупаемости и бизнес-кейс для приложений, создаваемых через платформу'
          : 'ROI, payback period, and business case for apps built through the platform'}
        action={
          <button className="btn-primary" onClick={() => setShowForm(v => !v)}>
            {showForm ? '✕' : `+ ${lang === 'ru' ? 'Новый проект' : 'New Project'}`}
          </button>
        }
      />

      {showForm && (
        <form onSubmit={handleCreate} className="card border-accent/30 mb-6 space-y-4 animate-fade-in">
          <p className="font-display font-bold">{lang === 'ru' ? 'Новый build-проект' : 'New Build Project'}</p>
          <div>
            <label className="label">{lang === 'ru' ? 'Исходный документ (ТЗ/BRD/SRS)' : 'Source document (TZ/BRD/SRS)'}</label>
            <select className="input" value={form.document_id} onChange={e => setForm(p => ({...p, document_id: e.target.value}))}>
              <option value="">—</option>
              {docs.map(d => <option key={d.id} value={d.id}>{d.title}</option>)}
            </select>
          </div>
          <div>
            <label className="label">{lang === 'ru' ? 'Название приложения' : 'Application name'}</label>
            <input className="input" value={form.name} onChange={e => setForm(p => ({...p, name: e.target.value}))} />
          </div>
          <div>
            <label className="label">{lang === 'ru' ? 'Описание' : 'Description'}</label>
            <textarea className="input min-h-[80px]" value={form.description} onChange={e => setForm(p => ({...p, description: e.target.value}))} />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" className="btn-ghost" onClick={() => setShowForm(false)}>{lang === 'ru' ? 'Отмена' : 'Cancel'}</button>
            <button type="submit" className="btn-primary" disabled={creating}>
              {creating ? <Spinner /> : `✓ ${lang === 'ru' ? 'Создать' : 'Create'}`}
            </button>
          </div>
        </form>
      )}

      <div className="grid grid-cols-3 gap-5">
        {/* Project list */}
        <div className="col-span-1">
          <p className="label mb-3">{lang === 'ru' ? 'Проекты' : 'Projects'}</p>
          {loading ? <Spinner /> : projects.length === 0 ? (
            <EmptyState icon="💰" title={lang === 'ru' ? 'Нет проектов' : 'No projects'} />
          ) : (
            <div className="space-y-2">
              {projects.map(p => {
                const meta = STATUS_META[p.status] || STATUS_META.draft;
                return (
                  <button key={p.id} onClick={() => selectProject(p)}
                    className={`w-full text-left p-3 rounded-lg border transition-all text-sm ${
                      selected?.id === p.id ? 'border-accent/50 bg-accent/10 text-white' : 'border-slate-border text-slate-muted hover:text-white bg-ink-soft'
                    }`}>
                    <p className="font-medium truncate">{p.name}</p>
                    <span className={`inline-block mt-1 text-xs border px-2 py-0.5 rounded ${meta.color}`}>
                      {meta.icon} {p.status}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Workspace */}
        <div className="col-span-2">
          {!selected ? (
            <EmptyState icon="💰" title={lang === 'ru' ? 'Выберите проект' : 'Select a project'} />
          ) : (
            <div className="space-y-5">
              <div className="card border-accent/20 flex items-center justify-between">
                <div>
                  <p className="font-display font-bold text-white">{selected.name}</p>
                  <p className="text-xs text-slate-muted mt-0.5">{selected.description}</p>
                </div>
                <div className="flex gap-2">
                  <button className="btn-ghost text-xs" onClick={() => handleExport('docx')}>⬇ DOCX</button>
                  <button className="btn-ghost text-xs" onClick={() => handleExport('pdf')}>⬇ PDF</button>
                </div>
              </div>

              <Tabs tabs={TABS} active={tab} onChange={setTab} />

              {/* Task estimation */}
              {tab === 'estimate' && (
                <div className="space-y-4">
                  <button className="btn-primary" onClick={handleEstimateTasks} disabled={busy === 'tasks'}>
                    {busy === 'tasks' ? <><Spinner /> {lang === 'ru' ? 'Декомпозирую…' : 'Decomposing…'}</> : `🤖 ${lang === 'ru' ? 'AI-декомпозиция задач' : 'AI Task Decomposition'}`}
                  </button>
                  {report?.latest_task_estimate && (
                    <div className="card space-y-3 animate-fade-in">
                      <div className="flex items-center justify-between">
                        <p className="font-display font-bold">{lang === 'ru' ? 'Оценка трудозатрат' : 'Effort Estimate'}</p>
                        <NeedsReviewBadge show={report.latest_task_estimate.needs_review} />
                      </div>
                      {(() => {
                        try {
                          const data = JSON.parse(report.latest_task_estimate.tasks_json);
                          return (
                            <>
                              <div className="grid grid-cols-5 gap-2">
                                {Object.entries(data.total_hours_by_role || {}).map(([role, hours]: any) => (
                                  <div key={role} className="bg-ink rounded-lg p-2 text-center border border-slate-border/60">
                                    <p className="text-xs text-slate-muted">{role}</p>
                                    <p className="font-mono text-white">{hours}ч</p>
                                  </div>
                                ))}
                              </div>
                              <div className="space-y-1.5 max-h-64 overflow-auto">
                                {data.tasks?.map((t: any, i: number) => (
                                  <div key={i} className="text-xs flex justify-between p-2 bg-ink rounded border border-slate-border/40">
                                    <span className="text-white/80">{t.name}</span>
                                    <span className="text-slate-muted font-mono">{t.role} · {t.estimated_hours}ч</span>
                                  </div>
                                ))}
                              </div>
                            </>
                          );
                        } catch { return null; }
                      })()}
                    </div>
                  )}
                </div>
              )}

              {/* Economics calculator with sliders, live preview, and break-even chart */}
              {tab === 'economics' && (
                <div className="space-y-4">
                  <div className="card space-y-3">
                    <p className="label">{lang === 'ru' ? 'Ставки (руб/час)' : 'Rates (RUB/hour)'}</p>
                    <div className="grid grid-cols-2 gap-3">
                      {([
                        ['rate_backend', 'Backend', 500, 10000, 500],
                        ['rate_frontend', 'Frontend', 500, 10000, 500],
                        ['rate_qa', 'QA', 500, 8000, 500],
                        ['rate_devops', 'DevOps', 500, 10000, 500],
                        ['rate_analyst', 'Analyst', 500, 10000, 500],
                        ['avg_employee_rate', lang === 'ru' ? 'Сотрудник' : 'Employee', 500, 10000, 500],
                      ] as const).map(([key, label, min, max, step]) => (
                        <div key={key}>
                          <div className="flex justify-between items-center">
                            <label className="label text-xs">{label}</label>
                            <span className="font-mono text-xs text-accent">{(rates as any)[key]}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <input type="range" className="w-full accent-accent" min={min} max={max} step={step}
                              value={(rates as any)[key]}
                              onChange={e => setRates(p => ({...p, [key]: parseFloat(e.target.value)}))} />
                            <input type="number" className="input w-20 text-xs p-1" min={min} max={max} step={step}
                              value={(rates as any)[key]}
                              onChange={e => setRates(p => ({...p, [key]: parseFloat(e.target.value) || 0}))} />
                          </div>
                        </div>
                      ))}
                    </div>
                    <p className="label mt-2">{lang === 'ru' ? 'Операционные расходы (руб/мес)' : 'Operating costs (RUB/month)'}</p>
                    <div className="grid grid-cols-3 gap-3">
                      {([
                        ['hosting_cost_monthly', lang === 'ru' ? 'Хостинг' : 'Hosting', 0, 50000, 1000],
                        ['llm_cost_monthly', 'LLM API', 0, 50000, 1000],
                        ['support_hours_monthly', lang === 'ru' ? 'Часы поддержки' : 'Support hours', 0, 100, 1],
                      ] as const).map(([key, label, min, max, step]) => (
                        <div key={key}>
                          <label className="label text-xs">{label} <span className="text-accent font-mono">{(rates as any)[key]}</span></label>
                          <input type="range" className="w-full accent-accent" min={min} max={max} step={step}
                            value={(rates as any)[key]}
                            onChange={e => setRates(p => ({...p, [key]: parseFloat(e.target.value)}))} />
                        </div>
                      ))}
                    </div>
                    <p className="label mt-2">{lang === 'ru' ? 'Выгода' : 'Benefit'}</p>
                    <div>
                      <label className="label">{lang === 'ru' ? 'Экономия часов сотрудников/мес' : 'Employee hours saved/month'} <span className="text-accent font-mono">{rates.time_saved_hours_monthly}</span></label>
                      <input type="range" className="w-full accent-accent" min={0} max={500} step={5}
                        value={rates.time_saved_hours_monthly}
                        onChange={e => setRates(p => ({...p, time_saved_hours_monthly: parseFloat(e.target.value)}))} />
                    </div>

                    {/* Live preview */}
                    {preview && (
                      <div className="grid grid-cols-4 gap-2 p-3 bg-ink rounded-lg border border-accent/20 animate-fade-in">
                        {[
                          { label: 'CAPEX', val: money(preview.capex), color: 'text-white' },
                          { label: 'OPEX/мес', val: money(preview.opexMonthly), color: 'text-yellow-400' },
                          { label: lang === 'ru' ? 'Окупаемость' : 'Payback', val: preview.payback > 0 ? `${preview.payback.toFixed(1)} мес` : '∞', color: 'text-accent' },
                          { label: 'ROI 12мес', val: `${preview.roi.toFixed(1)}%`, color: preview.roi > 0 ? 'text-green-400' : 'text-red-400' },
                        ].map(c => (
                          <div key={c.label} className="text-center">
                            <p className={`font-display text-lg font-bold ${c.color}`}>{c.val}</p>
                            <p className="text-xs text-slate-muted">{c.label} (live)</p>
                          </div>
                        ))}
                      </div>
                    )}

                    <button className="btn-primary mt-2" onClick={handleCalcEconomics} disabled={busy === 'economics'}>
                      {busy === 'economics' ? <Spinner /> : `💾 ${lang === 'ru' ? 'Сохранить в БД' : 'Save to DB'}`}
                    </button>
                  </div>

                  {chartData.length > 0 && (
                    <div className="card animate-fade-in">
                      <p className="font-display font-bold mb-3">{lang === 'ru' ? 'Точка безубыточности (12 мес)' : 'Break-even Analysis (12 months)'}</p>
                      <ResponsiveContainer width="100%" height={280}>
                        <BarChart data={chartData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                          <XAxis dataKey="month" stroke="rgba(255,255,255,0.3)" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }} />
                          <YAxis stroke="rgba(255,255,255,0.3)" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }} />
                          <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#fff' }} />
                          <Legend wrapperStyle={{ fontSize: 12, color: 'rgba(255,255,255,0.7)' }} />
                          <Bar dataKey="Cum. Cost" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                          <Bar dataKey="Cum. Benefit" fill="#22c55e" radius={[4, 4, 0, 0]} />
                          <ReferenceLine y={0} stroke="rgba(255,255,255,0.1)" />
                        </BarChart>
                      </ResponsiveContainer>
                      <p className="text-xs text-slate-muted mt-2 text-center">
                        {lang === 'ru'
                          ? 'Точка безубыточности — месяц, когда Cumulative Benefit пересекает Cumulative Cost'
                          : 'Break-even is the month when Cumulative Benefit crosses Cumulative Cost'}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Plan vs Actual */}
              {tab === 'actuals' && (
                <div className="space-y-4">
                  {!report?.latest_economic_estimate ? (
                    <EmptyState icon="📈" title={lang === 'ru' ? 'Сначала рассчитайте экономику' : 'Calculate economics first'} />
                  ) : (
                    <>
                      <div className="card space-y-3">
                        <p className="label">{lang === 'ru' ? 'Фактические данные после внедрения' : 'Actual figures after launch'}</p>
                        <div className="grid grid-cols-2 gap-3">
                          {[
                            ['actual_capex', 'CAPEX'], ['actual_opex_monthly', 'OPEX/мес'],
                            ['actual_benefit_monthly', lang === 'ru' ? 'Выгода/мес' : 'Benefit/month'],
                            ['actual_time_saved_hours_monthly', lang === 'ru' ? 'Часы экономии/мес' : 'Hours saved/month'],
                          ].map(([key, label]) => (
                            <div key={key}>
                              <label className="label">{label}</label>
                              <input type="number" className="input" value={(actualForm as any)[key]}
                                onChange={e => setActualForm(p => ({...p, [key]: parseFloat(e.target.value) || 0}))} />
                            </div>
                          ))}
                        </div>
                        <textarea className="input" placeholder={lang === 'ru' ? 'Комментарий' : 'Notes'}
                          value={actualForm.notes} onChange={e => setActualForm(p => ({...p, notes: e.target.value}))} />
                        <button className="btn-primary" onClick={handleAddActual} disabled={busy === 'actual'}>
                          {busy === 'actual' ? <Spinner /> : `✓ ${lang === 'ru' ? 'Сохранить факт' : 'Save Actuals'}`}
                        </button>
                      </div>

                      {report.variance && Object.keys(report.variance).length > 0 && (
                        <div className="card space-y-2 animate-fade-in">
                          <p className="label">{lang === 'ru' ? 'Отклонение план/факт' : 'Plan vs Actual Variance'}</p>
                          {Object.entries(report.variance).map(([key, v]: any) => (
                            <div key={key} className="flex items-center justify-between p-2 bg-ink rounded border border-slate-border/50 text-sm">
                              <span className="text-slate-muted">{key}</span>
                              <span className="font-mono">
                                {money(v.plan)} → {money(v.actual)}
                                <span className={v.delta > 0 ? 'text-red-400 ml-2' : 'text-green-400 ml-2'}>
                                  ({v.delta > 0 ? '+' : ''}{v.delta_pct}%)
                                </span>
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
