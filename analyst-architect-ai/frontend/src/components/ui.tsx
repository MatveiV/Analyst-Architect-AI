import React, { useEffect, useState, useCallback } from 'react';
import { useI18n } from '../i18n';

// ── Toast ─────────────────────────────────────────────────────────────────────
type ToastType = 'success' | 'error' | 'info';
interface ToastMsg { id: number; type: ToastType; text: string; }

const toastListeners: ((t: ToastMsg) => void)[] = [];
let toastId = 0;

export function toast(text: string, type: ToastType = 'info') {
  const msg: ToastMsg = { id: ++toastId, type, text };
  toastListeners.forEach(fn => fn(msg));
}

export function ToastContainer() {
  const [msgs, setMsgs] = useState<ToastMsg[]>([]);
  useEffect(() => {
    const handler = (m: ToastMsg) => {
      setMsgs(p => [...p, m]);
      setTimeout(() => setMsgs(p => p.filter(x => x.id !== m.id)), 4000);
    };
    toastListeners.push(handler);
    return () => { const i = toastListeners.indexOf(handler); if (i > -1) toastListeners.splice(i, 1); };
  }, []);
  const colors: Record<ToastType, string> = {
    success: 'border-green-500/40 bg-ok-bg text-green-300',
    error:   'border-red-500/40 bg-danger-bg text-red-300',
    info:    'border-accent/40 bg-accent-glow text-accent-light',
  };
  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2">
      {msgs.map(m => (
        <div key={m.id} className={`card border ${colors[m.type]} animate-fade-in px-4 py-3 text-sm max-w-xs shadow-xl`}>
          {m.text}
        </div>
      ))}
    </div>
  );
}

// ── Spinner ───────────────────────────────────────────────────────────────────
export function Spinner({ size = 'sm' }: { size?: 'sm' | 'md' | 'lg' }) {
  const s = { sm: 'w-4 h-4 border-2', md: 'w-6 h-6 border-2', lg: 'w-8 h-8 border-[3px]' }[size];
  return <span className={`inline-block ${s} border-slate-border border-t-accent rounded-full animate-spin`} />;
}

// ── NeedsReviewBadge ──────────────────────────────────────────────────────────
export function NeedsReviewBadge({ show }: { show: boolean }) {
  const { t } = useI18n();
  if (!show) return null;
  return <span className="badge-needs-review inline-flex items-center gap-1">{t('needs_review')}</span>;
}

// ── SeverityBadge ─────────────────────────────────────────────────────────────
export function SeverityBadge({ severity }: { severity: string }) {
  const { t } = useI18n();
  const cls = severity === 'high' ? 'badge-high' : severity === 'medium' ? 'badge-medium' : 'badge-low';
  const label = severity === 'high' ? t('sev_high') : severity === 'medium' ? t('sev_medium') : t('sev_low');
  return <span className={cls}>{label}</span>;
}

// ── ConfidenceBadge ───────────────────────────────────────────────────────────
export function ConfidenceBadge({ confidence }: { confidence: string }) {
  const { t } = useI18n();
  const cfg: Record<string, string> = {
    high:   'text-green-400 bg-ok-bg border-green-500/30',
    medium: 'text-yellow-400 bg-warn-bg border-yellow-500/30',
    low:    'text-red-400 bg-danger-bg border-red-500/30',
  };
  const label = confidence === 'high' ? t('confidence_high')
              : confidence === 'medium' ? t('confidence_med')
              : t('confidence_low');
  return (
    <span className={`${cfg[confidence] || cfg.medium} border px-2 py-0.5 rounded text-xs font-mono`}>
      {label}
    </span>
  );
}

// ── CopyButton ────────────────────────────────────────────────────────────────
export function CopyButton({ text, label }: { text: string; label?: string }) {
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);
  const copy = useCallback(() => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [text]);
  return (
    <button onClick={copy} className="btn-ghost text-xs px-3 py-1.5">
      {copied ? t('copied') : (label || t('copy'))}
    </button>
  );
}

// ── EmptyState ────────────────────────────────────────────────────────────────
export function EmptyState({ icon, title, subtitle }: { icon: string; title: string; subtitle?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="text-5xl mb-4 opacity-30">{icon}</div>
      <p className="text-slate-muted font-medium">{title}</p>
      {subtitle && <p className="text-slate-muted/60 text-sm mt-1">{subtitle}</p>}
    </div>
  );
}

// ── LoadingOverlay ────────────────────────────────────────────────────────────
export function LoadingOverlay({ message }: { message?: string }) {
  const { t } = useI18n();
  return (
    <div className="flex items-center gap-3 p-4 card border-accent/30 bg-accent-glow animate-pulse-glow">
      <Spinner size="md" />
      <span className="text-accent-light text-sm">{message || t('loading')}</span>
    </div>
  );
}

// ── JsonViewer ────────────────────────────────────────────────────────────────
export function JsonViewer({ data }: { data: any }) {
  const json = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
  return (
    <div className="relative">
      <pre className="code-block text-xs max-h-96 overflow-auto">{json}</pre>
      <div className="absolute top-2 right-2">
        <CopyButton text={json} label="JSON" />
      </div>
    </div>
  );
}

// ── SectionHeader ─────────────────────────────────────────────────────────────
export function SectionHeader({
  title, subtitle, action,
}: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-white">{title}</h1>
        {subtitle && <p className="text-slate-muted text-sm mt-1">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}

// ── Modal ─────────────────────────────────────────────────────────────────────
export function Modal({ open, onClose, title, children, wide = false }:
  { open: boolean; onClose: () => void; title: string; children: React.ReactNode; wide?: boolean }) {
  useEffect(() => {
    if (open) document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, [open]);
  const { t } = useI18n();
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className={`relative card border-slate-border animate-fade-in shadow-2xl
        ${wide ? 'w-full max-w-4xl' : 'w-full max-w-2xl'} max-h-[90vh] flex flex-col`}>
        <div className="flex items-center justify-between p-5 border-b border-slate-border">
          <h2 className="font-display font-bold text-lg">{title}</h2>
          <button onClick={onClose} className="text-slate-muted hover:text-white text-xl leading-none"
            title={t('close')}>✕</button>
        </div>
        <div className="overflow-y-auto flex-1 p-5">{children}</div>
      </div>
    </div>
  );
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
export function Tabs({ tabs, active, onChange }: {
  tabs: { key: string; label: string }[];
  active: string;
  onChange: (k: string) => void;
}) {
  return (
    <div className="flex gap-1 bg-ink-muted p-1 rounded-lg">
      {tabs.map(t => (
        <button key={t.key}
          onClick={() => onChange(t.key)}
          className={`tab-btn flex-1 ${active === t.key ? 'tab-btn-active' : 'tab-btn-inactive'}`}>
          {t.label}
        </button>
      ))}
    </div>
  );
}
