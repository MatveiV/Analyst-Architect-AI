import React, { useState, useEffect, useCallback } from 'react';
import { createBatchReview, listBatchReviews, getBatchReview, exportBatchReviewCsv } from '../api';
import { SectionHeader, EmptyState, Spinner, NeedsReviewBadge, ConfidenceBadge, toast } from '../components/ui';
import { useI18n } from '../i18n';
import { Link } from 'react-router-dom';

interface BatchItem {
  id: string;
  order_index: number;
  title: string;
  document_id: string | null;
  review_id: string | null;
  status: string;
  needs_review: boolean;
  confidence: string | null;
  error: string | null;
}

interface BatchSummary {
  id: string;
  created_at: string;
  title: string | null;
  status: string;
  total_count: number;
  completed_count: number;
  needs_review_count: number;
  error_count: number;
}

interface BatchDetail extends BatchSummary {
  items: BatchItem[];
}

interface FormRow { title: string; text: string; }

const EMPTY_ROW = (): FormRow => ({ title: '', text: '' });

export default function BatchReviewPage() {
  const { t, lang } = useI18n();
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [selected, setSelected] = useState<BatchDetail | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [onlyNeedsReview, setOnlyNeedsReview] = useState(false);

  const [showForm, setShowForm] = useState(false);
  const [batchTitle, setBatchTitle] = useState('');
  const [rows, setRows] = useState<FormRow[]>([EMPTY_ROW(), EMPTY_ROW()]);
  const [submitting, setSubmitting] = useState(false);

  const loadList = useCallback(async () => {
    setLoadingList(true);
    try {
      const res = await listBatchReviews();
      setBatches(res.data);
    } catch { toast(t('error_loading'), 'error'); }
    finally { setLoadingList(false); }
  }, [t]);

  useEffect(() => { loadList(); }, [loadList]);

  const openBatch = async (id: string, filterOverride?: boolean) => {
    setLoadingDetail(true);
    const filt = filterOverride ?? onlyNeedsReview;
    try {
      const res = await getBatchReview(id, filt || undefined);
      setSelected(res.data);
    } catch { toast(t('error_loading'), 'error'); }
    finally { setLoadingDetail(false); }
  };

  const toggleFilter = async () => {
    const next = !onlyNeedsReview;
    setOnlyNeedsReview(next);
    if (selected) await openBatch(selected.id, next);
  };

  const addRow = () => setRows(r => [...r, EMPTY_ROW()]);
  const removeRow = (idx: number) => setRows(r => r.filter((_, i) => i !== idx));
  const updateRow = (idx: number, field: keyof FormRow, value: string) =>
    setRows(r => r.map((row, i) => (i === idx ? { ...row, [field]: value } : row)));

  const handleSubmit = async () => {
    const validRows = rows.filter(r => r.title.trim() && r.text.trim().length >= 10);
    if (!validRows.length) {
      toast(lang === 'ru' ? 'Заполните хотя бы одно ТЗ (текст ≥ 10 символов)' : 'Fill at least one item (text ≥ 10 chars)', 'error');
      return;
    }
    setSubmitting(true);
    try {
      const res = await createBatchReview({
        title: batchTitle || undefined,
        items: validRows.map(r => ({ title: r.title, text: r.text })),
      });
      toast(lang === 'ru' ? `Пакет обработан: ${res.data.completed_count}/${res.data.total_count}` : `Batch processed: ${res.data.completed_count}/${res.data.total_count}`, 'success');
      setShowForm(false);
      setBatchTitle('');
      setRows([EMPTY_ROW(), EMPTY_ROW()]);
      await loadList();
      setSelected(res.data);
    } catch (e: any) {
      toast(e?.response?.data?.detail || t('error_loading'), 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleExportCsv = async (id: string) => {
    try {
      const res = await exportBatchReviewCsv(id);
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a'); a.href = url; a.download = `batch_review_${id.slice(0, 8)}.csv`; a.click();
      URL.revokeObjectURL(url);
    } catch { toast(t('error_loading'), 'error'); }
  };

  return (
    <div>
      <SectionHeader
        title={lang === 'ru' ? 'Пакетная рецензия' : 'Batch Review'}
        subtitle={lang === 'ru'
          ? 'Загрузите сразу несколько ТЗ — каждое пройдёт через тот же ИИ-рецензент, что и одиночная рецензия'
          : 'Upload several TORs at once — each goes through the same AI reviewer as a single review'}
      />

      <div className="flex justify-end mb-4">
        <button className="btn-primary text-sm" onClick={() => setShowForm(s => !s)}>
          {showForm ? '✕ ' + (lang === 'ru' ? 'Отмена' : 'Cancel') : '+ ' + (lang === 'ru' ? 'Новый пакет' : 'New batch')}
        </button>
      </div>

      {showForm && (
        <div className="card mb-6 space-y-4 animate-fade-in">
          <div>
            <label className="label">{lang === 'ru' ? 'Название пакета (необязательно)' : 'Batch title (optional)'}</label>
            <input className="input" value={batchTitle} onChange={e => setBatchTitle(e.target.value)}
              placeholder={lang === 'ru' ? 'Например: ТЗ на спринт 14' : 'e.g. Sprint 14 TORs'} />
          </div>

          <div className="space-y-3">
            {rows.map((row, idx) => (
              <div key={idx} className="p-3 rounded-lg border border-slate-border bg-ink-soft space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <input
                    className="input flex-1 text-sm"
                    placeholder={lang === 'ru' ? `Название ТЗ №${idx + 1}` : `TOR title #${idx + 1}`}
                    value={row.title}
                    onChange={e => updateRow(idx, 'title', e.target.value)}
                  />
                  {rows.length > 1 && (
                    <button className="btn-ghost !py-1 !px-2 text-xs" onClick={() => removeRow(idx)}>✕</button>
                  )}
                </div>
                <textarea
                  className="input text-sm h-24 resize-y w-full"
                  placeholder={lang === 'ru' ? 'Текст ТЗ…' : 'TOR text…'}
                  value={row.text}
                  onChange={e => updateRow(idx, 'text', e.target.value)}
                />
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between">
            <button className="btn-ghost text-xs" onClick={addRow}>+ {lang === 'ru' ? 'Добавить ТЗ' : 'Add TOR'}</button>
            <button className="btn-primary text-sm" onClick={handleSubmit} disabled={submitting}>
              {submitting ? <><Spinner /> {lang === 'ru' ? 'Обрабатываю пакет…' : 'Processing batch…'}</> : (lang === 'ru' ? '▶ Запустить пакетную рецензию' : '▶ Run batch review')}
            </button>
          </div>
          <p className="text-xs text-slate-muted/70">
            {lang === 'ru'
              ? 'Каждый пункт обрабатывается независимо — ошибка в одном ТЗ не остановит остальные.'
              : 'Each item is processed independently — a failure in one TOR does not block the rest.'}
          </p>
        </div>
      )}

      <div className="grid grid-cols-3 gap-5">
        <div className="col-span-1">
          <p className="label mb-3">{lang === 'ru' ? 'Прошлые пакеты' : 'Past batches'}</p>
          {loadingList ? <Spinner /> : batches.length === 0 ? (
            <p className="text-slate-muted text-sm">{lang === 'ru' ? 'Пакетов ещё не было' : 'No batches yet'}</p>
          ) : (
            <div className="space-y-2">
              {batches.map(b => (
                <button key={b.id} onClick={() => openBatch(b.id)}
                  className={`w-full text-left p-3 rounded-lg border transition-all text-sm ${
                    selected?.id === b.id
                      ? 'border-accent/50 bg-accent/10 text-white'
                      : 'border-slate-border text-slate-muted hover:text-white hover:border-slate-border/80 bg-ink-soft'
                  }`}>
                  <p className="font-medium truncate">{b.title || `Batch ${b.id.slice(0, 8)}`}</p>
                  <p className="text-xs opacity-70 mt-1 flex items-center gap-2">
                    <span>{b.completed_count}/{b.total_count}</span>
                    {b.needs_review_count > 0 && <span className="text-yellow-400">⚠ {b.needs_review_count}</span>}
                    {b.error_count > 0 && <span className="text-red-400">✕ {b.error_count}</span>}
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="col-span-2">
          {!selected ? (
            <EmptyState icon="📦" title={lang === 'ru' ? 'Выберите пакет слева' : 'Select a batch on the left'}
              subtitle={lang === 'ru' ? 'или создайте новый через кнопку выше' : 'or create a new one using the button above'} />
          ) : loadingDetail ? (
            <Spinner size="lg" />
          ) : (
            <div className="space-y-4 animate-fade-in">
              <div className="card border-accent/20">
                <div className="flex items-center justify-between mb-3">
                  <p className="font-display font-bold text-white">{selected.title || `Batch ${selected.id.slice(0, 8)}`}</p>
                  <button className="btn-ghost text-xs" onClick={() => handleExportCsv(selected.id)}>⬇ CSV</button>
                </div>
                <div className="grid grid-cols-4 gap-3 text-center">
                  <div><p className="text-xl font-display font-bold text-white">{selected.total_count}</p><p className="text-xs text-slate-muted">{lang === 'ru' ? 'всего' : 'total'}</p></div>
                  <div><p className="text-xl font-display font-bold text-green-400">{selected.completed_count}</p><p className="text-xs text-slate-muted">{lang === 'ru' ? 'обработано' : 'done'}</p></div>
                  <div><p className="text-xl font-display font-bold text-yellow-400">{selected.needs_review_count}</p><p className="text-xs text-slate-muted">{lang === 'ru' ? 'на проверку' : 'needs review'}</p></div>
                  <div><p className="text-xl font-display font-bold text-red-400">{selected.error_count}</p><p className="text-xs text-slate-muted">{lang === 'ru' ? 'ошибок' : 'errors'}</p></div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <label className="flex items-center gap-2 text-sm text-slate-muted cursor-pointer select-none">
                  <input type="checkbox" checked={onlyNeedsReview} onChange={toggleFilter} />
                  {lang === 'ru' ? 'Только «требует проверки»' : 'Only "needs review"'}
                </label>
              </div>

              <div className="space-y-2">
                {selected.items.map(item => (
                  <div key={item.id} className="p-3 rounded-lg border border-slate-border bg-ink-soft flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-white truncate">{item.title}</p>
                      <p className="text-xs text-slate-muted mt-0.5 flex items-center gap-2">
                        {item.status === 'error' ? (
                          <span className="text-red-400">✕ {item.error?.slice(0, 80) || 'error'}</span>
                        ) : (
                          <>
                            {item.confidence && <ConfidenceBadge confidence={item.confidence} />}
                            <NeedsReviewBadge show={item.needs_review} />
                          </>
                        )}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {item.review_id && (
                        <Link to={`/reviews`} className="btn-ghost !py-1 !px-2 text-xs">
                          {lang === 'ru' ? 'Рецензия' : 'Review'}
                        </Link>
                      )}
                      {item.document_id && (
                        <Link to={`/documents/${item.document_id}`} className="btn-ghost !py-1 !px-2 text-xs">
                          {lang === 'ru' ? 'Документ' : 'Document'}
                        </Link>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
