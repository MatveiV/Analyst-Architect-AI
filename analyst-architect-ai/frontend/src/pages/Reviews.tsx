import React, { useState, useEffect, useCallback } from 'react';
import { listReviews, listDocuments } from '../api';
import { SectionHeader, EmptyState, Spinner, NeedsReviewBadge, ConfidenceBadge, toast } from '../components/ui';
import ReviewCard from '../components/ReviewCard';
import { useI18n } from '../i18n';

interface Review { id: string; document_id: string; review_json: string; needs_review: boolean; confidence: string; created_at: string; error?: string; }
interface Doc { id: string; title: string; }

export default function ReviewsPage() {
  const { t, lang } = useI18n();
  const [reviews, setReviews] = useState<Review[]>([]);
  const [docs, setDocs] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<boolean | undefined>(undefined);
  const [expanded, setExpanded] = useState<string | null>(null);

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

  const filters = [
    { label: t('rev_filter_all'), value: undefined },
    { label: t('rev_filter_ok'),  value: false },
    { label: t('rev_filter_nr'),  value: true },
  ];

  return (
    <div>
      <SectionHeader title={t('rev_title')} subtitle={t('rev_subtitle')} />

      <div className="flex gap-2 mb-6">
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
      </div>

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
                  onClick={() => setExpanded(rev.id)}>
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
