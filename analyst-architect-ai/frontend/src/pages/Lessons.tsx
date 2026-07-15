import React, { useState, useEffect, useCallback } from 'react';
import { useI18n } from '../i18n';
import { SectionHeader, EmptyState, Spinner, toast } from '../components/ui';
import api from '../api';

interface LessonItem {
  id: string; title: string; description: string;
  category: string; impact_type: string;
  root_cause: string | null; recommendation: string | null;
  project_name: string | null; source: string;
  created_at: string; updated_at: string;
}

const CATEGORIES = ['technology', 'process', 'communication', 'estimation'];
const IMPACT_TYPES = ['positive', 'negative'];

const CAT_COLORS: Record<string, string> = {
  technology: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  process: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  communication: 'bg-green-500/20 text-green-300 border-green-500/30',
  estimation: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
};

const emptyForm = () => ({
  title: '', description: '', category: 'technology',
  impact_type: 'negative', root_cause: '', recommendation: '',
  project_name: '', document_id: null as string | null,
});

export default function LessonsPage() {
  const { t } = useI18n();
  const [items, setItems] = useState<LessonItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterCat, setFilterCat] = useState<string | undefined>(undefined);
  const [filterImpact, setFilterImpact] = useState<string | undefined>(undefined);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm());
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (filterCat) params.category = filterCat;
      if (filterImpact) params.impact_type = filterImpact;
      const res = await api.get('/api/lessons', { params });
      setItems(res.data);
    } catch { toast(t('error_loading'), 'error'); }
    finally { setLoading(false); }
  }, [filterCat, filterImpact, t]);

  useEffect(() => { load(); }, [load]);

  const handleSave = async () => {
    try {
      const payload = { ...form, root_cause: form.root_cause || null, recommendation: form.recommendation || null };
      if (editId) {
        await api.put(`/api/lessons/${editId}`, payload);
      } else {
        await api.post('/api/lessons', payload);
      }
      toast(t('less_saved'));
      setShowForm(false);
      setEditId(null);
      setForm(emptyForm());
      load();
    } catch { toast(t('error_loading'), 'error'); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm(t('delete') + '?')) return;
    try {
      await api.delete(`/api/lessons/${id}`);
      toast(t('less_deleted'));
      load();
    } catch { toast(t('error_loading'), 'error'); }
  };

  const handleEdit = (item: LessonItem) => {
    setForm({
      title: item.title, description: item.description,
      category: item.category, impact_type: item.impact_type,
      root_cause: item.root_cause || '', recommendation: item.recommendation || '',
      project_name: item.project_name || '', document_id: null,
    });
    setEditId(item.id);
    setShowForm(true);
  };

  const catLabel = (c: string) => {
    const map: Record<string, string> = { technology: t('less_cat_tech'), process: t('less_cat_proc'), communication: t('less_cat_comm'), estimation: t('less_cat_est') };
    return map[c] || c;
  };

  const impactLabel = (i: string) => i === 'positive' ? t('less_impact_pos') : t('less_impact_neg');

  const exportCsv = async () => {
    const res = await api.get('/api/lessons/export/csv', { responseType: 'blob' });
    const url = URL.createObjectURL(new Blob([res.data]));
    const a = document.createElement('a'); a.href = url; a.download = 'project_lessons.csv'; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div className="flex items-center justify-between">
        <SectionHeader title={t('less_title')} subtitle={t('less_subtitle')} />
        <div className="flex gap-2">
          <button onClick={exportCsv} className="px-3 py-1.5 rounded-lg text-sm border border-slate-border text-slate-muted hover:text-white transition-all">
            {t('less_export_csv')}
          </button>
          <button onClick={() => { setEditId(null); setForm(emptyForm()); setShowForm(true); }} className="px-4 py-1.5 rounded-lg text-sm font-medium bg-accent/20 text-accent border border-accent/30 hover:bg-accent/30 transition-all">
            {t('less_new')}
          </button>
        </div>
      </div>

      <div className="flex gap-2 mb-6 flex-wrap">
        <select value={filterCat || ''} onChange={e => setFilterCat(e.target.value || undefined)}
          className="px-3 py-1.5 rounded-lg bg-ink border border-slate-border text-sm text-slate-muted focus:border-accent outline-none">
          <option value="">{t('all')} — {t('less_category')}</option>
          {CATEGORIES.map(c => <option key={c} value={c}>{catLabel(c)}</option>)}
        </select>
        <select value={filterImpact || ''} onChange={e => setFilterImpact(e.target.value || undefined)}
          className="px-3 py-1.5 rounded-lg bg-ink border border-slate-border text-sm text-slate-muted focus:border-accent outline-none">
          <option value="">{t('all')} — {t('less_impact')}</option>
          {IMPACT_TYPES.map(i => <option key={i} value={i}>{impactLabel(i)}</option>)}
        </select>
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      ) : items.length === 0 ? (
        <EmptyState icon="📚" title={t('less_empty')} subtitle={t('less_empty_sub')} />
      ) : (
        <div className="space-y-3">
          {items.map(item => (
            <div key={item.id} className="bg-ink-muted border border-slate-border rounded-xl p-4 hover:border-accent/20 transition-all">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded border ${CAT_COLORS[item.category] || CAT_COLORS.process}`}>
                      {catLabel(item.category)}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded border ${item.impact_type === 'positive' ? 'bg-green-500/20 text-green-300 border-green-500/30' : 'bg-red-500/20 text-red-300 border-red-500/30'}`}>
                      {impactLabel(item.impact_type)}
                    </span>
                    <span className="text-xs text-slate-muted">{t('less_source')}: {item.source}</span>
                  </div>
                  <h3 className="text-white font-medium truncate">{item.title}</h3>
                  {item.description && <p className="text-sm text-slate-muted mt-1 line-clamp-2">{item.description}</p>}
                  {item.root_cause && <p className="text-xs text-slate-muted mt-1"><span className="text-accent">{t('less_root_cause')}:</span> {item.root_cause}</p>}
                  {item.recommendation && <p className="text-xs text-slate-muted mt-1"><span className="text-accent">{t('less_recommend')}:</span> {item.recommendation}</p>}
                  {item.project_name && <p className="text-xs text-slate-muted mt-2">{t('less_project')}: {item.project_name}</p>}
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
            <h2 className="text-lg font-bold text-white mb-4">{editId ? t('less_edit') : t('less_create')}</h2>
            <div className="space-y-3">
              <input placeholder={t('less_title_f')} value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-ink border border-slate-border text-white text-sm focus:border-accent outline-none" />
              <textarea placeholder={t('less_desc')} rows={3} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-ink border border-slate-border text-white text-sm focus:border-accent outline-none" />
              <div className="grid grid-cols-2 gap-3">
                <select value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-ink border border-slate-border text-white text-sm focus:border-accent outline-none">
                  {CATEGORIES.map(c => <option key={c} value={c}>{catLabel(c)}</option>)}
                </select>
                <select value={form.impact_type} onChange={e => setForm(f => ({ ...f, impact_type: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-ink border border-slate-border text-white text-sm focus:border-accent outline-none">
                  {IMPACT_TYPES.map(i => <option key={i} value={i}>{impactLabel(i)}</option>)}
                </select>
              </div>
              <textarea placeholder={t('less_root_cause')} rows={2} value={form.root_cause} onChange={e => setForm(f => ({ ...f, root_cause: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-ink border border-slate-border text-white text-sm focus:border-accent outline-none" />
              <textarea placeholder={t('less_recommend')} rows={2} value={form.recommendation} onChange={e => setForm(f => ({ ...f, recommendation: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-ink border border-slate-border text-white text-sm focus:border-accent outline-none" />
              <input placeholder={t('less_project')} value={form.project_name} onChange={e => setForm(f => ({ ...f, project_name: e.target.value }))}
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
