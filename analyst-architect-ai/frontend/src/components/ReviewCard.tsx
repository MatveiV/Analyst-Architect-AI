import React, { useState } from 'react';
import { NeedsReviewBadge, SeverityBadge, ConfidenceBadge, CopyButton, JsonViewer } from './ui';
import { exportReviewJson, exportReviewCsv } from '../api';
import { useI18n } from '../i18n';

interface Risk { severity: string; description: string; }
interface ReviewData {
  summary: string; risks: Risk[]; missing_requirements: string[];
  questions_to_client: string[]; acceptance_criteria: string[];
  architecture_risks: string[]; lessons_learned: string[];
  confidence: string; needs_review: boolean;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

export default function ReviewCard({ reviewId, reviewJson, needsReview, confidence, documentTitle }:
  { reviewId: string; reviewJson: string; needsReview: boolean; confidence: string; documentTitle?: string; }) {
  const { t } = useI18n();
  const [showJson, setShowJson] = useState(false);
  const data: ReviewData = React.useMemo(() => {
    try { return JSON.parse(reviewJson); } catch { return {} as any; }
  }, [reviewJson]);

  const handleExportJson = async () => {
    const res = await exportReviewJson(reviewId);
    downloadBlob(res.data, `review_${reviewId.slice(0,8)}.json`);
  };
  const handleExportCsv = async () => {
    const res = await exportReviewCsv(reviewId);
    downloadBlob(res.data, `review_${reviewId.slice(0,8)}.csv`);
  };

  const Section = ({ title, items }: { title: string; items?: string[] }) =>
    items && items.length > 0 ? (
      <div className="mb-5">
        <p className="label">{title}</p>
        <ul className="space-y-1.5">
          {items.map((it, i) => (
            <li key={i} className="text-sm text-white/80 flex items-start gap-2">
              <span className="text-accent mt-0.5 shrink-0">›</span>{it}
            </li>
          ))}
        </ul>
      </div>
    ) : null;

  return (
    <div className="card animate-fade-in space-y-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          {documentTitle && <p className="text-xs text-slate-muted mb-1">{documentTitle}</p>}
          <p className="text-white font-medium leading-snug">{data.summary || '—'}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <ConfidenceBadge confidence={confidence} />
          <NeedsReviewBadge show={needsReview} />
        </div>
      </div>

      {data.risks?.length > 0 && (
        <div>
          <p className="label">{t('rev_risks')} ({data.risks.length})</p>
          <div className="space-y-2">
            {data.risks.map((r, i) => (
              <div key={i} className="flex items-start gap-3 p-3 bg-ink rounded-lg border border-slate-border/60">
                <SeverityBadge severity={r.severity} />
                <p className="text-sm text-white/80 flex-1">{r.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <Section title={t('rev_questions')} items={data.questions_to_client} />
      <Section title={t('rev_criteria')} items={data.acceptance_criteria} />
      <Section title={t('rev_missing')} items={data.missing_requirements} />
      <Section title={t('rev_arch_risks')} items={data.architecture_risks} />
      <Section title={t('rev_lessons')} items={data.lessons_learned} />

      <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-border">
        <button onClick={handleExportJson} className="btn-ghost text-xs">⬇ JSON</button>
        <button onClick={handleExportCsv} className="btn-ghost text-xs">⬇ CSV</button>
        <button onClick={() => setShowJson(v => !v)} className="btn-ghost text-xs">
          {showJson ? `▲ ${t('close')}` : '{ } JSON'}
        </button>
      </div>

      {showJson && <JsonViewer data={data} />}
    </div>
  );
}
