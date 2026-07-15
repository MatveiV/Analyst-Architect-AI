import React, { useState, useEffect, useCallback } from 'react';
import { addKBDocument, listKBDocuments, askKB, getQAHistory, reindexKB } from '../api';
import { SectionHeader, EmptyState, Spinner, NeedsReviewBadge, Tabs, toast } from '../components/ui';
import { useI18n } from '../i18n';

interface KBDoc { id: string; title: string; created_at: string; }
interface QARun { id: string; question: string; answer: string; sources_json: string; needs_review: boolean; created_at: string; }

export default function KnowledgeBasePage() {
  const { t, lang } = useI18n();
  const [tab, setTab] = useState('ask');
  const [docs, setDocs] = useState<KBDoc[]>([]);
  const [history, setHistory] = useState<QARun[]>([]);
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState<any>(null);
  const [asking, setAsking] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [form, setForm] = useState({ title: '', text: '' });
  const [adding, setAdding] = useState(false);
  const [histFilter, setHistFilter] = useState<boolean | undefined>(undefined);

  const loadDocs = useCallback(async () => {
    try { const r = await listKBDocuments(); setDocs(r.data); } catch {}
  }, []);

  const loadHistory = useCallback(async () => {
    setLoading(true);
    try { const r = await getQAHistory(histFilter); setHistory(r.data); } catch {}
    finally { setLoading(false); }
  }, [histFilter]);

  useEffect(() => { loadDocs(); loadHistory(); }, [loadDocs, loadHistory]);

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    setAsking(true); setAnswer(null);
    try { const res = await askKB(question); setAnswer(res.data); }
    catch { toast(t('error_loading'), 'error'); }
    finally { setAsking(false); loadHistory(); }
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setAdding(true);
    try {
      await addKBDocument({ ...form, doc_type: 'kb_article' });
      toast(t('kb_added'), 'success');
      setShowAddForm(false); setForm({ title: '', text: '' });
      loadDocs();
    } catch { toast(t('error_loading'), 'error'); }
    finally { setAdding(false); }
  };

  const handleReindex = async () => {
    try { const r = await reindexKB(); toast(`${t('kb_reindex')}: ${r.data.indexed}`, 'success'); }
    catch { toast(t('error_loading'), 'error'); }
  };

  const TABS = [
    { key: 'ask',     label: t('kb_ask_tab') },
    { key: 'docs',    label: `${t('kb_docs_tab')} (${docs.length})` },
    { key: 'history', label: t('kb_history_tab') },
  ];

  const histFilters = [
    { label: t('all'), v: undefined },
    { label: t('kb_answered'), v: false },
    { label: t('kb_no_data'), v: true },
  ];

  return (
    <div>
      <SectionHeader title={t('kb_title')} subtitle={t('kb_subtitle')} />
      <div className="mb-6"><Tabs tabs={TABS} active={tab} onChange={setTab} /></div>

      {tab === 'ask' && (
        <div className="space-y-5">
          <form onSubmit={handleAsk} className="card">
            <label className="label">{t('kb_question')}</label>
            <div className="flex gap-3">
              <input className="input flex-1" placeholder={t('kb_placeholder')}
                value={question} onChange={e => setQuestion(e.target.value)} />
              <button type="submit" className="btn-primary" disabled={asking || !question.trim()}>
                {asking ? <Spinner /> : t('kb_ask_btn')}
              </button>
            </div>
          </form>
          {asking && (
            <div className="card border-accent/30 bg-accent-glow flex items-center gap-3">
              <Spinner size="md" /><span className="text-accent-light text-sm">{t('kb_searching')}</span>
            </div>
          )}
          {answer && (
            <div className="card animate-fade-in space-y-4">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm text-slate-muted font-mono">{question}</p>
                <NeedsReviewBadge show={answer.needs_review} />
              </div>
              <div className="bg-ink rounded-lg p-4 border border-slate-border">
                <p className="text-white leading-relaxed">{answer.answer}</p>
              </div>
              {answer.sources?.length > 0 && (
                <div>
                  <p className="label">{t('kb_sources')} ({answer.sources.length})</p>
                  <div className="space-y-2">
                    {answer.sources.map((s: any, i: number) => (
                      <div key={i} className="p-3 bg-ink rounded-lg border border-slate-border/60 text-sm">
                        <p className="text-accent-light text-xs mb-1">{s.document_title || s.document_id?.slice(0, 8)}</p>
                        <p className="text-white/70 italic">«{s.quote}»</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {tab === 'docs' && (
        <div className="space-y-4">
          <div className="flex justify-between">
            <p className="text-slate-muted text-sm">{docs.length} {t('kb_docs_count')}</p>
            <div className="flex gap-2">
              <button className="btn-ghost text-xs" onClick={handleReindex}>{t('kb_reindex')}</button>
              <button className="btn-primary text-sm" onClick={() => setShowAddForm(v => !v)}>+ {t('add')}</button>
            </div>
          </div>
          {showAddForm && (
            <form onSubmit={handleAdd} className="card border-accent/30 space-y-4 animate-fade-in">
              <p className="font-display font-bold">{t('kb_new_doc')}</p>
              <div>
                <label className="label">{t('doc_name')}</label>
                <input className="input" placeholder={lang === 'ru' ? 'Правила работы команды' : 'Team working rules'}
                  value={form.title} onChange={e => setForm(p => ({...p, title: e.target.value}))} />
              </div>
              <div>
                <label className="label">{t('kb_content')}</label>
                <textarea className="input min-h-[150px] font-mono text-sm resize-y"
                  placeholder={lang === 'ru' ? 'Содержимое документа...' : 'Document content...'}
                  value={form.text} onChange={e => setForm(p => ({...p, text: e.target.value}))} />
              </div>
              <div className="flex justify-end gap-2">
                <button type="button" className="btn-ghost" onClick={() => setShowAddForm(false)}>{t('cancel')}</button>
                <button type="submit" className="btn-primary" disabled={adding}>
                  {adding ? <Spinner /> : `✓ ${t('add')}`}
                </button>
              </div>
            </form>
          )}
          {docs.length === 0 ? (
            <EmptyState icon="📚" title={t('kb_empty')} subtitle={t('kb_empty_sub')} />
          ) : (
            <div className="space-y-2">
              {docs.map(doc => (
                <div key={doc.id} className="card flex items-center gap-4">
                  <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center text-accent">🧠</div>
                  <div className="flex-1">
                    <p className="text-white font-medium">{doc.title}</p>
                    <p className="text-xs text-slate-muted">{new Date(doc.created_at).toLocaleDateString(lang === 'ru' ? 'ru' : 'en')}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'history' && (
        <div className="space-y-4">
          <div className="flex gap-2 mb-4">
            {histFilters.map(f => (
              <button key={String(f.v)}
                onClick={() => setHistFilter(f.v as any)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                  histFilter === f.v ? 'border-accent/40 bg-accent/15 text-accent' : 'border-slate-border text-slate-muted hover:text-white'
                }`}>
                {f.label}
              </button>
            ))}
          </div>
          {loading ? (
            <div className="flex justify-center py-10"><Spinner size="lg" /></div>
          ) : history.length === 0 ? (
            <EmptyState icon="🕐" title={t('kb_no_history')} subtitle={t('kb_no_hist_sub')} />
          ) : (
            <div className="space-y-3">
              {history.map(qa => (
                <div key={qa.id} className="card space-y-2">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm text-accent font-medium">❓ {qa.question}</p>
                    <div className="flex items-center gap-2 shrink-0">
                      <NeedsReviewBadge show={qa.needs_review} />
                      <span className="text-xs text-slate-muted">{new Date(qa.created_at).toLocaleDateString(lang === 'ru' ? 'ru' : 'en')}</span>
                    </div>
                  </div>
                  <p className="text-white/80 text-sm leading-relaxed">{qa.answer}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
