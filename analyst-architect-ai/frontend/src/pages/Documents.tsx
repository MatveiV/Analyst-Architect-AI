import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { listDocuments, createDocument, reviewDocument, uploadMarkdown } from '../api';
import { SectionHeader, EmptyState, Spinner, toast } from '../components/ui';
import { useI18n } from '../i18n';

interface Doc { id: string; title: string; doc_type: string; project_name?: string; created_at: string; }

const DOC_TYPES_RU = ['ТЗ', 'BRD', 'User Story', 'SRS', 'KB Article'];
const DOC_TYPES_EN = ['TZ', 'BRD', 'User Story', 'SRS', 'KB Article'];
const DOC_TYPE_VALUES = ['tz', 'brd', 'user_story', 'srs', 'kb_article'];

export default function DocumentsPage() {
  const { t, lang } = useI18n();
  const DOC_TYPE_LABELS = lang === 'ru' ? DOC_TYPES_RU : DOC_TYPES_EN;
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const [docs, setDocs] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [reviewing, setReviewing] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: '', text: '', doc_type: 'tz', project_name: '' });
  const navigate = useNavigate();

  const load = useCallback(async () => {
    try { const res = await listDocuments(); setDocs(res.data); }
    catch { toast(t('error_loading'), 'error'); }
    finally { setLoading(false); }
  }, [t]);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim() || form.text.trim().length < 10) return;
    setCreating(true);
    try {
      await createDocument(form);
      toast(t('doc_created'), 'success');
      setShowForm(false);
      setForm({ title: '', text: '', doc_type: 'tz', project_name: '' });
      await load();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const msg = Array.isArray(detail) ? detail.map((d: any) => d.msg).join('; ') : (detail || t('doc_create_err'));
      toast(msg, 'error');
    } finally { setCreating(false); }
  };

  const handleUploadMarkdown = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadMarkdown(file);
      toast('Markdown загружен, диаграммы извлечены', 'success');
      await load();
    } catch { toast('Ошибка загрузки', 'error'); }
    finally { setUploading(false); if (fileInputRef.current) fileInputRef.current.value = ''; }
  };

  const handleReview = async (docId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setReviewing(docId);
    try {
      await reviewDocument(docId);
      toast(t('doc_review_done'), 'success');
      navigate('/reviews');
    } catch { toast(t('doc_review_err'), 'error'); }
    finally { setReviewing(null); }
  };

  const typeLabel = (v: string) => {
    const idx = DOC_TYPE_VALUES.indexOf(v);
    return idx >= 0 ? DOC_TYPE_LABELS[idx] : v;
  };

  return (
    <div>
      <SectionHeader
        title={t('doc_title')}
        subtitle={t('doc_subtitle')}
        action={
          <div className="flex gap-2">
            <button className="btn-primary" onClick={() => setShowForm(v => !v)}>
              {showForm ? `✕ ${t('cancel')}` : t('doc_new')}
            </button>
            <input ref={fileInputRef} type="file" accept=".md,.markdown" className="hidden" onChange={handleUploadMarkdown} />
            <button className="btn-ghost" disabled={uploading} onClick={() => fileInputRef.current?.click()}>
              {uploading ? <Spinner /> : '📄 Загрузить .md'}
            </button>
          </div>
        }
      />

      {showForm && (
        <form onSubmit={handleCreate} className="card border-accent/30 mb-6 space-y-4 animate-fade-in">
          <p className="font-display font-bold text-white">{t('doc_new')}</p>
          <div>
            <label className="label">{t('doc_name')}</label>
            <input className="input" placeholder={lang === 'ru' ? 'Форма заявки с таблицей результатов' : 'Request form with results table'}
              value={form.title} onChange={e => setForm(p => ({...p, title: e.target.value}))} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">{t('doc_type')}</label>
              <select className="input" value={form.doc_type}
                onChange={e => setForm(p => ({...p, doc_type: e.target.value}))}>
                {DOC_TYPE_VALUES.map((v, i) => (
                  <option key={v} value={v}>{DOC_TYPE_LABELS[i]}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">{t('doc_project')}</label>
              <input className="input" placeholder="project-alpha"
                value={form.project_name} onChange={e => setForm(p => ({...p, project_name: e.target.value}))} />
            </div>
          </div>
          <div>
            <label className="label">{t('doc_text')}</label>
            <textarea className="input min-h-[180px] resize-y font-mono text-sm"
              placeholder={lang === 'ru' ? 'Нужна форма заявки для клиентов...' : 'We need a client request form...'}
              value={form.text} onChange={e => setForm(p => ({...p, text: e.target.value}))} />
            <p className="text-xs text-slate-muted mt-1">{form.text.length} / 30 000 {t('doc_chars')}{form.text.trim().length > 0 && form.text.trim().length < 10 && <span className="text-red-400 ml-2">мин. 10 символов</span>}</p>
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" className="btn-ghost" onClick={() => setShowForm(false)}>{t('cancel')}</button>
            <button type="submit" className="btn-primary" disabled={creating}>
              {creating ? <><Spinner /> {t('loading')}</> : `✓ ${t('create')}`}
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      ) : docs.length === 0 ? (
        <EmptyState icon="📄" title={t('doc_empty')} subtitle={t('doc_empty_sub')} />
      ) : (
        <div className="space-y-3">
          {docs.map(doc => (
            <div key={doc.id}
              onClick={() => navigate(`/documents/${doc.id}`)}
              className="card card-hover cursor-pointer flex items-center gap-4">
              <div className="w-9 h-9 rounded-lg bg-ink-muted flex items-center justify-center text-lg shrink-0">
                {doc.doc_type === 'kb_article' ? '🧠' : doc.doc_type === 'markdown' ? '📝' : '📄'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-white truncate">{doc.title}</p>
                <div className="flex items-center gap-3 mt-1 text-xs text-slate-muted">
                  <span className="bg-ink-muted px-2 py-0.5 rounded font-mono">{typeLabel(doc.doc_type)}</span>
                  {doc.project_name && <span>📁 {doc.project_name}</span>}
                  <span>{new Date(doc.created_at).toLocaleDateString(lang === 'ru' ? 'ru' : 'en')}</span>
                </div>
              </div>
              <div className="flex gap-2 shrink-0" onClick={e => e.stopPropagation()}>
                <button className="btn-primary text-xs px-3 py-1.5"
                  disabled={reviewing === doc.id}
                  onClick={e => handleReview(doc.id, e)}>
                  {reviewing === doc.id ? <Spinner /> : t('doc_review_btn')}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
