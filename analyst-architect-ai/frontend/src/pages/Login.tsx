import React, { useState } from 'react';
import { useAuth } from '../AuthContext';
import { useI18n } from '../i18n';
import { Spinner } from '../components/ui';

export default function LoginPage() {
  const { login } = useAuth();
  const { lang, setLang } = useI18n();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) return;
    setLoading(true);
    setError('');
    try {
      await login(username.trim(), password);
    } catch (err: any) {
      const msg = err?.response?.data?.detail;
      setError(
        lang === 'ru'
          ? (msg === 'Incorrect username or password' ? 'Неверный логин или пароль' : 'Ошибка входа')
          : (msg || 'Login failed')
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-ink flex items-center justify-center p-4">
      {/* Lang toggle top-right */}
      <div className="fixed top-4 right-4">
        <button
          onClick={() => setLang(lang === 'ru' ? 'en' : 'ru')}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-border
                     hover:border-accent/40 hover:bg-accent/10 transition-all text-xs font-medium text-slate-muted hover:text-accent">
          <span className="text-base">{lang === 'ru' ? '🇬🇧' : '🇷🇺'}</span>
          <span className="font-mono">{lang === 'ru' ? 'EN' : 'RU'}</span>
        </button>
      </div>

      <div className="w-full max-w-md animate-fade-in">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-accent pulse-glow mb-4">
            <span className="font-display font-bold text-white text-2xl">AG</span>
          </div>
          <h1 className="font-display text-3xl font-bold text-white">AnalystGuru</h1>
          <p className="text-slate-muted mt-1 text-sm">AI System Analyst Copilot</p>
        </div>

        {/* Card */}
        <div className="card border-slate-border shadow-2xl">
          <h2 className="font-display font-bold text-white text-lg mb-5">
            {lang === 'ru' ? 'Вход в систему' : 'Sign in'}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">{lang === 'ru' ? 'Логин' : 'Username'}</label>
              <input
                className="input"
                placeholder="analyst"
                value={username}
                onChange={e => setUsername(e.target.value)}
                autoFocus
                autoComplete="username"
              />
            </div>
            <div>
              <label className="label">{lang === 'ru' ? 'Пароль' : 'Password'}</label>
              <input
                type="password"
                className="input"
                placeholder="••••••••"
                value={password}
                onChange={e => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>

            {error && (
              <div className="bg-danger-bg border border-red-500/30 rounded-lg px-4 py-2.5 text-red-400 text-sm">
                {error}
              </div>
            )}

            <button type="submit" className="btn-primary w-full justify-center py-3" disabled={loading}>
              {loading ? <><Spinner /> {lang === 'ru' ? 'Вхожу…' : 'Signing in…'}</> : (lang === 'ru' ? '→ Войти' : '→ Sign in')}
            </button>
          </form>

          {/* Default credentials hint */}
          <div className="mt-5 pt-4 border-t border-slate-border">
            <p className="text-xs text-slate-muted mb-2">
              {lang === 'ru' ? 'Тестовые учётные записи:' : 'Test accounts:'}
            </p>
            <div className="space-y-1.5">
              {[
                { role: 'admin',     user: 'admin',     pass: 'admin123',     color: 'text-red-400' },
                { role: 'analyst',   user: 'analyst',   pass: 'analyst123',   color: 'text-blue-400' },
                { role: 'architect', user: 'architect', pass: 'architect123', color: 'text-purple-400' },
              ].map(acc => (
                <button
                  key={acc.role}
                  type="button"
                  className="w-full flex items-center justify-between px-3 py-1.5 rounded-lg
                             bg-ink-muted hover:bg-ink-soft border border-slate-border/50
                             transition-all text-xs cursor-pointer"
                  onClick={() => { setUsername(acc.user); setPassword(acc.pass); }}
                >
                  <span className={`font-mono font-medium ${acc.color}`}>{acc.role}</span>
                  <span className="text-slate-muted font-mono">{acc.user} / {acc.pass}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
