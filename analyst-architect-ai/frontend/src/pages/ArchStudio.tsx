import React, { useState, useEffect, useCallback } from 'react';
import { listDocuments, recommendArchitecture, generateADR, designAPI, generateDiagrams, generateURS, generateSRS, getDocumentDiagrams, exportDocx } from '../api';
import { SectionHeader, EmptyState, Spinner, NeedsReviewBadge, Tabs, SeverityBadge, CopyButton, JsonViewer, toast } from '../components/ui';
import DiagramViewer from '../components/DiagramViewer';
import { useI18n } from '../i18n';

interface Doc { id: string; title: string; doc_type: string; }

export default function ArchStudioPage() {
  const { t } = useI18n();
  const [docs, setDocs] = useState<Doc[]>([]);
  const [selected, setSelected] = useState<Doc | null>(null);
  const [tab, setTab] = useState('arch');
  const [loading, setLoading] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, any>>({});
  const [diagrams, setDiagrams] = useState<any[]>([]);

  useEffect(() => { listDocuments().then(r => setDocs(r.data)).catch(() => {}); }, []);

  const selectDoc = useCallback(async (doc: Doc) => {
    setSelected(doc); setResults({});
    try { const d = await getDocumentDiagrams(doc.id); setDiagrams(d.data); }
    catch { setDiagrams([]); }
  }, []);

  const run = async (action: string, fn: () => Promise<any>) => {
    setLoading(action);
    try {
      const res = await fn();
      setResults(p => ({ ...p, [action]: res.data }));
      toast(`${action} OK`, 'success');
    } catch (e: any) {
      toast(e?.response?.data?.detail || t('error_loading'), 'error');
    } finally { setLoading(null); }
  };

  const handleDiagrams = async () => {
    if (!selected) return;
    await run('diagrams', () => generateDiagrams(selected.id));
    try { const d = await getDocumentDiagrams(selected.id); setDiagrams(d.data); } catch {}
  };

  const handleExportDocx = async () => {
    if (!selected) return;
    try {
      const res = await exportDocx(selected.id);
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a'); a.href = url; a.download = `${selected.title.slice(0,30)}.docx`; a.click();
      URL.revokeObjectURL(url);
    } catch { toast(t('error_loading'), 'error'); }
  };

  const TABS = [
    { key: 'arch',     label: `🏛 ${t('nav_studio').split(' ')[0]}` },
    { key: 'adr',      label: '📋 ADR' },
    { key: 'api',      label: '🔌 API' },
    { key: 'diagrams', label: '🗺' },
    { key: 'urs',      label: '📝 URS/SRS' },
  ];

  return (
    <div>
      <SectionHeader title={t('studio_title')} subtitle={t('studio_subtitle')} />
      <div className="grid grid-cols-3 gap-5">
        <div className="col-span-1">
          <p className="label mb-3">{t('studio_select')}</p>
          {docs.length === 0 ? <p className="text-slate-muted text-sm">{t('studio_none')}</p> : (
            <div className="space-y-2">
              {docs.filter(d => d.doc_type !== 'kb_article').map(doc => (
                <button key={doc.id} onClick={() => selectDoc(doc)}
                  className={`w-full text-left p-3 rounded-lg border transition-all text-sm ${
                    selected?.id === doc.id
                      ? 'border-accent/50 bg-accent/10 text-white'
                      : 'border-slate-border text-slate-muted hover:text-white hover:border-slate-border/80 bg-ink-soft'
                  }`}>
                  <p className="font-medium truncate">{doc.title}</p>
                  <p className="text-xs opacity-60 mt-0.5 font-mono">{doc.doc_type}</p>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="col-span-2">
          {!selected ? (
            <EmptyState icon="🏛️" title={t('studio_empty')} subtitle={t('studio_empty_sub')} />
          ) : (
            <div className="space-y-5">
              <div className="card border-accent/20 flex items-center justify-between">
                <div>
                  <p className="font-display font-bold text-white">{selected.title}</p>
                  <p className="text-xs text-slate-muted mt-0.5 font-mono">{selected.doc_type}</p>
                </div>
                <button className="btn-ghost text-xs" onClick={handleExportDocx}>⬇ DOCX</button>
              </div>

              <Tabs tabs={TABS} active={tab} onChange={setTab} />

              {tab === 'arch' && (
                <div className="space-y-4">
                  <button className="btn-primary"
                    onClick={() => run('arch', () => recommendArchitecture(selected.id))}
                    disabled={loading === 'arch'}>
                    {loading === 'arch' ? <><Spinner /> {t('studio_analyzing')}</> : t('studio_arch_btn')}
                  </button>
                  {results.arch && <ArchResult data={results.arch} t={t} />}
                </div>
              )}
              {tab === 'adr' && (
                <div className="space-y-4">
                  <button className="btn-primary"
                    onClick={() => run('adr', () => generateADR(selected.id))}
                    disabled={loading === 'adr'}>
                    {loading === 'adr' ? <><Spinner /> {t('loading')}</> : t('studio_adr_btn')}
                  </button>
                  {results.adr && <ADRResult data={results.adr.adr_json ? JSON.parse(results.adr.adr_json) : results.adr} t={t} />}
                </div>
              )}
              {tab === 'api' && (
                <div className="space-y-4">
                  <button className="btn-primary"
                    onClick={() => run('api', () => designAPI(selected.id))}
                    disabled={loading === 'api'}>
                    {loading === 'api' ? <><Spinner /> {t('loading')}</> : t('studio_api_btn')}
                  </button>
                  {results.api && (
                    <div className="space-y-3">
                      <div className="relative">
                        <pre className="code-block text-xs max-h-[400px] overflow-auto">{results.api.openapi_json}</pre>
                        <div className="absolute top-2 right-2 flex gap-1">
                          <CopyButton text={results.api.openapi_json} label="JSON" />
                          <CopyButton text={results.api.openapi_yaml} label="YAML" />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
              {tab === 'diagrams' && (
                <div className="space-y-4">
                  <button className="btn-primary" onClick={handleDiagrams} disabled={loading === 'diagrams'}>
                    {loading === 'diagrams' ? <><Spinner /> {t('studio_generating')}</> : t('studio_diag_btn')}
                  </button>
                  <DiagramViewer diagrams={diagrams} />
                </div>
              )}
              {tab === 'urs' && (
                <div className="space-y-4">
                  <div className="flex gap-3">
                    <button className="btn-primary" onClick={() => run('urs', () => generateURS(selected.id))} disabled={!!loading}>
                      {loading === 'urs' ? <Spinner /> : t('studio_urs_btn')}
                    </button>
                    <button className="btn-ghost" onClick={() => run('srs', () => generateSRS(selected.id))} disabled={!!loading}>
                      {loading === 'srs' ? <Spinner /> : t('studio_srs_btn')}
                    </button>
                  </div>
                  {results.urs && <div className="card"><div className="flex items-center justify-between mb-3"><p className="font-display font-bold">{results.urs.title}</p><NeedsReviewBadge show={results.urs.needs_review} /></div><JsonViewer data={results.urs} /></div>}
                  {results.srs && <div className="card"><div className="flex items-center justify-between mb-3"><p className="font-display font-bold">{results.srs.title}</p><NeedsReviewBadge show={results.srs.needs_review} /></div><JsonViewer data={results.srs} /></div>}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ArchResult({ data, t }: { data: any; t: (k: any) => string }) {
  const rec = data.recommendation_json ? JSON.parse(data.recommendation_json) : data;
  return (
    <div className="card space-y-4 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <p className="label">{t('studio_pattern')}</p>
          <p className="font-display text-2xl font-bold text-accent">{rec.recommended_pattern}</p>
        </div>
        <NeedsReviewBadge show={rec.needs_review || data.needs_review} />
      </div>
      <div><p className="label">{t('studio_rationale')}</p><p className="text-white/80 text-sm leading-relaxed">{rec.rationale}</p></div>
      {rec.alternatives?.length > 0 && (
        <div>
          <p className="label">{t('studio_alts')}</p>
          {rec.alternatives.map((alt: any, i: number) => (
            <div key={i} className="p-3 bg-ink rounded-lg border border-slate-border text-sm mb-2">
              <p className="font-medium text-white">{alt.pattern}</p>
              <div className="grid grid-cols-2 gap-3 mt-2">
                <div>{alt.pros?.map((p: string, j: number) => <p key={j} className="text-green-400 text-xs">+ {p}</p>)}</div>
                <div>{alt.cons?.map((c: string, j: number) => <p key={j} className="text-red-400 text-xs">− {c}</p>)}</div>
              </div>
            </div>
          ))}
        </div>
      )}
      {rec.risks?.length > 0 && (
        <div>
          {rec.risks.map((r: any, i: number) => (
            <div key={i} className="flex gap-3 p-2 rounded text-sm">
              <SeverityBadge severity={r.severity} /><p className="text-white/80">{r.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ADRResult({ data, t }: { data: any; t: (k: any) => string }) {
  return (
    <div className="card space-y-3 animate-fade-in">
      <div className="flex items-center gap-3">
        <p className="font-display font-bold text-white">{data.title}</p>
        <span className="text-xs font-mono bg-ink-muted px-2 py-0.5 rounded border border-slate-border">{data.status}</span>
        <NeedsReviewBadge show={data.needs_review} />
      </div>
      {[['det_context', data.context], ['det_problem', data.problem], ['det_decision', data.decision]].map(([lk, v]) => (
        <div key={lk as string}><p className="label">{t(lk as any)}</p><p className="text-white/80 text-sm">{v as string}</p></div>
      ))}
      {data.consequences && (
        <div className="grid grid-cols-2 gap-4">
          <div><p className="label">{t('det_positive')}</p>{data.consequences.positive?.map((p: string, i: number) => <p key={i} className="text-green-400 text-xs">✓ {p}</p>)}</div>
          <div><p className="label">{t('det_negative')}</p>{data.consequences.negative?.map((n: string, i: number) => <p key={i} className="text-red-400 text-xs">✗ {n}</p>)}</div>
        </div>
      )}
    </div>
  );
}
