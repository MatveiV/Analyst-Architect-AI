import React, { useEffect, useRef, useState } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { oneDark } from '@codemirror/theme-one-dark';
import { EditorView } from '@codemirror/view';
import { CopyButton, toast } from './ui';
import { updateDiagram, getDiagramVersions, rollbackDiagram } from '../api';

interface Diagram {
  id: string;
  diagram_type: string;
  notation: string;
  source_code: string;
  render_svg?: string | null;
  render_status?: string; // pending | ok | failed | external_fallback | blocked_external
  render_error?: string | null;
  standard_profile?: string | null;
}

interface DiagramVersion {
  id: string;
  version_number: number;
  source_code: string;
  notation: string;
  created_at: string;
  change_note?: string | null;
}

const TYPE_LABELS: Record<string, string> = {
  c4_context: 'C4 Context',
  c4_container: 'C4 Container',
  c4_component: 'C4 Component',
  use_case: 'Use Case',
  sequence: 'Sequence',
  class: 'Class Diagram',
  erd: 'ERD',
  flowchart: 'Mermaid Flowchart',
  uml: 'UML Diagram',
};

// Эпик B6: человекочитаемые названия стандартов для бейджа диаграммы
const STANDARD_LABELS: Record<string, string> = {
  C4_MODEL: 'C4-модель',
  UML_ISO_19505: 'UML (ISO/IEC 19505)',
  ISO_IEC_IEEE_42010: 'ISO/IEC/IEEE 42010',
  GOST_19_701: 'ГОСТ 19.701-90',
  IEC_61082: 'IEC 61082',
};

// Эпик A2/A4: статус локального рендера — показываем честно, откуда пришла картинка
const RENDER_STATUS_META: Record<string, { label: string; className: string }> = {
  ok: { label: '🔒 Локальный рендер (Kroki)', className: 'text-teal-400 bg-teal-500/10 border-teal-500/20' },
  external_fallback: { label: '🌐 Внешний рендер-сервис', className: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20' },
  blocked_external: { label: '⛔ Рендер заблокирован (ENFORCE_LOCAL_ONLY)', className: 'text-red-400 bg-red-500/10 border-red-500/20' },
  failed: { label: '⚠️ Рендер не удался', className: 'text-red-400 bg-red-500/10 border-red-500/20' },
  pending: { label: '⏳ Не отрендерено', className: 'text-slate-muted bg-ink-muted border-slate-border' },
};

function encodePlantUML(code: string): string {
  let data = code;
  // Strip @startuml / @enduml for encoding
  data = data.replace(/@startuml\s*/i, '').replace(/@enduml\s*/i, '');
  data = data.trim();
  // PlantUML ASCII encoding
  let compressed = '';
  for (let i = 0; i < data.length; i++) {
    const c = data.charCodeAt(i);
    if (c === 10) compressed += '_';
    else if (c === 32) compressed += ' ';
    else if (c > 32 && c < 127) compressed += data[i];
  }
  // Simple base64-ish encode (PlantUML standard)
  const std = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_';
  let out = '~1';
  let bits = 0;
  let bitCount = 0;
  for (let i = 0; i < compressed.length; i++) {
    let val = compressed.charCodeAt(i);
    if (val > 127) val = 63;
    bits = (bits << 8) | val;
    bitCount += 8;
    while (bitCount >= 6) {
      bitCount -= 6;
      out += std[(bits >> bitCount) & 0x3f];
    }
  }
  if (bitCount > 0) {
    bits <<= (6 - bitCount);
    out += std[bits & 0x3f];
  }
  return out;
}

function MermaidDiagram({ code }: { code: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    if (!ref.current) return;
    const w = window as any;
    if (w.mermaid) {
      try {
        ref.current.innerHTML = code;
        ref.current.removeAttribute('data-processed');
        w.mermaid.init(undefined, ref.current);
        setError(false);
      } catch {
        setError(true);
      }
    } else {
      setError(true);
    }
  }, [code]);
  if (error) {
    return (
      <div>
        <pre className="code-block text-xs leading-relaxed max-h-[500px] overflow-auto">{code}</pre>
        <p className="text-xs text-slate-muted/60 mt-1">
          Просмотр:         <a href={`https://mermaid.live/edit#code=${btoa(unescape(encodeURIComponent(code)))}`} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">mermaid.live ↗</a>
        </p>
      </div>
    );
  }
  return <div ref={ref} className="mermaid text-sm" />;
}

function PlantUMLDiagram({ code }: { code: string }) {
  const encoded = encodePlantUML(code);
  const imgUrl = `https://www.plantuml.com/plantuml/svg/${encoded}`;

  return (
    <div className="space-y-3">
      <img src={imgUrl} alt="PlantUML diagram" className="max-w-full bg-white rounded-lg p-2"
        onError={(e) => {
          (e.target as HTMLImageElement).style.display = 'none';
          (e.target as HTMLImageElement).nextElementSibling?.classList.remove('hidden');
        }} />
      <pre className="code-block text-xs leading-relaxed max-h-[500px] overflow-auto hidden">{code}</pre>
      <p className="text-xs text-slate-muted/60">
        PlantUML: <a href={`https://www.plantuml.com/plantuml/uml/${encoded}`} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">plantuml.com ↗</a>
      </p>
    </div>
  );
}

/** Эпик A2: рендер, полученный локально от Kroki (SVG приходит напрямую с бэкенда) */
function LocalSvgDiagram({ svg }: { svg: string }) {
  return (
    <div
      className="max-w-full bg-white rounded-lg p-2 overflow-auto [&>svg]:max-w-full [&>svg]:h-auto"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}

export default function DiagramViewer({ diagrams }: { diagrams: Diagram[] }) {
  const [items, setItems] = useState<Diagram[]>(diagrams);
  const [selected, setSelected] = useState<Diagram | null>(diagrams[0] || null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const [saving, setSaving] = useState(false);
  const [showVersions, setShowVersions] = useState(false);
  const [versions, setVersions] = useState<DiagramVersion[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(false);

  useEffect(() => {
    setItems(diagrams);
    setSelected(prev => diagrams.find(d => d.id === prev?.id) || diagrams[0] || null);
  }, [diagrams]);

  useEffect(() => {
    setEditing(false);
    setShowVersions(false);
  }, [selected?.id]);

  if (!items.length) {
    return (
      <div className="text-center py-12 text-slate-muted text-sm">
        Диаграммы не сгенерированы. Нажмите «Генерировать диаграммы».
      </div>
    );
  }

  const updateSelected = (updated: Diagram) => {
    setItems(prev => prev.map(d => (d.id === updated.id ? updated : d)));
    setSelected(updated);
  };

  const handleStartEdit = () => {
    if (!selected) return;
    setDraft(selected.source_code);
    setEditing(true);
  };

  // Эпик A3: применить правку — сохранить версию и перерендерить локально
  const handleApplyEdit = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      const res = await updateDiagram(selected.id, draft, 'Правка через веб-панель');
      updateSelected(res.data);
      setEditing(false);
      toast('Диаграмма обновлена, версия сохранена', 'success');
    } catch (e: any) {
      toast(e?.response?.data?.detail || 'Не удалось обновить диаграмму', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleLoadVersions = async () => {
    if (!selected) return;
    setShowVersions(v => !v);
    if (showVersions) return; // toggling off — no need to refetch
    setVersionsLoading(true);
    try {
      const res = await getDiagramVersions(selected.id);
      setVersions(res.data);
    } catch {
      toast('Не удалось загрузить историю версий', 'error');
    } finally {
      setVersionsLoading(false);
    }
  };

  const handleRollback = async (versionNumber: number) => {
    if (!selected) return;
    try {
      const res = await rollbackDiagram(selected.id, versionNumber);
      updateSelected(res.data);
      toast(`Откачено к версии ${versionNumber}`, 'success');
      const v = await getDiagramVersions(selected.id);
      setVersions(v.data);
    } catch {
      toast('Не удалось откатить версию', 'error');
    }
  };

  const statusMeta = selected?.render_status ? RENDER_STATUS_META[selected.render_status] : null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {items.map(d => (
          <button
            key={d.id}
            onClick={() => setSelected(d)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              selected?.id === d.id
                ? 'bg-accent/20 text-accent border border-accent/30'
                : 'text-slate-muted hover:text-white border border-slate-border hover:border-slate-border/60'
            }`}
          >
            {TYPE_LABELS[d.diagram_type] || d.diagram_type}
            <span className={`ml-1.5 text-xs opacity-60 font-mono ${d.notation === 'mermaid' ? 'text-yellow-400' : 'text-green-400'}`}>
              {d.notation}
            </span>
          </button>
        ))}
      </div>

      {selected && (
        <div className="space-y-3 animate-fade-in">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="text-sm font-medium text-white">{TYPE_LABELS[selected.diagram_type] || selected.diagram_type}</p>
              {selected.standard_profile && (
                <span className="text-xs px-2 py-0.5 rounded-full border border-slate-border text-slate-muted font-mono">
                  {STANDARD_LABELS[selected.standard_profile] || selected.standard_profile}
                </span>
              )}
              {statusMeta && (
                <span className={`text-xs px-2 py-0.5 rounded-full border ${statusMeta.className}`}>
                  {statusMeta.label}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button className="btn-ghost text-xs" onClick={handleLoadVersions}>
                🕘 История версий
              </button>
              {!editing && (
                <button className="btn-ghost text-xs" onClick={handleStartEdit}>
                  ✏️ Редактировать код
                </button>
              )}
              <CopyButton text={selected.source_code} label="Копировать код" />
            </div>
          </div>

          {showVersions && (
            <div className="p-3 rounded-lg border border-slate-border bg-ink-soft space-y-2 animate-fade-in">
              {versionsLoading ? (
                <p className="text-xs text-slate-muted">Загрузка…</p>
              ) : versions.length === 0 ? (
                <p className="text-xs text-slate-muted">Правок ещё не было — история появится после первого редактирования.</p>
              ) : (
                versions.map(v => (
                  <div key={v.id} className="flex items-center justify-between text-xs p-2 rounded bg-ink border border-slate-border/60">
                    <div>
                      <span className="font-mono text-accent">v{v.version_number}</span>{' '}
                      <span className="text-slate-muted">{new Date(v.created_at).toLocaleString('ru-RU')}</span>
                      {v.change_note && <span className="text-slate-muted"> — {v.change_note}</span>}
                    </div>
                    <button className="btn-ghost !py-1 !px-2 text-xs" onClick={() => handleRollback(v.version_number)}>
                      ↩ Откатить
                    </button>
                  </div>
                ))
              )}
            </div>
          )}

          {editing ? (
            <div className="space-y-2 animate-fade-in">
              <div className="rounded-lg overflow-hidden border border-slate-border">
                <CodeMirror
                  value={draft}
                  height="280px"
                  theme={oneDark}
                  basicSetup={{ lineNumbers: true, foldGutter: false, highlightActiveLine: true }}
                  extensions={[EditorView.lineWrapping]}
                  onChange={value => setDraft(value)}
                />
              </div>
              <div className="flex gap-2">
                <button className="btn-primary text-xs" onClick={handleApplyEdit} disabled={saving}>
                  {saving ? '⏳ Применяю…' : '✓ Применить и перерендерить'}
                </button>
                <button className="btn-ghost text-xs" onClick={() => setEditing(false)} disabled={saving}>
                  Отмена
                </button>
              </div>
              <p className="text-xs text-slate-muted/70">
                Предыдущая версия сохранится в истории — правку всегда можно откатить.
                {' '}Готовой грамматики PlantUML/Mermaid в редакторе нет — подсветка общая,
                но номера строк и парные скобки помогают ориентироваться в коде диаграммы.
              </p>
            </div>
          ) : selected.render_status === 'ok' && selected.render_svg ? (
            <LocalSvgDiagram svg={selected.render_svg} />
          ) : selected.notation === 'mermaid' ? (
            <div className="p-4 bg-white rounded-lg">
              <MermaidDiagram code={selected.source_code} />
            </div>
          ) : selected.notation === 'plantuml' ? (
            <PlantUMLDiagram code={selected.source_code} />
          ) : (
            <pre className="code-block text-xs leading-relaxed max-h-[500px] overflow-auto">
              {selected.source_code}
            </pre>
          )}

          {!editing && selected.render_status && selected.render_status !== 'ok' && selected.render_error && (
            <p className="text-xs text-slate-muted/70">{selected.render_error}</p>
          )}
        </div>
      )}
    </div>
  );
}
