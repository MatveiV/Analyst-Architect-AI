import React, { useState, useEffect, useCallback } from 'react';
import api from '../api';
import { SectionHeader, EmptyState, Spinner, toast } from '../components/ui';
import { useAuth } from '../AuthContext';
import { useI18n } from '../i18n';

interface UserRow {
  id: string; username: string; email: string; full_name: string;
  role: string; is_active: boolean; created_at: string; last_login?: string;
}

const ROLE_COLORS: Record<string, string> = {
  admin:     'text-red-400 bg-red-500/10 border-red-500/30',
  analyst:   'text-blue-400 bg-blue-500/10 border-blue-500/30',
  architect: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
};

const ROLE_LABELS_RU: Record<string, string> = { admin: 'Администратор', analyst: 'Аналитик', architect: 'Архитектор' };
const ROLE_LABELS_EN: Record<string, string> = { admin: 'Administrator', analyst: 'Analyst', architect: 'Architect' };

export default function UsersPage() {
  const { lang } = useI18n();
  const { isAdmin } = useAuth();
  const ROLE_LABELS = lang === 'ru' ? ROLE_LABELS_RU : ROLE_LABELS_EN;

  const [users, setUsers] = useState<UserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [resetId, setResetId] = useState<string | null>(null);
  const [newPwd, setNewPwd] = useState('');
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({ username: '', email: '', password: '', full_name: '', role: 'analyst' });

  const load = useCallback(async () => {
    setLoading(true);
    try { const r = await api.get('/auth/users'); setUsers(r.data); }
    catch { toast(lang === 'ru' ? 'Ошибка загрузки' : 'Load error', 'error'); }
    finally { setLoading(false); }
  }, [lang]);

  useEffect(() => { load(); }, [load]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true);
    try {
      await api.post('/auth/register', form);
      toast(lang === 'ru' ? 'Пользователь создан' : 'User created', 'success');
      setShowAdd(false); setForm({ username: '', email: '', password: '', full_name: '', role: 'analyst' });
      load();
    } catch (err: any) { toast(err?.response?.data?.detail || 'Error', 'error'); }
    finally { setSaving(false); }
  };

  const handleToggleActive = async (u: UserRow) => {
    try {
      await api.patch(`/auth/users/${u.id}`, { is_active: !u.is_active });
      toast(lang === 'ru' ? 'Обновлено' : 'Updated', 'success'); load();
    } catch { toast('Error', 'error'); }
  };

  const handleRoleChange = async (u: UserRow, role: string) => {
    try {
      await api.patch(`/auth/users/${u.id}`, { role });
      toast(lang === 'ru' ? 'Роль изменена' : 'Role updated', 'success'); load();
    } catch { toast('Error', 'error'); }
  };

  const handleResetPwd = async (userId: string) => {
    if (!newPwd.trim()) return; setSaving(true);
    try {
      await api.post(`/auth/users/${userId}/reset-password`, { new_password: newPwd });
      toast(lang === 'ru' ? 'Пароль сброшен' : 'Password reset', 'success');
      setResetId(null); setNewPwd('');
    } catch { toast('Error', 'error'); }
    finally { setSaving(false); }
  };

  if (!isAdmin) return (
    <div className="flex items-center justify-center h-64 text-slate-muted">
      {lang === 'ru' ? '⛔ Только для администраторов' : '⛔ Admin only'}
    </div>
  );

  return (
    <div>
      <SectionHeader
        title={lang === 'ru' ? 'Пользователи' : 'Users'}
        subtitle={lang === 'ru' ? 'Управление учётными записями и ролями' : 'Manage accounts and roles'}
        action={
          <button className="btn-primary" onClick={() => setShowAdd(v => !v)}>
            {showAdd ? '✕' : `+ ${lang === 'ru' ? 'Добавить' : 'Add User'}`}
          </button>
        }
      />

      {/* Add form */}
      {showAdd && (
        <form onSubmit={handleAdd} className="card border-accent/30 mb-6 space-y-4 animate-fade-in">
          <p className="font-display font-bold">{lang === 'ru' ? 'Новый пользователь' : 'New User'}</p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">{lang === 'ru' ? 'Логин' : 'Username'}</label>
              <input className="input" value={form.username} onChange={e => setForm(p => ({...p, username: e.target.value}))} />
            </div>
            <div>
              <label className="label">Email</label>
              <input className="input" type="email" value={form.email} onChange={e => setForm(p => ({...p, email: e.target.value}))} />
            </div>
            <div>
              <label className="label">{lang === 'ru' ? 'Пароль' : 'Password'}</label>
              <input className="input" type="password" value={form.password} onChange={e => setForm(p => ({...p, password: e.target.value}))} />
            </div>
            <div>
              <label className="label">{lang === 'ru' ? 'Имя' : 'Full Name'}</label>
              <input className="input" value={form.full_name} onChange={e => setForm(p => ({...p, full_name: e.target.value}))} />
            </div>
            <div>
              <label className="label">{lang === 'ru' ? 'Роль' : 'Role'}</label>
              <select className="input" value={form.role} onChange={e => setForm(p => ({...p, role: e.target.value}))}>
                <option value="analyst">{ROLE_LABELS.analyst}</option>
                <option value="architect">{ROLE_LABELS.architect}</option>
                <option value="admin">{ROLE_LABELS.admin}</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" className="btn-ghost" onClick={() => setShowAdd(false)}>{lang === 'ru' ? 'Отмена' : 'Cancel'}</button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? <Spinner /> : `✓ ${lang === 'ru' ? 'Создать' : 'Create'}`}
            </button>
          </div>
        </form>
      )}

      {/* Reset password modal */}
      {resetId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60" onClick={() => setResetId(null)} />
          <div className="relative card w-full max-w-sm animate-fade-in">
            <h2 className="font-display font-bold mb-4">{lang === 'ru' ? 'Сброс пароля' : 'Reset Password'}</h2>
            <input className="input mb-4" type="password" placeholder={lang === 'ru' ? 'Новый пароль' : 'New password'}
              value={newPwd} onChange={e => setNewPwd(e.target.value)} />
            <div className="flex justify-end gap-2">
              <button className="btn-ghost" onClick={() => { setResetId(null); setNewPwd(''); }}>
                {lang === 'ru' ? 'Отмена' : 'Cancel'}
              </button>
              <button className="btn-primary" onClick={() => handleResetPwd(resetId)} disabled={saving}>
                {saving ? <Spinner /> : (lang === 'ru' ? 'Сохранить' : 'Save')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Users table */}
      {loading ? (
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      ) : users.length === 0 ? (
        <EmptyState icon="👤" title={lang === 'ru' ? 'Нет пользователей' : 'No users'} />
      ) : (
        <div className="rounded-xl border border-slate-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-ink-muted text-slate-muted text-xs uppercase tracking-wider">
                <th className="px-4 py-3 text-left">{lang === 'ru' ? 'Пользователь' : 'User'}</th>
                <th className="px-4 py-3 text-left">{lang === 'ru' ? 'Роль' : 'Role'}</th>
                <th className="px-4 py-3 text-left">{lang === 'ru' ? 'Статус' : 'Status'}</th>
                <th className="px-4 py-3 text-left">{lang === 'ru' ? 'Последний вход' : 'Last login'}</th>
                <th className="px-4 py-3 text-right">{lang === 'ru' ? 'Действия' : 'Actions'}</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u, i) => (
                <tr key={u.id} className={`border-t border-slate-border ${i % 2 === 0 ? 'bg-ink-soft' : 'bg-ink'}`}>
                  <td className="px-4 py-3">
                    <p className="font-medium text-white">{u.full_name || u.username}</p>
                    <p className="text-xs text-slate-muted font-mono">{u.username} · {u.email}</p>
                  </td>
                  <td className="px-4 py-3">
                    <select
                      value={u.role}
                      onChange={e => handleRoleChange(u, e.target.value)}
                      className={`text-xs font-medium border px-2 py-1 rounded bg-transparent cursor-pointer ${ROLE_COLORS[u.role]}`}>
                      <option value="analyst">{ROLE_LABELS.analyst}</option>
                      <option value="architect">{ROLE_LABELS.architect}</option>
                      <option value="admin">{ROLE_LABELS.admin}</option>
                    </select>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-mono border px-2 py-0.5 rounded ${
                      u.is_active ? 'text-green-400 bg-ok-bg border-green-500/30' : 'text-slate-muted bg-ink-muted border-slate-border'
                    }`}>
                      {u.is_active ? (lang === 'ru' ? 'Активен' : 'Active') : (lang === 'ru' ? 'Заблокирован' : 'Blocked')}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-muted font-mono">
                    {u.last_login ? new Date(u.last_login).toLocaleString(lang === 'ru' ? 'ru' : 'en') : '—'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex gap-2 justify-end">
                      <button className="btn-ghost text-xs px-2 py-1" onClick={() => { setResetId(u.id); setNewPwd(''); }}>
                        🔑
                      </button>
                      <button className="btn-ghost text-xs px-2 py-1" onClick={() => handleToggleActive(u)}>
                        {u.is_active ? '🚫' : '✓'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
