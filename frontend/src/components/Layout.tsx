import React from 'react';
import { NavLink } from 'react-router-dom';
import { useI18n, LangToggle } from '../i18n';
import { useAuth } from '../AuthContext';

const ROLE_COLORS: Record<string, string> = {
  admin:     'text-red-400 bg-red-500/10 border-red-500/30',
  analyst:   'text-blue-400 bg-blue-500/10 border-blue-500/30',
  architect: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
};
const ROLE_LABELS_RU: Record<string, string> = { admin: 'Администратор', analyst: 'Аналитик', architect: 'Архитектор' };
const ROLE_LABELS_EN: Record<string, string> = { admin: 'Administrator', analyst: 'Analyst', architect: 'Architect' };

export default function Layout({ children }: { children: React.ReactNode }) {
  const { t, lang } = useI18n();
  const { user, logout, isAdmin } = useAuth();
  const ROLE_LABELS = lang === 'ru' ? ROLE_LABELS_RU : ROLE_LABELS_EN;

  const nav = [
    { path: '/dashboard', icon: '📊', labelKey: 'nav_dashboard' as const },
    { path: '/documents', icon: '📄', labelKey: 'nav_documents' as const },
    { path: '/reviews',   icon: '🔍', labelKey: 'nav_reviews'   as const },
    { path: '/batch-reviews', icon: '📦', labelKey: 'nav_batch_reviews' as const },
    { path: '/kb',        icon: '🧠', labelKey: 'nav_kb'        as const },
    { path: '/studio',    icon: '🏛️', labelKey: 'nav_studio'    as const },
    { path: '/memory',    icon: '💾', labelKey: 'nav_memory'    as const },
    { path: '/audit',     icon: '📋', labelKey: 'nav_audit'     as const },
    { path: '/economics', icon: '💰', labelKey: 'nav_economics' as const },
    { path: '/risks',     icon: '⚠️', labelKey: 'nav_risks'     as const },
    { path: '/lessons',   icon: '📚', labelKey: 'nav_lessons'   as const },
    { path: '/settings',  icon: '⚙️', labelKey: 'nav_settings'  as const },
    ...(isAdmin ? [{ path: '/users', icon: '👥', labelKey: 'nav_users' as const }] : []),
  ];

  return (
    <div className="flex min-h-screen bg-ink">
      <aside className="w-56 shrink-0 border-r border-slate-border bg-ink-soft flex flex-col">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-slate-border">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center text-white font-display font-bold text-sm pulse-glow">
              AG
            </div>
            <div>
              <p className="font-display font-bold text-white text-sm leading-tight">AnalystGuru</p>
              <p className="text-xs text-slate-muted">{t('layout_ai_copilot')}</p>
            </div>
          </div>
        </div>

        {/* User badge */}
        {user && (
          <div className="px-4 py-3 border-b border-slate-border bg-ink-muted/40">
            <p className="text-xs text-white font-medium truncate">{user.full_name || user.username}</p>
            <div className="flex items-center justify-between mt-1">
              <span className={`text-xs font-medium border px-1.5 py-0.5 rounded ${ROLE_COLORS[user.role]}`}>
                {ROLE_LABELS[user.role] || user.role}
              </span>
              <button onClick={logout}
                className="text-xs text-slate-muted hover:text-red-400 transition-colors"
                title={lang === 'ru' ? 'Выйти' : 'Logout'}>
                ⎋
              </button>
            </div>
          </div>
        )}

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {nav.map(item => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-accent/15 text-accent border border-accent/25'
                    : 'text-slate-muted hover:text-white hover:bg-ink-muted'
                }`
              }
            >
              <span className="text-base">{item.icon}</span>
              {t(item.labelKey)}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-4 py-4 border-t border-slate-border space-y-3">
          <LangToggle />
          <p className="text-xs text-slate-muted/60">v1.0.0 · enterprise</p>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto px-6 py-8 animate-fade-in">
          {children}
        </div>
      </main>
    </div>
  );
}
