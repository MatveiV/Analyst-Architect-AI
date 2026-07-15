import React, { useState, useEffect, useCallback } from 'react';
import { getAuditRuns, getAuditStats } from '../api';
import { SectionHeader, EmptyState, Spinner, JsonViewer, toast } from '../components/ui';
import { useI18n } from '../i18n';

interface AuditRun { id: string; action: string; status: string; input: string; output: string; error?: string; duration_ms: number; created_at: string; }
interface Stats { total: number; ok: number; errors: number; needs_review: number; avg_duration_ms: number; needs_review_pct: number; }

const ACTION_KEYS: Record<string, string> = {
  review: 'Рецензия / Review', direct_review: 'Прямая рецензия / Direct review',
  ask_kb: 'Вопрос KB / KB Question', direct_answer: 'Прямой ответ / Direct answer',
  generate_urs: 'URS', generate_srs: 'SRS', generate_adr: 'ADR',
  recommend_architecture: 'Архитектура / Architecture', design_api: 'API Spec',
  generate_diagrams: 'Диаграммы / Diagrams', generate_c4: 'C4',
  generate_uml: 'UML', generate_erd: 'ERD',
  memory_store: 'Память / Memory',
};

const STATUS_STYLES: Record<string, string> = {
  ok:           'text-green-400 bg-ok-bg border-green-500/30',
  error:        'text-red-400 bg-danger-bg border-red-500/30',
  needs_review: 'text-yellow-400 bg-warn-bg border-yellow-500/30',
};

export default function AuditPage() {
  const { t, lang } = useI18n();
  const [runs, setRuns] = useState<AuditRun[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(0);
  const [expanded, setExpanded] = useState<string | null>(null);
  const PAGE_SIZE = 20;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [runsRes, statsRes] = await Promise.all([
        getAuditRuns({ action: actionFilter || undefined, status: statusFilter || undefined, limit: PAGE_SIZE, offset: page * PAGE_SIZE }),
        getAuditStats(),
      ]);
      setRuns(runsRes.data); setStats(statsRes.data);
    } catch { toast(t('error_loading'), 'error'); }
    finally { setLoading(false); }
  }, [actionFilter, statusFilter, page, t]);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <SectionHeader title={t('audit_title')} subtitle={t('audit_subtitle')} />

      {stats && (
        <>
          <div className="grid grid-cols-4 gap-4 mb-4">
            {[
              { label: t('audit_total'),  value: stats.total,        color: 'text-white' },
              { label: t('audit_ok'),     value: stats.ok,           color: 'text-green-400' },
              { label: t('audit_review'), value: stats.needs_review, color: 'text-yellow-400' },
              { label: t('audit_errors'), value: stats.errors,       color: 'text-red-400' },
            ].map(s => (
              <div key={s.label} className="card text-center">
                <p className={`font-display text-3xl font-bold ${s.color}`}>{s.value}</p>
                <p className="text-xs text-slate-muted mt-1">{s.label}</p>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="card flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center text-accent">⏱</div>
              <div>
                <p className="font-display text-xl font-bold text-white">{stats.avg_duration_ms} ms</p>
                <p className="text-xs text-slate-muted">{t('audit_avg_time')}</p>
              </div>
            </div>
            <div className="card flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-warn-bg flex items-center justify-center text-yellow-400">%</div>
              <div>
                <p className="font-display text-xl font-bold text-white">{stats.needs_review_pct}%</p>
                <p className="text-xs text-slate-muted">{t('audit_nr_pct')}</p>
              </div>
            </div>
          </div>
        </>
      )}

      <div className="flex gap-3 mb-5">
        <select className="input w-52" value={actionFilter} onChange={e => { setActionFilter(e.target.value); setPage(0); }}>
          <option value="">{t('audit_all_ops')}</option>
          {Object.entries(ACTION_KEYS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select className="input w-44" value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(0); }}>
          <option value="">{t('audit_all_stat')}</option>
          <option value="ok">✓ OK</option>
          <option value="error">✗ {t('audit_errors')}</option>
          <option value="needs_review">⚠ {t('audit_review')}</option>
        </select>
        <button className="btn-ghost text-sm" onClick={load}>{t('refresh')}</button>
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      ) : runs.length === 0 ? (
        <EmptyState icon="📋" title={t('audit_empty')} subtitle={t('audit_empty_sub')} />
      ) : (
        <>
          <div className="rounded-xl border border-slate-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-ink-muted text-slate-muted text-xs uppercase tracking-wider">
                  <th className="px-4 py-3 text-left">{t('audit_time')}</th>
                  <th className="px-4 py-3 text-left">{t('audit_action')}</th>
                  <th className="px-4 py-3 text-left">{t('audit_status')}</th>
                  <th className="px-4 py-3 text-right">{t('audit_duration')}</th>
                  <th className="px-4 py-3 text-left">{t('audit_err_col')}</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run, i) => (
                  <React.Fragment key={run.id}>
                    <tr className={`border-t border-slate-border transition-colors hover:bg-ink-muted/50 ${i % 2 === 0 ? 'bg-ink-soft' : 'bg-ink'}`}>
                      <td className="px-4 py-3 font-mono text-xs text-slate-muted whitespace-nowrap">
                        {new Date(run.created_at).toLocaleString(lang === 'ru' ? 'ru' : 'en', { hour: '2-digit', minute: '2-digit', second: '2-digit', day: '2-digit', month: '2-digit' })}
                      </td>
                      <td className="px-4 py-3 text-white font-medium">{ACTION_KEYS[run.action] || run.action}</td>
                      <td className="px-4 py-3">
                        <span className={`text-xs font-mono border px-2 py-0.5 rounded ${STATUS_STYLES[run.status] || ''}`}>{run.status}</span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-xs text-slate-muted">{run.duration_ms}</td>
                      <td className="px-4 py-3 text-xs text-red-400 max-w-xs truncate">{run.error || '—'}</td>
                      <td className="px-4 py-3">
                        <button onClick={() => setExpanded(expanded === run.id ? null : run.id)}
                          className="text-xs text-slate-muted hover:text-accent transition-colors">
                          {expanded === run.id ? '▲' : '▼'}
                        </button>
                      </td>
                    </tr>
                    {expanded === run.id && (
                      <tr className="border-t border-slate-border bg-ink animate-fade-in">
                        <td colSpan={6} className="p-4">
                          <div className="grid grid-cols-2 gap-4">
                            <div><p className="label mb-2">{t('audit_input')}</p><JsonViewer data={run.input} /></div>
                            <div><p className="label mb-2">{t('audit_output')}</p><JsonViewer data={run.output} /></div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between mt-4">
            <p className="text-xs text-slate-muted">{t('audit_page')} {page + 1}</p>
            <div className="flex gap-2">
              <button className="btn-ghost text-xs" disabled={page === 0} onClick={() => setPage(p => p - 1)}>{t('audit_prev')}</button>
              <button className="btn-ghost text-xs" disabled={runs.length < PAGE_SIZE} onClick={() => setPage(p => p + 1)}>{t('audit_next')}</button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
