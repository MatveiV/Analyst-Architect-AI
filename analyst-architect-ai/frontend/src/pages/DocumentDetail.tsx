import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getDocument, reviewDocument, recommendArchitecture, generateADR, designAPI, generateDiagrams, generateURS, generateSRS, getDocumentDiagrams, exportDocx, exportMarkdown } from '../api';
import { SectionHeader, Spinner, NeedsReviewBadge, ConfidenceBadge, SeverityBadge, CopyButton, JsonViewer, Tabs, toast } from '../components/ui';
import ReviewCard from '../components/ReviewCard';
import DiagramViewer from '../components/DiagramViewer';
import MarkdownViewer from '../components/MarkdownViewer';
import { useI18n } from '../i18n';

interface Doc { id: string; title: string; text: string; doc_type: string; project_name?: string; created_at: string; }

export default function DocumentDetail() {
  const { t, lang } = useI18n();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [doc, setDoc] = useState<Doc | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, any>>({});
  const [reasoningMode, setReasoningMode] = useState<'direct' | 'cot' | 'react'>('direct');
  const [diagrams, setDiagrams] = useState<any[]>([]);
  const [tab, setTab] = useState('text');

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [docRes, diagRes] = await Promise.all([getDocument(id), getDocumentDiagrams(id).catch(() => ({ data: [] }))]);
      setDoc(docRes.data); setDiagrams(diagRes.data);
    } catch { toast(t('error_loading'), 'error'); navigate('/'); }
    finally { setLoading(false); }
  }, [id, navigate, t]);

  useEffect(() => { load(); }, [load]);

  const run = async (action: string, fn: () => Promise<any>) => {
    setRunning(action);
    try {
      const res = await fn();
      setResults(p => ({ ...p, [action]: res.data }));
      if (action === 'diagrams') { const d = await getDocumentDiagrams(id!); setDiagrams(d.data); }
    } catch (e: any) { toast(e?.response?.data?.detail || t('error_loading'), 'error'); }
    finally { setRunning(null); }
  };

  const handleExport = async () => {
    try {
      const res = await exportDocx(id!);
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a'); a.href = url; a.download = `${doc?.title?.slice(0,30) || 'doc'}.docx`; a.click(); URL.revokeObjectURL(url);
    } catch { toast(t('error_loading'), 'error'); }
  };

  const handleExportFinal = async () => {
    try {
      const res = await exportMarkdown(id!);
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a'); a.href = url; a.download = `${doc?.title?.slice(0,30) || 'doc'}_final.md`; a.click(); URL.revokeObjectURL(url);
      toast('Итоговый документ создан', 'success');
    } catch { toast(t('error_loading'), 'error'); }
  };

  const ACTIONS = [
    { key: 'review',    icon: '🔍', labelKey: 'doc_review_btn' as const, fn: () => reviewDocument(id!, reasoningMode) },
    { key: 'urs',       icon: '📝', labelKey: 'studio_urs_btn'  as const, fn: () => generateURS(id!, doc?.project_name) },
    { key: 'srs',       icon: '📄', labelKey: 'studio_srs_btn'  as const, fn: () => generateSRS(id!, doc?.project_name) },
    { key: 'arch',      icon: '🏛', labelKey: 'studio_arch_btn' as const, fn: () => recommendArchitecture(id!, doc?.project_name) },
    { key: 'adr',       icon: '📋', labelKey: 'studio_adr_btn'  as const, fn: () => generateADR(id!, doc?.project_name) },
    { key: 'api',       icon: '🔌', labelKey: 'studio_api_btn'  as const, fn: () => designAPI(id!, doc?.project_name) },
    { key: 'diagrams',  icon: '🗺', labelKey: 'studio_diag_btn' as const, fn: () => generateDiagrams(id!, doc?.project_name) },
  ];

  const TABS = [
    { key: 'text',     label: t('det_tab_text') },
    { key: 'review',   label: t('det_tab_review') },
    { key: 'arch',     label: t('det_tab_arch') },
    { key: 'adr',      label: t('det_tab_adr') },
    { key: 'api',      label: t('det_tab_api') },
    { key: 'diagrams', label: t('det_tab_diag') },
    { key: 'specs',    label: t('det_tab_specs') },
  ];

  if (loading) return <div className="flex justify-center items-center h-64"><Spinner size="lg" /></div>;
  if (!doc) return null;

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <button onClick={() => navigate('/')} className="text-slate-muted hover:text-white text-sm mb-2 flex items-center gap-1">
            {t('det_back')}
          </button>
          <h1 className="font-display text-2xl font-bold text-white">{doc.title}</h1>
          <div className="flex items-center gap-3 mt-1 text-xs text-slate-muted">
            <span className="font-mono bg-ink-muted px-2 py-0.5 rounded">{doc.doc_type}</span>
            {doc.project_name && <span>📁 {doc.project_name}</span>}
            <span>{new Date(doc.created_at).toLocaleDateString(lang === 'ru' ? 'ru' : 'en')}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button className="btn-ghost text-sm" onClick={handleExportFinal}>📄 Итоговый MD</button>
          <button className="btn-ghost text-sm" onClick={handleExport}>⬇ DOCX</button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-6 p-4 bg-ink-soft rounded-xl border border-slate-border">
        <span className="text-xs text-slate-muted self-center mr-2">{t('det_run')}</span>
        <div className="flex items-center gap-1 self-center mr-2 bg-ink-muted rounded-full px-1 py-0.5 border border-slate-border/50">
          {(['direct', 'cot', 'react'] as const).map(m => (
            <button key={m}
              onClick={() => setReasoningMode(m)}
              className={`text-xs px-2.5 py-1 rounded-full transition-colors ${
                reasoningMode === m
                  ? 'bg-accent/20 text-accent-light border border-accent/40'
                  : 'text-slate-muted hover:text-white'
              }`}>
              {m === 'direct' ? 'Direct' : m === 'cot' ? '🧠 CoT' : '🔄 ReAct'}
            </button>
          ))}
        </div>
        {ACTIONS.map(a => (
          <button key={a.key} disabled={running === a.key}
            onClick={() => { run(a.key, a.fn); setTab(a.key); }}
            className={`btn-primary text-xs px-3 py-1.5 ${running === a.key ? 'opacity-70' : ''}`}>
            {running === a.key ? <Spinner /> : a.icon} {t(a.labelKey)}
          </button>
        ))}
      </div>

      <div className="mb-5 overflow-x-auto"><Tabs tabs={TABS} active={tab} onChange={setTab} /></div>

      {tab === 'text' && (
        <div className="card">
          <div className="flex justify-between items-center mb-3">
            <p className="label">{t('det_source')}</p><CopyButton text={doc.text} />
          </div>
          {doc.doc_type === 'markdown' ? (
            <MarkdownViewer text={doc.text} className="max-h-[600px] overflow-y-auto" />
          ) : (
            <pre className="whitespace-pre-wrap font-mono text-sm text-white/80 leading-relaxed max-h-[600px] overflow-y-auto">{doc.text}</pre>
          )}
          <p className="text-xs text-slate-muted mt-3">{doc.text.length} {t('doc_chars')}</p>
        </div>
      )}

      {tab === 'review' && (
        <div>
          {running === 'review' && (
            <div className="card border-accent/30 bg-accent-glow flex items-center gap-3 mb-4">
              <Spinner size="md" /><span className="text-accent-light text-sm">{t('det_analyzing')} <span className="text-xs text-accent/70">({reasoningMode.toUpperCase()})</span></span>
            </div>
          )}
          {results.review ? (
            <ReviewCard reviewId={results.review.id || 'direct'}
              reviewJson={results.review.review_json || JSON.stringify(results.review)}
              needsReview={results.review.needs_review} confidence={results.review.confidence}
              documentTitle={doc.title} />
          ) : <EmptyPrompt icon="🔍" label={t('det_run_review')} />}
        </div>
      )}

      {tab === 'arch' && (
        <div>
          {running === 'arch' && <div className="card border-accent/30 bg-accent-glow flex items-center gap-3 mb-4"><Spinner size="md" /><span className="text-accent-light text-sm">{t('studio_analyzing')}</span></div>}
          {results.arch ? <ArchCard data={results.arch} t={t} /> : <EmptyPrompt icon="🏛" label={t('det_run_arch')} />}
        </div>
      )}

      {tab === 'adr' && (
        <div>{results.adr ? <ADRCard data={results.adr} t={t} /> : <EmptyPrompt icon="📋" label={t('det_run_gen')} />}</div>
      )}

      {tab === 'api' && (
        <div>
          {results.api ? (
            <div className="card space-y-3">
              <div className="flex items-center justify-between">
                <p className="font-display font-bold">OpenAPI 3.1</p>
                <div className="flex gap-2">
                  <CopyButton text={results.api.openapi_json} label="JSON" />
                  <CopyButton text={results.api.openapi_yaml} label="YAML" />
                </div>
              </div>
              <button className="btn-ghost text-xs" onClick={() => window.open('https://editor.swagger.io/', '_blank')}>
                {t('det_swagger')}
              </button>
              <pre className="code-block text-xs max-h-[500px] overflow-auto">{results.api.openapi_json}</pre>
            </div>
          ) : <EmptyPrompt icon="🔌" label={t('det_run_gen')} />}
        </div>
      )}

      {tab === 'diagrams' && (
        <div>
          {running === 'diagrams' && <div className="card border-accent/30 bg-accent-glow flex items-center gap-3 mb-4"><Spinner size="md" /><span className="text-accent-light text-sm">{t('studio_generating')}</span></div>}
          <div className="card"><DiagramViewer diagrams={diagrams} /></div>
        </div>
      )}

      {tab === 'specs' && (
        <div className="space-y-4">
          {results.urs && (
            <div className="card animate-fade-in">
              <div className="flex items-center justify-between mb-3">
                <p className="font-display font-bold">URS — {results.urs.title}</p>
                <NeedsReviewBadge show={results.urs.needs_review} />
              </div>
              <JsonViewer data={results.urs} />
            </div>
          )}
          {results.srs && (
            <div className="card animate-fade-in">
              <div className="flex items-center justify-between mb-3">
                <p className="font-display font-bold">SRS — {results.srs.title}</p>
                <NeedsReviewBadge show={results.srs.needs_review} />
              </div>
              <JsonViewer data={results.srs} />
            </div>
          )}
          {!results.urs && !results.srs && <EmptyPrompt icon="📝" label={t('det_run_gen')} />}
        </div>
      )}
    </div>
  );
}

function EmptyPrompt({ icon, label }: { icon: string; label: string }) {
  return (
    <div className="text-center py-16 text-slate-muted">
      <p className="text-4xl mb-3">{icon}</p><p>{label}</p>
    </div>
  );
}

function ArchCard({ data, t }: { data: any; t: (k: any) => string }) {
  const rec = data.recommendation_json ? JSON.parse(data.recommendation_json) : data;
  return (
    <div className="card space-y-5 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <p className="label">{t('studio_pattern')}</p>
          <p className="font-display text-3xl font-bold text-accent">{rec.recommended_pattern}</p>
        </div>
        <div className="flex gap-2">
          <ConfidenceBadge confidence={rec.confidence || 'medium'} />
          <NeedsReviewBadge show={rec.needs_review || data.needs_review} />
        </div>
      </div>
      <div><p className="label">{t('studio_rationale')}</p><p className="text-white/80 leading-relaxed">{rec.rationale}</p></div>
      {rec.integration_recommendations?.length > 0 && (
        <div>
          <p className="label">{t('det_integrations')}</p>
          <div className="flex flex-wrap gap-2">
            {rec.integration_recommendations.map((r: string, i: number) => (
              <span key={i} className="bg-ink-muted text-slate-muted border border-slate-border px-3 py-1 rounded-full text-xs font-mono">{r}</span>
            ))}
          </div>
        </div>
      )}
      {rec.alternatives?.length > 0 && (
        <div>
          <p className="label">{t('studio_alts')}</p>
          {rec.alternatives.map((alt: any, i: number) => (
            <div key={i} className="p-4 bg-ink rounded-xl border border-slate-border mb-2">
              <p className="font-medium text-white mb-2">{alt.pattern}</p>
              <div className="grid grid-cols-2 gap-3">
                <div>{alt.pros?.map((p: string, j: number) => <p key={j} className="text-green-400 text-xs flex gap-1"><span>+</span>{p}</p>)}</div>
                <div>{alt.cons?.map((c: string, j: number) => <p key={j} className="text-red-400 text-xs flex gap-1"><span>−</span>{c}</p>)}</div>
              </div>
            </div>
          ))}
        </div>
      )}
      {rec.risks?.length > 0 && (
        <div>
          <p className="label">{t('det_arch_risks')}</p>
          {rec.risks.map((r: any, i: number) => (
            <div key={i} className="flex gap-3 items-start p-3 bg-ink rounded-lg border border-slate-border/60 mb-2">
              <SeverityBadge severity={r.severity} /><p className="text-sm text-white/80">{r.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ADRCard({ data, t }: { data: any; t: (k: any) => string }) {
  const adr = data.adr_json ? JSON.parse(data.adr_json) : data;
  return (
    <div className="card space-y-4 animate-fade-in">
      <div className="flex items-center gap-3">
        <p className="font-display font-bold text-white text-lg">{adr.title}</p>
        <span className="text-xs font-mono border border-slate-border bg-ink-muted px-2 py-0.5 rounded">{adr.status}</span>
        <NeedsReviewBadge show={adr.needs_review} />
      </div>
      {[['det_context', adr.context], ['det_problem', adr.problem], ['det_decision', adr.decision]].map(([lk, v]) => (
        <div key={lk as string}>
          <p className="label">{t(lk as any)}</p>
          <p className="text-white/80 text-sm leading-relaxed bg-ink rounded-lg p-3 border border-slate-border/60">{v as string}</p>
        </div>
      ))}
      {adr.alternatives?.length > 0 && (
        <div>
          <p className="label">{t('det_rejected')}</p>
          {adr.alternatives.map((a: any, i: number) => (
            <div key={i} className="p-3 bg-ink rounded-lg border border-slate-border text-sm border-l-2 border-l-red-500/40 mb-2">
              <p className="text-white font-medium">{a.option}</p>
              <p className="text-red-400/70 text-xs mt-1">{a.reason_rejected}</p>
            </div>
          ))}
        </div>
      )}
      {adr.consequences && (
        <div className="grid grid-cols-2 gap-4">
          <div><p className="label">{t('det_positive')}</p>{adr.consequences.positive?.map((p: string, i: number) => <p key={i} className="text-green-400 text-sm flex gap-1.5 mb-1"><span>✓</span>{p}</p>)}</div>
          <div><p className="label">{t('det_negative')}</p>{adr.consequences.negative?.map((n: string, i: number) => <p key={i} className="text-red-400 text-sm flex gap-1.5 mb-1"><span>✗</span>{n}</p>)}</div>
        </div>
      )}
    </div>
  );
}
