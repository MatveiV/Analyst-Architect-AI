import React, { useEffect, useRef, useState } from 'react';
import { CopyButton } from './ui';

interface Diagram {
  id: string;
  diagram_type: string;
  notation: string;
  source_code: string;
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

export default function DiagramViewer({ diagrams }: { diagrams: Diagram[] }) {
  const [selected, setSelected] = React.useState<Diagram | null>(diagrams[0] || null);

  if (!diagrams.length) {
    return (
      <div className="text-center py-12 text-slate-muted text-sm">
        Диаграммы не сгенерированы. Нажмите «Генерировать диаграммы».
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {diagrams.map(d => (
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
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-white">{TYPE_LABELS[selected.diagram_type] || selected.diagram_type}</p>
            <CopyButton text={selected.source_code} label="Копировать код" />
          </div>

          {selected.notation === 'mermaid' ? (
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
        </div>
      )}
    </div>
  );
}