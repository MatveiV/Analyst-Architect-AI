import React, { useState, useEffect, useCallback } from 'react';
import { listProviders, saveProvider, activateProvider, testProvider, seedExamples } from '../api';
import { SectionHeader, Spinner, toast } from '../components/ui';
import { useI18n } from '../i18n';

interface Provider {
  id: string;
  provider: string;
  api_key_masked: string;
  model: string;
  base_url: string;
  temperature: number;
  max_tokens: number;
  route: string;
  is_active: boolean;
  updated_at: string;
}

const OPENROUTER_ROUTES = [
  { value: 'openrouter/free', label: 'Free (бесплатные модели)' },
  { value: 'openrouter/fusion', label: 'Fusion (ансамбль моделей)' },
  { value: 'openrouter/pareto-code', label: 'Pareto Code (оптимизация кода)' },
];

const PROVIDER_META: Record<string, {
  label: string; icon: string; color: string;
  defaultModels: string[]; showBaseUrl: boolean;
  infoKey: 'set_anthropic_info' | 'set_openai_info' | 'set_proxyapi_info' | 'set_openrouter_info';
  docsUrl: string;
}> = {
  anthropic: {
    label: 'Anthropic Claude',
    icon: '🤖',
    color: 'border-orange-500/40 bg-orange-500/5',
    defaultModels: [
      'claude-sonnet-4-20250514',
      'claude-opus-4-20250514',
      'claude-haiku-4-5-20251001',
      'claude-opus-4-8',
    ],
    showBaseUrl: false,
    infoKey: 'set_anthropic_info',
    docsUrl: 'https://docs.anthropic.com/en/api/getting-started',
  },
  openai: {
    label: 'OpenAI GPT',
    icon: '🟢',
    color: 'border-green-500/40 bg-green-500/5',
    defaultModels: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
    showBaseUrl: true,
    infoKey: 'set_openai_info',
    docsUrl: 'https://platform.openai.com/docs',
  },
  proxyapi: {
    label: 'ProxyAPI',
    icon: '🔀',
    color: 'border-blue-500/40 bg-blue-500/5',
    defaultModels: [
      'claude-sonnet-4-20250514',
      'claude-opus-4-20250514',
      'claude-haiku-4-5-20251001',
      'gpt-4o',
      'gpt-4o-mini',
    ],
    showBaseUrl: true,
    infoKey: 'set_proxyapi_info',
    docsUrl: 'https://proxyapi.ru',
  },
  openrouter: {
    label: 'OpenRouter',
    icon: '🌐',
    color: 'border-purple-500/40 bg-purple-500/5',
    defaultModels: [
      'openrouter/auto',
      'openrouter/chatgpt',
      'openrouter/claude',
      'openrouter/gemini',
      'openrouter/llama',
      'openrouter/qwen',
      'openrouter/deepseek',
      'openrouter/free',
    ],
    showBaseUrl: true,
    infoKey: 'set_openrouter_info',
    docsUrl: 'https://openrouter.ai/docs',
  },
};

export default function SettingsPage() {
  const { t, lang } = useI18n();
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [testing, setTesting] = useState<string | null>(null);
  const [activating, setActivating] = useState<string | null>(null);
  const [seeding, setSeeding] = useState(false);
  const [testResults, setTestResults] = useState<Record<string, { status: string; msg: string }>>({});
  const [forms, setForms] = useState<Record<string, any>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listProviders();
      setProviders(res.data);
      // Init forms with current values (api_key left blank for security)
      const init: Record<string, any> = {};
      res.data.forEach((p: Provider) => {
        init[p.provider] = {
          api_key: '',
          model: p.model,
          base_url: p.base_url,
          temperature: p.temperature,
          max_tokens: p.max_tokens,
          route: p.route || 'openrouter/free',
        };
      });
      setForms(init);
    } catch { toast(t('error_loading'), 'error'); }
    finally { setLoading(false); }
  }, [t]);

  useEffect(() => { load(); }, [load]);

  const handleSave = async (provider: string) => {
    setSaving(provider);
    try {
      const form = forms[provider];
      await saveProvider({
        provider,
        api_key: form.api_key || '',
        model: form.model,
        base_url: form.base_url,
        temperature: parseFloat(form.temperature),
        max_tokens: parseInt(form.max_tokens),
        route: form.route || 'openrouter/free',
        is_active: false,
      });
      toast(t('set_saved'), 'success');
      setEditing(null);
      await load();
    } catch { toast(t('set_save_err'), 'error'); }
    finally { setSaving(null); }
  };

  const handleActivate = async (provider: string) => {
    setActivating(provider);
    try {
      await activateProvider(provider);
      toast(`${PROVIDER_META[provider]?.label} — ${t('set_activated')}`, 'success');
      await load();
    } catch { toast(t('error_loading'), 'error'); }
    finally { setActivating(null); }
  };

  const handleTest = async (provider: string) => {
    setTesting(provider);
    setTestResults(p => ({ ...p, [provider]: { status: 'loading', msg: '' } }));
    try {
      const res = await testProvider(provider);
      const data = res.data;
      if (data.status === 'ok') {
        setTestResults(p => ({ ...p, [provider]: { status: 'ok', msg: data.response || 'OK' } }));
        toast(`${PROVIDER_META[provider]?.label}: ${t('set_test_ok')}`, 'success');
      } else {
        setTestResults(p => ({ ...p, [provider]: { status: 'error', msg: data.error || 'Unknown error' } }));
        toast(`${t('set_test_err')}: ${data.error?.slice(0, 80)}`, 'error');
      }
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Network error';
      setTestResults(p => ({ ...p, [provider]: { status: 'error', msg } }));
      toast(t('set_test_err'), 'error');
    } finally { setTesting(null); }
  };

  const handleSeed = async () => {
    setSeeding(true);
    try {
      const res = await seedExamples();
      const data = res.data;
      const parts = Object.entries(data).map(([k, v]: any) => `${k}: ${v.loaded || v.skipped || 'OK'}`);
      toast((lang === 'ru' ? 'Демо-данные загружены: ' : 'Demo data loaded: ') + parts.join(', '), 'success');
    } catch {
      toast(lang === 'ru' ? 'Ошибка загрузки демо-данных' : 'Demo data error', 'error');
    } finally { setSeeding(false); }
  };

  const updateForm = (provider: string, field: string, value: any) => {
    setForms(p => ({ ...p, [provider]: { ...p[provider], [field]: value } }));
  };

  if (loading) return (
    <div className="flex justify-center items-center h-64"><Spinner size="lg" /></div>
  );

  const activeProvider = providers.find(p => p.is_active);

  return (
    <div>
      <SectionHeader title={t('set_title')} subtitle={t('set_subtitle')} />

      {/* Active provider status bar */}
      {activeProvider && (
        <div className="mb-6 p-4 rounded-xl border border-accent/30 bg-accent/5 flex items-center gap-3">
          <span className="text-2xl">{PROVIDER_META[activeProvider.provider]?.icon}</span>
          <div>
            <p className="text-xs text-slate-muted mb-0.5">{t('set_current')}</p>
            <p className="font-display font-bold text-white">
              {PROVIDER_META[activeProvider.provider]?.label}
              <span className="ml-2 text-sm font-normal text-accent font-mono">
                {activeProvider.model}
              </span>
            </p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            <span className="text-xs text-green-400 font-medium">Active</span>
          </div>
        </div>
      )}

      {/* Provider cards */}
      <div className="space-y-4">
        {(['anthropic', 'openai', 'proxyapi', 'openrouter'] as const).map(providerKey => {
          const meta = PROVIDER_META[providerKey];
          const provData = providers.find(p => p.provider === providerKey);
          const form = forms[providerKey] || {};
          const isEdit = editing === providerKey;
          const testResult = testResults[providerKey];
          const hasKey = !!provData?.api_key_masked;

          return (
            <div key={providerKey}
              className={`rounded-xl border ${meta.color} ${provData?.is_active ? 'ring-1 ring-accent/40' : ''} overflow-hidden`}>
              {/* Card header */}
              <div className="p-5 flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{meta.icon}</span>
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-display font-bold text-white">{meta.label}</p>
                      {provData?.is_active && (
                        <span className="text-xs bg-accent/20 text-accent border border-accent/30 px-2 py-0.5 rounded-full font-medium">
                          ✓ Active
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-muted mt-0.5">
                      {hasKey
                        ? <span className="text-green-400">🔑 {t('set_masked')}: {provData?.api_key_masked}</span>
                        : <span className="text-red-400/70">{t('set_no_key')}</span>
                      }
                      {provData?.model && (
                        <span className="ml-2 font-mono text-slate-muted/80">{provData.model}</span>
                      )}
                    </p>
                  </div>
                </div>

                <div className="flex gap-2 shrink-0 flex-wrap justify-end">
                  {!provData?.is_active && (
                    <button
                      className="btn-primary text-xs px-3 py-1.5"
                      disabled={activating === providerKey}
                      onClick={() => handleActivate(providerKey)}>
                      {activating === providerKey ? <Spinner /> : t('set_activate')}
                    </button>
                  )}
                  <button
                    className="btn-ghost text-xs px-3 py-1.5"
                    disabled={testing === providerKey || !hasKey}
                    onClick={() => handleTest(providerKey)}
                    title={!hasKey ? t('set_no_key') : ''}>
                    {testing === providerKey ? <Spinner /> : t('set_test')}
                  </button>
                  <button
                    className={`btn-ghost text-xs px-3 py-1.5 ${isEdit ? 'border-accent/40 text-accent' : ''}`}
                    onClick={() => setEditing(isEdit ? null : providerKey)}>
                    {isEdit ? '✕' : t('set_edit')}
                  </button>
                </div>
              </div>

              {/* Test result */}
              {testResult && testResult.status !== 'loading' && (
                <div className={`mx-5 mb-4 px-3 py-2 rounded-lg text-xs font-mono border ${
                  testResult.status === 'ok'
                    ? 'bg-ok-bg border-green-500/30 text-green-400'
                    : 'bg-danger-bg border-red-500/30 text-red-400'
                }`}>
                  {testResult.status === 'ok' ? '✓ ' : '✗ '}{testResult.msg}
                </div>
              )}

              {/* Info block */}
              <div className="mx-5 mb-4 px-3 py-2 rounded-lg bg-ink-muted/50 border border-slate-border/50 text-xs text-slate-muted flex items-start gap-2">
                <span className="shrink-0 mt-0.5">ℹ️</span>
                <span>{t(meta.infoKey)}</span>
                <a href={meta.docsUrl} target="_blank" rel="noopener noreferrer"
                  className="text-accent hover:underline shrink-0 ml-auto">
                  Docs ↗
                </a>
              </div>

              {/* Edit form */}
              {isEdit && (
                <div className="border-t border-slate-border bg-ink-soft px-5 py-5 space-y-4 animate-fade-in">
                  <p className="text-sm font-medium text-white">{t('set_edit')} — {meta.label}</p>

                  {/* API Key */}
                  <div>
                    <label className="label">{t('set_api_key')}</label>
                    <input
                      type="password"
                      className="input font-mono"
                      placeholder={t('set_api_key_ph')}
                      value={form.api_key || ''}
                      onChange={e => updateForm(providerKey, 'api_key', e.target.value)}
                      autoComplete="new-password"
                    />
                  </div>

                  {/* Model */}
                  <div>
                    <label className="label">{t('set_model')}</label>
                    <div className="flex gap-2">
                      <input
                        className="input flex-1 font-mono text-sm"
                        placeholder={meta.defaultModels[0]}
                        value={form.model || ''}
                        onChange={e => updateForm(providerKey, 'model', e.target.value)}
                      />
                      <select
                        className="input w-56 font-mono text-sm"
                        onChange={e => e.target.value && updateForm(providerKey, 'model', e.target.value)}
                        value="">
                        <option value="">— выбрать —</option>
                        {meta.defaultModels.map(m => (
                          <option key={m} value={m}>{m}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {/* Base URL (for openai / proxyapi) */}
                  {meta.showBaseUrl && (
                    <div>
                      <label className="label">{t('set_base_url')}</label>
                      <input
                        className="input font-mono text-sm"
                        placeholder={providerKey === 'proxyapi' ? 'https://api.proxyapi.ru/openai/v1' : 'https://api.openai.com/v1'}
                        value={form.base_url || ''}
                        onChange={e => updateForm(providerKey, 'base_url', e.target.value)}
                      />
                      {providerKey === 'proxyapi' && (
                        <p className="text-xs text-slate-muted mt-1">
                          По умолчанию: <code className="font-mono text-accent">https://api.proxyapi.ru/openai/v1</code>
                        </p>
                      )}
                    </div>
                  )}

                  {/* Temperature + Max tokens */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="label">{t('set_temperature')} <span className="text-accent font-mono">{form.temperature}</span></label>
                      <input
                        type="range" min="0" max="2" step="0.1"
                        className="w-full accent-[#6d6aff]"
                        value={form.temperature ?? 0.2}
                        onChange={e => updateForm(providerKey, 'temperature', parseFloat(e.target.value))}
                      />
                      <div className="flex justify-between text-xs text-slate-muted mt-0.5">
                        <span>0 (точно)</span><span>1 (баланс)</span><span>2 (творч.)</span>
                      </div>
                    </div>
                    <div>
                      <label className="label">{t('set_max_tokens')}</label>
                      <select
                        className="input font-mono text-sm"
                        value={form.max_tokens ?? 4096}
                        onChange={e => updateForm(providerKey, 'max_tokens', parseInt(e.target.value))}>
                        {[256, 512, 1024, 2048, 4096, 8192, 16384, 32768].map(v => (
                          <option key={v} value={v}>{v.toLocaleString()}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {/* Route (only for OpenRouter) */}
                  {providerKey === 'openrouter' && (
                    <div>
                      <label className="label">Route</label>
                      <select
                        className="input font-mono text-sm"
                        value={form.route || 'openrouter/free'}
                        onChange={e => updateForm(providerKey, 'route', e.target.value)}>
                        {OPENROUTER_ROUTES.map(r => (
                          <option key={r.value} value={r.value}>{r.label}</option>
                        ))}
                      </select>
                      <p className="text-xs text-slate-muted mt-1">
                        Определяет стратегию маршрутизации запросов OpenRouter.
                      </p>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex justify-end gap-3 pt-2 border-t border-slate-border">
                    <button className="btn-ghost" onClick={() => setEditing(null)}>{t('cancel')}</button>
                    <button
                      className="btn-primary"
                      disabled={saving === providerKey}
                      onClick={() => handleSave(providerKey)}>
                      {saving === providerKey ? <><Spinner /> {t('loading')}</> : `✓ ${t('save')}`}
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Quickstart hint */}
      <div className="mt-8 p-5 rounded-xl border border-slate-border/50 bg-ink-soft">
        <p className="text-sm font-medium text-white mb-3">🚀 Быстрый старт / Quick start</p>
        <ol className="space-y-1.5 text-sm text-slate-muted list-decimal list-inside">
          <li>Нажмите <b className="text-white">✎ Редактировать</b> для нужного провайдера</li>
          <li>Введите <b className="text-white">API ключ</b> и выберите модель</li>
          <li>Нажмите <b className="text-white">⚡ Тест связи</b> для проверки</li>
          <li>Нажмите <b className="text-white">Сделать активным</b> для переключения</li>
        </ol>
        <div className="mt-4 pt-4 border-t border-slate-border/30">
          <p className="text-sm text-slate-muted mb-2">🌱 {lang === 'ru' ? 'Демо-данные' : 'Demo Data'}</p>
          <button className="btn-primary text-xs" onClick={handleSeed} disabled={seeding}>
            {seeding ? <Spinner /> : `📥 ${lang === 'ru' ? 'Загрузить примеры для всех процессов' : 'Load examples for all processes'}`}
          </button>
        </div>
      </div>
    </div>
  );
}
