import React, { useState, useEffect, useCallback } from 'react';
import { listReviews, listDocuments, diffReviews } from '../api';
import { SectionHeader, EmptyState, Spinner, NeedsReviewBadge, ConfidenceBadge, toast } from '../components/ui';
import ReviewCard from '../components/ReviewCard';
import { useI18n } from '../i18n';

interface Review { id: string; document_id: string; review_json: string; needs_review: boolean; confidence: string; created_at: string; error?: string; }
interface Doc { id: string; title: string; }
interface ReviewDiff {
  from_review_id: string; to_review_id: string;
  confidence_changed: boolean; confidence_from: string; confidence_to: string;
  needs_review_changed: boolean; needs_review_from: boolean; needs_review_to: boolean;
  summary_diff_lines: string[];
  risks_added: string[]; risks_removed: string[];
  acceptance_criteria_added: string[]; acceptance_criteria_removed: string[];
  missing_requirements_added: string[]; missing_requirements_removed: string[];
}

export default function ReviewsPage() {
  const { t, lang } = useI18n();
  const [reviews, setReviews] = useState<Review[]>([]);
  const [docs, setDocs] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<boolean | undefined>(undefined);
  const [expanded, setExpanded] = useState<string | null>(null);
  // Фаза 2: сравнение двух рецензий одного документа
  const [compareMode, setCompareMode] = useState(false);
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);
  const [diff, setDiff] = useState<ReviewDiff | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [revRes, docRes] = await Promise.all([listReviews(filter), listDocuments()]);
      setReviews(revRes.data);
      const map: Record<string, string> = {};
      docRes.data.forEach((d: Doc) => { map[d.id] = d.title; });
      setDocs(map);
    } catch { toast(t('error_loading'), 'error'); }
    finally { setLoading(false); }
  }, [filter, t]);

  useEffect(() => { load(); }, [load]);

  const toggleCompareSelect = (id: string) => {
    setSelectedForCompare(prev => {
      if (prev.includes(id)) return prev.filter(x => x !== id);
      if (prev.length >= 2) return [prev[1], id]; // держим максимум 2, сдвигаем окно
      return [...prev, id];
    });
    setDiff(null);
  };

  const runDiff = async () => {
    if (selectedForCompare.length !== 2) return;
    setDiffLoading(true);
    try {
      // Сравниваем в хронологическом порядке (старая -> новая), а не в порядке клика
      const [a, b] = selectedForCompare;
      const revA = reviews.find(r => r.id === a)!;
      const revB = reviews.find(r => r.id === b)!;
      const [fromRev, toRev] = new Date(revA.created_at) <= new Date(revB.created_at) ? [revA, revB] : [revB, revA];
      const res = await diffReviews(fromRev.id, toRev.id);
      setDiff(res.data);
    } catch { toast(t('error_loading'), 'error'); }
    finally { setDiffLoading(false); }
  };

  const filters = [
    { label: t('rev_filter_all'), value: undefined },
    { label: t('rev_filter_ok'),  value: false },
    { label: t('rev_filter_nr'),  value: true },
  ];

  return (
    <div>
      <SectionHeader title={t('rev_title')} subtitle={t('rev_subtitle')} />

      <div className="flex gap-2 mb-6 items-center flex-wrap">
        {filters.map(f => (
          <button key={String(f.value)}
            onClick={() => setFilter(f.value)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              filter === f.value
                ? 'bg-accent/20 text-accent border border-accent/30'
                : 'text-slate-muted border border-slate-border hover:text-white'
            }`}>
            {f.label}
          </button>
        ))}
        <button
          onClick={() => { setCompareMode(c => !c); setSelectedForCompare([]); setDiff(null); }}
          className={`ml-auto px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            compareMode ? 'bg-accent/20 text-accent border border-accent/30' : 'text-slate-muted border border-slate-border hover:text-white'
          }`}>
          🔀 {lang === 'ru' ? 'Сравнить рецензии' : 'Compare reviews'}
        </button>
      </div>

      {compareMode && (
        <div className="card mb-6 border-accent/20">
          <p className="text-xs text-slate-muted mb-2">
            {lang === 'ru'
              ? 'Отметьте две рецензии (лучше — одного документа: до/после обновлённого ТЗ) и нажмите «Сравнить».'
              : 'Pick two reviews (ideally of the same document: before/after an updated TOR) and click "Compare".'}
          </p>
          <button className="btn-primary text-xs" onClick={runDiff} disabled={selectedForCompare.length !== 2 || diffLoading}>
            {diffLoading ? <Spinner /> : `🔀 ${lang === 'ru' ? 'Сравнить' : 'Compare'} (${selectedForCompare.length}/2)`}
          </button>

          {diff && (
            <div className="mt-4 space-y-3 animate-fade-in border-t border-slate-border/60 pt-4">
              <div className="flex flex-wrap gap-4 text-sm">
                {diff.confidence_changed && (
                  <p className="text-slate-muted">Confidence: <span className="text-white">{diff.confidence_from}</span> → <span className="text-accent">{diff.confidence_to}</span></p>
                )}
                {diff.needs_review_changed && (
                  <p className="text-slate-muted">
                    needs_review: <span className="text-white">{String(diff.needs_review_from)}</span> → <span className={diff.needs_review_to ? 'text-yellow-400' : 'text-green-400'}>{String(diff.needs_review_to)}</span>
                  </p>
                )}
                {!diff.confidence_changed && !diff.needs_review_changed && (
                  <p className="text-slate-muted">{lang === 'ru' ? 'Confidence и needs_review не изменились' : 'Confidence and needs_review unchanged'}</p>
                )}
              </div>

              {diff.summary_diff_lines.length > 0 && (
                <div>
                  <p className="label text-xs mb-1">{lang === 'ru' ? 'Изменения в резюме' : 'Summary changes'}</p>
                  <pre className="code-block text-xs leading-relaxed max-h-48 overflow-auto">
                    {diff.summary_diff_lines.map((l, i) => (
                      <div key={i} className={l.startsWith('+') ? 'text-green-400' : l.startsWith('-') ? 'text-red-400' : 'text-slate-muted'}>{l}</div>
                    ))}
                  </pre>
                </div>
              )}

              {[
                ['risks_added', diff.risks_added, lang === 'ru' ? 'Новые риски' : 'Risks added', 'text-red-400'],
                ['risks_removed', diff.risks_removed, lang === 'ru' ? 'Снятые риски' : 'Risks removed', 'text-green-400'],
                ['ac_added', diff.acceptance_criteria_added, lang === 'ru' ? 'Новые критерии приёмки' : 'Acceptance criteria added', 'text-green-400'],
                ['ac_removed', diff.acceptance_criteria_removed, lang === 'ru' ? 'Убранные критерии приёмки' : 'Acceptance criteria removed', 'text-red-400'],
                ['mr_added', diff.missing_requirements_added, lang === 'ru' ? 'Новые пробелы' : 'New gaps', 'text-yellow-400'],
                ['mr_removed', diff.missing_requirements_removed, lang === 'ru' ? 'Закрытые пробелы' : 'Closed gaps', 'text-green-400'],
              ].map(([key, list, label, cls]) => (
                Array.isArray(list) && list.length > 0 && (
                  <div key={key as string}>
                    <p className={`text-xs font-medium mb-1 ${cls}`}>{label as string}</p>
                    <ul className="text-xs text-slate-muted space-y-0.5 list-disc list-inside">
                      {(list as string[]).map((x, i) => <li key={i}>{x}</li>)}
                    </ul>
                  </div>
                )
              ))}
            </div>
          )}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      ) : reviews.length === 0 ? (
        <EmptyState icon="🔍" title={t('rev_empty')} subtitle={t('rev_empty_sub')} />
      ) : (
        <div className="space-y-3">
          {reviews.map(rev => (
            <div key={rev.id}>
              {expanded !== rev.id ? (
                <div className="card card-hover cursor-pointer flex items-center gap-4"
                  onClick={() => compareMode ? toggleCompareSelect(rev.id) : setExpanded(rev.id)}>
                  {compareMode && (
                    <input type="checkbox" checked={selectedForCompare.includes(rev.id)}
                      onChange={() => toggleCompareSelect(rev.id)} onClick={e => e.stopPropagation()}
                      className="shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-muted truncate mb-1">
                      {docs[rev.document_id] || rev.document_id.slice(0, 8)}
                    </p>
                    <p className="text-white text-sm truncate">
                      {(() => { try { return JSON.parse(rev.review_json).summary?.slice(0, 120) || '—'; } catch { return '—'; } })()}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <ConfidenceBadge confidence={rev.confidence} />
                    <NeedsReviewBadge show={rev.needs_review} />
                    <span className="text-xs text-slate-muted">{new Date(rev.created_at).toLocaleDateString(lang === 'ru' ? 'ru' : 'en')}</span>
                    <span className="text-slate-muted text-lg">›</span>
                  </div>
                </div>
              ) : (
                <div className="space-y-2 animate-fade-in">
                  <button onClick={() => setExpanded(null)} className="text-sm text-slate-muted hover:text-white flex items-center gap-1">
                    {t('rev_collapse')}
                  </button>
                  <ReviewCard reviewId={rev.id} reviewJson={rev.review_json}
                    needsReview={rev.needs_review} confidence={rev.confidence}
                    documentTitle={docs[rev.document_id]} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
