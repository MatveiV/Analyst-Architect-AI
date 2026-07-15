import React, { useMemo } from 'react';

function encodePlantUML(code: string): string {
  const data = code.replace(/@startuml\s*/i, '').replace(/@enduml\s*/i, '').trim();
  const std = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_';
  let out = '~1';
  let bits = 0;
  let bitCount = 0;
  for (let i = 0; i < data.length; i++) {
    let val = data.charCodeAt(i);
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

const RENDERED_CACHE = new Map<string, string>();

function renderMarkdown(md: string): string {
  if (RENDERED_CACHE.has(md)) return RENDERED_CACHE.get(md)!;

  let html = md
    // Escape HTML
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    // Headers
    .replace(/^###### (.*)$/gm, '<h6>$1</h6>')
    .replace(/^##### (.*)$/gm, '<h5>$1</h5>')
    .replace(/^#### (.*)$/gm, '<h4>$1</h4>')
    .replace(/^### (.*)$/gm, '<h3>$1</h3>')
    .replace(/^## (.*)$/gm, '<h2>$1</h2>')
    .replace(/^# (.*)$/gm, '<h1>$1</h1>')
    // Bold & italic
    .replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code class="text-xs bg-ink-muted px-1 py-0.5 rounded font-mono">$1</code>')
    // Images
    .replace(/!\[(.*?)\]\((.*?)\)/g, '<img src="$2" alt="$1" class="max-w-full rounded-lg my-2" />')
    // Links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-accent hover:underline">$1</a>')
    // Horizontal rules
    .replace(/^---$/gm, '<hr class="border-slate-border my-4" />')
    // Blockquotes
    .replace(/^&gt; (.*)$/gm, '<blockquote class="border-l-2 border-accent/40 pl-4 text-slate-muted italic my-2">$1</blockquote>')
    // Unordered lists
    .replace(/^- (.*)$/gm, '<li class="ml-4 list-disc text-white/80">$1</li>')
    .replace(/(<li.*<\/li>\n?)+/g, '<ul class="space-y-1 my-2">$&</ul>')
    // Ordered lists
    .replace(/^\d+\. (.*)$/gm, '<li class="ml-4 list-decimal text-white/80">$1</li>')
    // Line breaks
    .replace(/\n\n/g, '</p><p class="text-white/80 leading-relaxed mb-3">')
    .replace(/\n/g, '<br />');

  // Mermaid blocks: render as placeholder for JS
  html = html.replace(/```mermaid\n([\s\S]*?)```/g, (_m, code) => {
    const encoded = btoa(code.trim());
    return `<div class="mermaid-block bg-white rounded-lg p-4 my-3" data-mermaid="${encoded}"><pre class="text-xs opacity-60">Mermaid diagram (loading...)</pre></div>`;
  });

  // PlantUML blocks: render as image
  html = html.replace(/```plantuml\n([\s\S]*?)```/g, (_m, code) => {
    const encoded = encodePlantUML(code);
    return `<div class="my-3"><img src="https://www.plantuml.com/plantuml/svg/${encoded}" alt="PlantUML" class="max-w-full bg-white rounded-lg p-2" onerror="this.nextElementSibling.style.display='block';this.style.display='none'" /><pre class="code-block text-xs mt-1 hidden">${code.trim()}</pre></div>`;
  });

  html = `<p class="text-white/80 leading-relaxed mb-3">${html}</p>`;
  RENDERED_CACHE.set(md, html);
  return html;
}

export default function MarkdownViewer({ text, className = '' }: { text: string; className?: string }) {
  const html = useMemo(() => renderMarkdown(text), [text]);

  return (
    <div className={`prose prose-invert max-w-none ${className}`}>
      <div
        dangerouslySetInnerHTML={{ __html: html }}
        ref={(el) => {
          if (!el) return;
          el.querySelectorAll('.mermaid-block').forEach(async (block) => {
            const encoded = block.getAttribute('data-mermaid');
            if (!encoded) return;
            try {
              const w = window as any;
              if (w.mermaid) {
                const code = atob(encoded);
                block.innerHTML = code;
                block.removeAttribute('data-processed');
                await w.mermaid.init(undefined, block);
              } else {
                block.innerHTML = `<pre class="code-block text-xs">${atob(encoded)}</pre><p class="text-xs text-slate-muted/60 mt-1"><a href="https://mermaid.live/edit#code=${encoded}" target="_blank" rel="noopener noreferrer" class="text-accent hover:underline">mermaid.live ↗</a></p>`;
              }
            } catch {
              block.innerHTML = `<pre class="code-block text-xs">${atob(encoded)}</pre>`;
            }
          });
        }}
      />
    </div>
  );
}