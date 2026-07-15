import React, { useState, useEffect, useCallback } from 'react';
import { useI18n } from '../i18n';
import { SectionHeader, EmptyState, Spinner, toast } from '../components/ui';
import api from '../api';

interface RiskItem {
  id: string; title: string; description: string;
  probability: number; impact: number; severity: string;
  category: string; status: string; owner: string | null;
  mitigation: string | null; project_name: string | null;
  document_id: string | null; source: string;
  created_at: string; updated_at: string;
}

interface RiskStats {
  total: number; by_severity: Record<string, number>;
  by_category: Record<string, number>; by_status: Record<string, number>;
  by_project: Record<string, number>;
}

const CATEGORIES = ['tech', 'process', 'business', 'security'];
const STATUSES = ['open', 'mitigated', 'closed', 'accepted', 'reopened'];
const SEVERITY_COLORS: Record<string, string> = {
  low: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  medium: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  high: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
  critical: 'bg-red-500/20 text-red-300 border-red-500/30',
};

const emptyForm = () => ({
  title: '', description: '', probability: 1, impact: 1,
  category: 'tech', status: 'open', owner: '', mitigation: '',
  project_name: '', document_id: null as string | null,
});

export default function RiskCatalogPage() {
  const { t } = useI18n();
  const [items, setItems] = useState<RiskItem[]>([]);
  const [stats, setStats] = useState<RiskStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string | undefined>(undefined);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm());
  const [showForm, setShowForm] = useState(false);
  const [showStats, setShowStats] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (filter) params.status = filter;
      const res = await api.get('/api/risk-catalog', { params });
      setItems(res.data);
      const statsRes = await api.get('/api/risk-catalog/stats');
      setStats(statsRes.data);
    } catch { toast(t('error_loading'), 'error'); }
    finally { setLoading(false); }
  }, [filter, t]);

  useEffect(() => { load(); }, [load]);

  const handleSave = async () => {
    try {
      const payload = { ...form, owner: form.owner || null, mitigation: form.mitigation || null };
      if (editId) {
        await api.put(`/api/risk-catalog/${editId}`, payload);
      } else {
        await api.post('/api/risk-catalog', payload);
      }
      toast(t('risk_saved'));
      setShowForm(false);
      setEditId(null);
      setForm(emptyForm());
      load();
    } catch { toast(t('error_loading'), 'error'); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm(t('delete') + '?')) return;
    try {
      await api.delete(`/api/risk-catalog/${id}`);
      toast(t('risk_deleted'));
      load();
    } catch { toast(t('error_loading'), 'error'); }
  };

  const handleEdit = (item: RiskItem) => {
    setForm({
      title: item.title, description: item.description,
      probability: item.probability, impact: item.impact,
      category: item.category, status: item.status,
      owner: item.owner || '', mitigation: item.mitigation || '',
      project_name: item.project_name || '', document_id: null,
    });
    setEditId(item.id);
    setShowForm(true);
  };

  const exportCsv = async () => {
    const res = await api.get('/api/risk-catalog/export/csv', { responseType: 'blob' });
    const url = URL.createObjectURL(new Blob([res.data]));
    const a = document.createElement('a'); a.href = url; a.download = 'risk_catalog.csv'; a.click();
    URL.revokeObjectURL(url);
  };

  const severityLabel = (s: string) => {
    const map: Record<string, string> = {
      low: t('risk_sev_low'), medium: t('risk_sev_med'),
      high: t('risk_sev_high'), critical: t('risk_sev_crit'),
    };
    return map[s] || s;
  };

  const catLabel = (c: string) => {
    const map: Record<string, string> = {
      tech: t('risk_cat_tech'), process: t('risk_cat_proc'),
      business: t('risk_cat_biz'), security: t('risk_cat_sec'),
    };
    return map[c] || c;
  };

  const statusLabel = (s: string) => {
    const map: Record<string, string> = {
      open: t('risk_st_open'), mitigated: t('risk_st_mit'),
      closed: t('risk_st_closed'), accepted: t('risk_st_acc'),
      reopened: t('risk_st_reopen'),
    };
    return map[s] || s;
  };

  return (
    <div>
      <div className="flex items-center justify-between">
        <SectionHeader title={t('risk_title')} subtitle={t('risk_subtitle')} />
        <div className="flex gap-2">
          <button onClick={() => setShowStats(v => !v)} className="px-3 py-1.5 rounded-lg text-sm border border-slate-border text-slate-muted hover:text-white transition-all">
            {t('risk_stats')}
          </button>
          <button onClick={exportCsv} className="px-3 py-1.5 rounded-lg text-sm border border-slate-border text-slate-muted hover:text-white transition-all">
            {t('risk_export_csv')}
          </button>
          <button onClick={() => { setEditId(null); setForm(emptyForm()); setShowForm(true); }} className="px-4 py-1.5 rounded-lg text-sm font-medium bg-accent/20 text-accent border border-accent/30 hover:bg-accent/30 transition-all">
            {t('risk_new')}
          </button>
        </div>
      </div>

      {showStats && stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6 p-4 bg-ink-muted rounded-xl border border-slate-border">
          <div><p className="text-xs text-slate-muted">{t('risk_total')}</p><p className="text-2xl font-bold text-white">{stats.total}</p></div>
          <div><p className="text-xs text-slate-muted">{t('risk_severity')}</p>{Object.entries(stats.by_severity).map(([k, v]) => <div key={k} className="text-sm"><span className="text-slate-muted">{severityLabel(k)}:</span> {v}</div>)}</div>
          <div><p className="text-xs text-slate-muted">{t('risk_category')}</p>{Object.entries(stats.by_category).map(([k, v]) => <div key={k} className="text-sm"><span className="text-slate-muted">{catLabel(k)}:</span> {v}</div>)}</div>
          <div><p className="text-xs text-slate-muted">{t('risk_status')}</p>{Object.entries(stats.by_status).map(([k, v]) => <div key={k} className="text-sm"><span className="text-slate-muted">{statusLabel(k)}:</span> {v}</div>)}</div>
        </div>
      )}

      <div className="flex gap-2 mb-6 flex-wrap">
        {[{ label: t('all'), value: undefined }, ...STATUSES.map(s => ({ label: statusLabel(s), value: s }))].map(f => (
          <button key={String(f.value)} onClick={() => setFilter(f.value)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              filter === f.value ? 'bg-accent/20 text-accent border border-accent/30' : 'text-slate-muted border border-slate-border hover:text-white'
            }`}>
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      ) : items.length === 0 ? (
        <EmptyState icon="⚠️" title={t('risk_empty')} subtitle={t('risk_empty_sub')} />
      ) : (
        <div className="space-y-3">
          {items.map(item => (
            <div key={item.id} className="bg-ink-muted border border-slate-border rounded-xl p-4 hover:border-accent/20 transition-all">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded border ${SEVERITY_COLORS[item.severity] || SEVERITY_COLORS.medium}`}>
                      {severityLabel(item.severity)} ({item.probability}×{item.impact})
                    </span>
                    <span className="text-xs text-slate-muted border border-slate-border rounded px-1.5 py-0.5">{catLabel(item.category)}</span>
                    <span className="text-xs text-slate-muted border border-slate-border rounded px-1.5 py-0.5">{statusLabel(item.status)}</span>
                    <span className="text-xs text-slate-muted">{t('risk_source')}: {item.source}</span>
                  </div>
                  <h3 className="text-white font-medium truncate">{item.title}</h3>
                  {item.description && <p className="text-sm text-slate-muted mt-1 line-clamp-2">{item.description}</p>}
                  {item.mitigation && <p className="text-xs text-slate-muted mt-1"><span className="text-accent">{t('risk_mitigation')}:</span> {item.mitigation}</p>}
                  <div className="flex gap-3 mt-2 text-xs text-slate-muted">
                    {item.project_name && <span>{t('risk_project')}: {item.project_name}</span>}
                    {item.owner && <span>{t('risk_owner')}: {item.owner}</span>}
                  </div>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button onClick={() => handleEdit(item)} className="px-2 py-1 text-xs text-slate-muted hover:text-white border border-slate-border rounded-lg transition-all">✎</button>
                  <button onClick={() => handleDelete(item.id)} className="px-2 py-1 text-xs text-red-400 hover:text-red-300 border border-red-500/30 rounded-lg transition-all">✕</button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showForm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowForm(false)}>
          <div className="bg-ink-soft border border-slate-border rounded-2xl p-6 w-full max-w-lg mx-4" onClick={e => e.stopPropagation()}>
            <h2 className="text-lg font-bold text-white mb-4">{editId ? t('risk_edit') : t('risk_create')}</h2>
            <div className="space-y-3">
              <input placeholder={t('risk_title_f')} value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-ink border border-slate-border text-white text-sm focus:border-accent outline-none" />
              <textarea placeholder={t('risk_desc')} rows={3} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-ink border border-slate-border text-white text-sm focus:border-accent outline-none" />
              <div className="grid grid-cols-2 gap-3">
                <div><label className="text-xs text-slate-muted">{t('risk_prob')}</label>
                  <input type="number" min={1} max={5} value={form.probability} onChange={e => setForm(f => ({ ...f, probability: +e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg bg-ink border border-slate-border text-white text-sm focus:border-accent outline-none" /></div>
                <div><label className="text-xs text-slate-muted">{t('risk_impact')}</label>
                  <input type="number" min={1} max={5} value={form.impact} onChange={e => setForm(f => ({ ...f, impact: +e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg bg-ink border border-slate-border text-white text-sm focus:border-accent outline-none" /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <select value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-ink border border-slate-border text-white text-sm focus:border-accent outline-none">
                  {CATEGORIES.map(c => <option key={c} value={c}>{catLabel(c)}</option>)}
                </select>
                <select value={form.status} onChange={e => setForm(f => ({ ...f, status: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-ink border border-slate-border text-white text-sm focus:border-accent outline-none">
                  {STATUSES.map(s => <option key={s} value={s}>{statusLabel(s)}</option>)}
                </select>
              </div>
              <input placeholder={t('risk_owner')} value={form.owner} onChange={e => setForm(f => ({ ...f, owner: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-ink border border-slate-border text-white text-sm focus:border-accent outline-none" />
              <textarea placeholder={t('risk_mitigation')} rows={2} value={form.mitigation} onChange={e => setForm(f => ({ ...f, mitigation: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-ink border border-slate-border text-white text-sm focus:border-accent outline-none" />
              <input placeholder={t('risk_project')} value={form.project_name} onChange={e => setForm(f => ({ ...f, project_name: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-ink border border-slate-border text-white text-sm focus:border-accent outline-none" />
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-slate-muted hover:text-white border border-slate-border rounded-lg transition-all">{t('cancel')}</button>
              <button onClick={handleSave} className="px-4 py-2 text-sm font-medium bg-accent/20 text-accent border border-accent/30 rounded-lg hover:bg-accent/30 transition-all">{t('save')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
