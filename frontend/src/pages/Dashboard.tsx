import React, { useState, useEffect, useCallback } from 'react';
import { getDashboardStats, getRecentActivity } from '../api';
import { SectionHeader, EmptyState, Spinner, toast } from '../components/ui';
import { useI18n } from '../i18n';

interface DashboardStats {
  documents: { total: number };
  reviews: { total: number; needs_review: number; needs_review_pct: number };
  audit: { total_operations: number; avg_duration_ms: number };
  economics: { total_build_projects: number; avg_roi_12m_pct: number; avg_payback_months: number };
}

interface ActivityItem {
  id: string; created_at: string; action: string;
  status: string; duration_ms: number;
}

const ACTION_LABELS: Record<string, string> = {
  review: '🔍 Review / Рецензия',
  direct_review: '🔍 Direct Review',
  ask_kb: '🧠 KB Question',
  direct_answer: '🧠 Direct Answer',
  generate_urs: '📝 URS',
  generate_srs: '📄 SRS',
  generate_adr: '📋 ADR',
  recommend_architecture: '🏛 Architecture',
  design_api: '🔌 API Spec',
  generate_diagrams: '🗺 Diagrams',
  generate_c4: '🗺 C4',
  generate_uml: '🗺 UML',
  generate_erd: '🗺 ERD',
  memory_store: '💾 Memory',
  seed_documents: '🌱 Seed',
};

const STATUS_COLORS: Record<string, string> = {
  ok: 'text-green-400 bg-green-500/10 border-green-500/30',
  error: 'text-red-400 bg-red-500/10 border-red-500/30',
  needs_review: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
};

export default function DashboardPage() {
  const { t, lang } = useI18n();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [statsRes, actRes] = await Promise.all([
        getDashboardStats(),
        getRecentActivity(10),
      ]);
      setStats(statsRes.data);
      setActivity(actRes.data);
    } catch { toast(t('error_loading'), 'error'); }
    finally { setLoading(false); }
  }, [t]);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <SectionHeader
        title={t('dash_title')}
        subtitle={t('dash_subtitle')}
        action={<button onClick={load} className="btn-ghost text-sm">{t('refresh')}</button>}
      />

      {loading && !stats ? (
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      ) : !stats ? (
        <EmptyState icon="📊" title={t('dash_empty')} subtitle={t('dash_empty_sub')} />
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="card">
              <p className="text-xs text-slate-muted uppercase tracking-wider">{t('dash_docs')}</p>
              <p className="font-display text-3xl font-bold text-white mt-1">{stats.documents.total}</p>
            </div>
            <div className="card">
              <p className="text-xs text-slate-muted uppercase tracking-wider">{t('dash_reviews')}</p>
              <p className="font-display text-3xl font-bold text-white mt-1">{stats.reviews.total}</p>
              {stats.reviews.needs_review > 0 && (
                <p className="text-xs text-yellow-400 mt-1">⚠ {stats.reviews.needs_review} {t('needs_review')}</p>
              )}
            </div>
            <div className="card">
              <p className="text-xs text-slate-muted uppercase tracking-wider">{t('dash_audit')}</p>
              <p className="font-display text-3xl font-bold text-white mt-1">{stats.audit.total_operations}</p>
            </div>
            <div className="card">
              <p className="text-xs text-slate-muted uppercase tracking-wider">{t('dash_projects')}</p>
              <p className="font-display text-3xl font-bold text-white mt-1">{stats.economics.total_build_projects}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="card flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-warn-bg flex items-center justify-center text-yellow-400">%</div>
              <div>
                <p className="font-display text-xl font-bold text-white">{stats.reviews.needs_review_pct}%</p>
                <p className="text-xs text-slate-muted">{t('dash_need_review_rate')}</p>
              </div>
            </div>
            <div className="card flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center text-accent">⏱</div>
              <div>
                <p className="font-display text-xl font-bold text-white">{stats.audit.avg_duration_ms} ms</p>
                <p className="text-xs text-slate-muted">{t('dash_avg_duration')}</p>
              </div>
            </div>
          </div>

          <h2 className="font-display text-lg font-bold text-white mb-4">{t('dash_recent')}</h2>

          {activity.length === 0 ? (
            <EmptyState icon="🕐" title={t('dash_no_activity')} subtitle={t('dash_no_activity_sub')} />
          ) : (
            <div className="rounded-xl border border-slate-border overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-ink-muted text-slate-muted text-xs uppercase tracking-wider">
                    <th className="px-4 py-3 text-left">{t('audit_time')}</th>
                    <th className="px-4 py-3 text-left">{t('audit_action')}</th>
                    <th className="px-4 py-3 text-left">{t('audit_status')}</th>
                    <th className="px-4 py-3 text-right">{t('audit_duration')}</th>
                  </tr>
                </thead>
                <tbody>
                  {activity.map((item, i) => (
                    <tr key={item.id} className={`border-t border-slate-border hover:bg-ink-muted/50 ${i % 2 === 0 ? 'bg-ink-soft' : 'bg-ink'}`}>
                      <td className="px-4 py-3 font-mono text-xs text-slate-muted whitespace-nowrap">
                        {new Date(item.created_at).toLocaleString(lang === 'ru' ? 'ru' : 'en', {
                          hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit',
                        })}
                      </td>
                      <td className="px-4 py-3 text-white font-medium">{ACTION_LABELS[item.action] || item.action}</td>
                      <td className="px-4 py-3">
                        <span className={`text-xs font-mono border px-2 py-0.5 rounded ${STATUS_COLORS[item.status] || ''}`}>{item.status}</span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-xs text-slate-muted">{item.duration_ms} ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {stats.economics.total_build_projects > 0 && (
            <div className="grid grid-cols-2 gap-4 mt-6">
              <div className="card flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-green-500/10 flex items-center justify-center text-green-400">%</div>
                <div>
                  <p className="font-display text-xl font-bold text-white">{stats.economics.avg_roi_12m_pct}%</p>
                  <p className="text-xs text-slate-muted">{t('dash_avg_roi')}</p>
                </div>
              </div>
              <div className="card flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-400">⏳</div>
                <div>
                  <p className="font-display text-xl font-bold text-white">{stats.economics.avg_payback_months} {t('dash_months')}</p>
                  <p className="text-xs text-slate-muted">{t('dash_avg_payback')}</p>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
