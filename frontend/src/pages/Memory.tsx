import React, { useState, useEffect, useCallback } from 'react';
import { storeMemory, searchMemory, getRecentMemory, consolidateMemory } from '../api';
import { SectionHeader, EmptyState, Spinner, Tabs, toast } from '../components/ui';
import { useI18n } from '../i18n';

interface MemItem { id: string; memory_type: string; content: string; tags: string; project_name?: string; created_at: string; relevance_score?: number; }

export default function MemoryPage() {
  const { t, lang } = useI18n();

  const TYPES = [
    { value: 'semantic',    labelKey: 'mem_sem'  as const, color: 'text-blue-400 bg-blue-500/10 border-blue-500/30' },
    { value: 'episodic',    labelKey: 'mem_epi'  as const, color: 'text-purple-400 bg-purple-500/10 border-purple-500/30' },
    { value: 'decision',    labelKey: 'mem_dec'  as const, color: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30' },
    { value: 'risk',        labelKey: 'mem_risk' as const, color: 'text-red-400 bg-red-500/10 border-red-500/30' },
    { value: 'requirement', labelKey: 'mem_req'  as const, color: 'text-green-400 bg-green-500/10 border-green-500/30' },
  ];

  const [tab, setTab] = useState('recent');
  const [items, setItems] = useState<MemItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [form, setForm] = useState({ memory_type: 'semantic', content: '', tags: '', project_name: '' });
  const [saving, setSaving] = useState(false);
  const [typeFilter, setTypeFilter] = useState<string | undefined>(undefined);
  const [counts, setCounts] = useState<Record<string, number>>({});

  const loadRecent = useCallback(async () => {
    setLoading(true);
    try { const r = await getRecentMemory(typeFilter); setItems(r.data); }
    catch {} finally { setLoading(false); }
  }, [typeFilter]);

  const loadCounts = useCallback(async () => {
    try {
      const [s, e, d, risk, req] = await Promise.all([
        getRecentMemory('semantic'), getRecentMemory('episodic'),
        getRecentMemory('decision'), getRecentMemory('risk'), getRecentMemory('requirement'),
      ]);
      setCounts({
        semantic: s.data.length, episodic: e.data.length,
        decision: d.data.length, risk: risk.data.length, requirement: req.data.length,
      });
    } catch {}
  }, []);

  useEffect(() => { loadCounts(); }, [loadCounts]);

  useEffect(() => { if (tab === 'recent') loadRecent(); }, [tab, loadRecent]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    try { const r = await searchMemory({ query, limit: 20 }); setItems(r.data); }
    catch { toast(t('error_loading'), 'error'); } finally { setSearching(false); }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await storeMemory({ ...form, tags: form.tags.split(',').map((s: string) => s.trim()).filter(Boolean) });
      toast(t('mem_saved'), 'success');
      setForm({ memory_type: 'semantic', content: '', tags: '', project_name: '' });
      loadRecent();
    } catch { toast(t('mem_save_err'), 'error'); } finally { setSaving(false); }
  };

  const handleConsolidate = async () => {
    try { const r = await consolidateMemory(); toast(`${t('mem_dedup')}: ${r.data.removed_duplicates}`, 'success'); loadRecent(); }
    catch { toast(t('error_loading'), 'error'); }
  };

  const typeInfo = (v: string) => TYPES.find(x => x.value === v);

  const TABS = [
    { key: 'recent', label: t('mem_recent') },
    { key: 'search', label: t('mem_search_tab') },
    { key: 'store',  label: t('mem_store_tab') },
  ];

  return (
    <div>
      <SectionHeader title={t('mem_title')} subtitle={t('mem_subtitle')}
        action={<button className="btn-ghost text-sm" onClick={handleConsolidate}>{t('mem_dedup')}</button>} />
      <div className="flex flex-wrap gap-4 mb-6 p-3 bg-ink-muted rounded-xl border border-slate-border">
        {TYPES.map(tp => (
          <div key={tp.value} className="flex items-center gap-2">
            <span className={`text-xs font-medium border px-2 py-0.5 rounded ${tp.color}`}>{t(tp.labelKey)}</span>
            <span className="text-sm font-bold text-white">{counts[tp.value] ?? '…'}</span>
          </div>
        ))}
      </div>
      <div className="mb-6"><Tabs tabs={TABS} active={tab} onChange={setTab} /></div>

      {tab === 'recent' && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2 mb-4">
            <button onClick={() => setTypeFilter(undefined)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                !typeFilter ? 'border-accent/40 bg-accent/15 text-accent' : 'border-slate-border text-slate-muted hover:text-white'
              }`}>{t('mem_all_types')}</button>
            {TYPES.map(tp => (
              <button key={tp.value} onClick={() => setTypeFilter(tp.value)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                  typeFilter === tp.value ? 'border-accent/40 bg-accent/15 text-accent' : 'border-slate-border text-slate-muted hover:text-white'
                }`}>{t(tp.labelKey)}</button>
            ))}
          </div>
          {loading ? <div className="flex justify-center py-10"><Spinner size="lg" /></div>
          : items.length === 0 ? <EmptyState icon="💾" title={t('mem_empty')} subtitle={t('mem_empty_sub')} />
          : (
            <div className="space-y-2">
              {items.map(item => {
                const info = typeInfo(item.memory_type);
                const tags: string[] = (() => { try { return JSON.parse(item.tags); } catch { return []; } })();
                const isRisk = item.memory_type === 'risk';
                const isLesson = item.memory_type === 'lesson';
                const sevMatch = !isRisk ? null : item.content.match(/\b(low|medium|high|critical)\b/i)?.[0];
                const catMatch = !isLesson ? null : item.content.match(/\b(technology|process|communication|estimation)\b/i)?.[0];
                return (
                  <div key={item.id} className="card">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          {info && <span className={`text-xs font-medium border px-2 py-0.5 rounded ${info.color}`}>{t(info.labelKey)}</span>}
                          {isRisk && sevMatch && (
                            <span className={`text-xs font-medium px-2 py-0.5 rounded border ${sevMatch === 'critical' || sevMatch === 'high' ? 'bg-red-500/20 text-red-300 border-red-500/30' : 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30'}`}>
                              {sevMatch}
                            </span>
                          )}
                          {isLesson && catMatch && (
                            <span className="text-xs font-medium px-2 py-0.5 rounded border bg-purple-500/20 text-purple-300 border-purple-500/30">{catMatch}</span>
                          )}
                          {item.project_name && <span className="text-xs text-slate-muted font-mono">📁 {item.project_name}</span>}
                          {item.relevance_score !== undefined && item.relevance_score > 0 && (
                            <span className="text-xs text-accent font-mono">
                              {Math.round(item.relevance_score * 100)}% {t('mem_relevant')}
                            </span>
                          )}
                        </div>
                        <p className="text-white/80 text-sm leading-relaxed">{item.content}</p>
                        {tags.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {tags.map((tag, i) => (
                              <span key={i} className="text-xs bg-ink-muted text-slate-muted px-2 py-0.5 rounded font-mono">#{tag}</span>
                            ))}
                          </div>
                        )}
                      </div>
                      <span className="text-xs text-slate-muted shrink-0">
                        {new Date(item.created_at).toLocaleDateString(lang === 'ru' ? 'ru' : 'en')}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {tab === 'search' && (
        <div className="space-y-5">
          <form onSubmit={handleSearch} className="flex gap-3">
            <input className="input flex-1" placeholder={lang === 'ru' ? 'Поиск по содержимому памяти...' : 'Search memory content...'}
              value={query} onChange={e => setQuery(e.target.value)} />
            <button type="submit" className="btn-primary" disabled={searching}>
              {searching ? <Spinner /> : `🔍 ${t('search')}`}
            </button>
          </form>
          {items.map(item => {
            const info = typeInfo(item.memory_type);
            return (
              <div key={item.id} className="card animate-fade-in">
                <div className="flex items-center gap-2 mb-2">
                  {info && <span className={`text-xs font-medium border px-2 py-0.5 rounded ${info.color}`}>{t(info.labelKey)}</span>}
                  {item.relevance_score !== undefined && (
                    <span className="text-xs text-accent font-mono">{Math.round((item.relevance_score || 0) * 100)}%</span>
                  )}
                </div>
                <p className="text-white/80 text-sm">{item.content}</p>
              </div>
            );
          })}
        </div>
      )}

      {tab === 'store' && (
        <form onSubmit={handleSave} className="card max-w-2xl space-y-4">
          <p className="font-display font-bold text-white">{t('mem_new')}</p>
          <div>
            <label className="label">{t('mem_type')}</label>
            <div className="flex flex-wrap gap-2">
              {TYPES.map(tp => (
                <button key={tp.value} type="button"
                  onClick={() => setForm(p => ({...p, memory_type: tp.value}))}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                    form.memory_type === tp.value ? tp.color : 'border-slate-border text-slate-muted hover:text-white'
                  }`}>{t(tp.labelKey)}</button>
              ))}
            </div>
          </div>
          <div>
            <label className="label">{t('mem_content')}</label>
            <textarea className="input min-h-[100px] resize-y"
              placeholder={t('mem_content_ph')}
              value={form.content} onChange={e => setForm(p => ({...p, content: e.target.value}))} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">{t('mem_tags')}</label>
              <input className="input" placeholder="api, risk, integration"
                value={form.tags} onChange={e => setForm(p => ({...p, tags: e.target.value}))} />
            </div>
            <div>
              <label className="label">{t('mem_project')}</label>
              <input className="input" placeholder="project-alpha"
                value={form.project_name} onChange={e => setForm(p => ({...p, project_name: e.target.value}))} />
            </div>
          </div>
          <div className="flex justify-end">
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? <><Spinner /> {t('loading')}</> : `💾 ${t('save')}`}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
