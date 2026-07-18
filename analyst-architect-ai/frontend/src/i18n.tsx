import React, { createContext, useContext, useState, useCallback } from 'react';

export type Lang = 'ru' | 'en';

// ── Translation dictionary ────────────────────────────────────────────────────
const T = {
  // ── Nav ──────────────────────────────────────────────────────────────────
  nav_documents:   { ru: 'Документы',    en: 'Documents' },
  nav_reviews:     { ru: 'Рецензии',     en: 'Reviews' },
  nav_batch_reviews: { ru: 'Пакетная рецензия', en: 'Batch Review' },
  nav_kb:          { ru: 'База знаний',  en: 'Knowledge Base' },
  nav_studio:      { ru: 'Арх. студия',  en: 'Arch Studio' },
  nav_memory:      { ru: 'Память',       en: 'Memory' },
  nav_audit:       { ru: 'Аудит',        en: 'Audit' },
  nav_economics:   { ru: 'Экономика',    en: 'Economics' },
  nav_settings:    { ru: 'Настройки',    en: 'Settings' },
  nav_users:       { ru: 'Пользователи', en: 'Users' },
  nav_risks:       { ru: 'Риски',        en: 'Risks' },
  nav_lessons:     { ru: 'Уроки',        en: 'Lessons' },

  // ── Common ────────────────────────────────────────────────────────────────
  cancel:          { ru: 'Отмена',       en: 'Cancel' },
  save:            { ru: 'Сохранить',    en: 'Save' },
  create:          { ru: 'Создать',      en: 'Create' },
  add:             { ru: 'Добавить',     en: 'Add' },
  delete:          { ru: 'Удалить',      en: 'Delete' },
  search:          { ru: 'Найти',        en: 'Search' },
  all:             { ru: 'Все',          en: 'All' },
  loading:         { ru: 'Загрузка…',   en: 'Loading…' },
  error_loading:   { ru: 'Ошибка загрузки', en: 'Loading error' },
  copy:            { ru: 'Копировать',   en: 'Copy' },
  copied:          { ru: '✓ Скопировано', en: '✓ Copied' },
  export:          { ru: 'Экспорт',      en: 'Export' },
  refresh:         { ru: '↺ Обновить',   en: '↺ Refresh' },
  close:           { ru: 'Закрыть',      en: 'Close' },
  needs_review:    { ru: '⚠ Требует проверки', en: '⚠ Needs Review' },
  confidence_high: { ru: '↑ Высокая',   en: '↑ High' },
  confidence_med:  { ru: '~ Средняя',   en: '~ Medium' },
  confidence_low:  { ru: '↓ Низкая',    en: '↓ Low' },
  sev_high:        { ru: 'ВЫСОКИЙ',     en: 'HIGH' },
  sev_medium:      { ru: 'СРЕДНИЙ',     en: 'MEDIUM' },
  sev_low:         { ru: 'НИЗКИЙ',      en: 'LOW' },

  // ── Documents page ────────────────────────────────────────────────────────
  doc_title:       { ru: 'Документы',   en: 'Documents' },
  doc_subtitle:    { ru: 'ТЗ, BRD, User Stories и базовые спецификации', en: 'TZ, BRD, User Stories and base specifications' },
  doc_new:         { ru: '+ Новый документ', en: '+ New Document' },
  doc_name:        { ru: 'Название',    en: 'Title' },
  doc_type:        { ru: 'Тип документа', en: 'Document Type' },
  doc_project:     { ru: 'Проект (опционально)', en: 'Project (optional)' },
  doc_text:        { ru: 'Текст документа', en: 'Document Text' },
  doc_empty:       { ru: 'Нет документов', en: 'No documents' },
  doc_empty_sub:   { ru: 'Создайте первый документ для анализа', en: 'Create your first document for analysis' },
  doc_review_btn:  { ru: '🔍 Рецензия', en: '🔍 Review' },
  doc_chars:       { ru: 'символов',    en: 'characters' },
  doc_created:     { ru: 'Документ создан', en: 'Document created' },
  doc_create_err:  { ru: 'Ошибка создания', en: 'Creation error' },
  doc_review_done: { ru: 'Рецензия создана', en: 'Review created' },
  doc_review_err:  { ru: 'Ошибка рецензии', en: 'Review error' },

  // ── Reviews page ──────────────────────────────────────────────────────────
  rev_title:       { ru: 'Рецензии',    en: 'Reviews' },
  rev_subtitle:    { ru: 'История AI-рецензий технических заданий', en: 'History of AI-generated document reviews' },
  rev_filter_all:  { ru: 'Все',         en: 'All' },
  rev_filter_ok:   { ru: '✓ Без замечаний', en: '✓ No issues' },
  rev_filter_nr:   { ru: '⚠ Требует проверки', en: '⚠ Needs review' },
  rev_empty:       { ru: 'Нет рецензий', en: 'No reviews' },
  rev_empty_sub:   { ru: 'Запустите рецензию из раздела Документы', en: 'Run a review from the Documents section' },
  rev_collapse:    { ru: '‹ Свернуть',  en: '‹ Collapse' },
  rev_risks:       { ru: 'Риски',       en: 'Risks' },
  rev_questions:   { ru: 'Вопросы заказчику', en: 'Questions for client' },
  rev_criteria:    { ru: 'Критерии приёмки', en: 'Acceptance Criteria' },
  rev_missing:     { ru: 'Отсутствующие требования', en: 'Missing Requirements' },
  rev_arch_risks:  { ru: 'Архитектурные риски', en: 'Architecture Risks' },
  rev_lessons:     { ru: 'Уроки',       en: 'Lessons' },
  rev_summary:     { ru: 'Резюме',      en: 'Summary' },
  rev_metadata:    { ru: 'Метаданные',  en: 'Metadata' },
  rev_confidence:  { ru: 'Уверенность', en: 'Confidence' },

  // ── KB page ───────────────────────────────────────────────────────────────
  kb_title:        { ru: 'База знаний', en: 'Knowledge Base' },
  kb_subtitle:     { ru: 'RAG-поиск по корпоративным документам', en: 'RAG search across corporate documents' },
  kb_ask_tab:      { ru: '💬 Задать вопрос', en: '💬 Ask Question' },
  kb_docs_tab:     { ru: '📚 Документы', en: '📚 Documents' },
  kb_history_tab:  { ru: '🕐 История',  en: '🕐 History' },
  kb_question:     { ru: 'Задайте вопрос', en: 'Ask a question' },
  kb_placeholder:  { ru: 'Какой SLA установлен на ответы?', en: 'What is the SLA for responses?' },
  kb_ask_btn:      { ru: '↵ Спросить', en: '↵ Ask' },
  kb_searching:    { ru: 'Ищу в базе знаний…', en: 'Searching knowledge base…' },
  kb_sources:      { ru: 'Источники',  en: 'Sources' },
  kb_empty:        { ru: 'База знаний пуста', en: 'Knowledge base is empty' },
  kb_empty_sub:    { ru: 'Добавьте документы для RAG-поиска', en: 'Add documents for RAG search' },
  kb_reindex:      { ru: '↺ Переиндексировать', en: '↺ Reindex' },
  kb_indexed:      { ru: 'Переиндексировано', en: 'Reindexed' },
  kb_docs_count:   { ru: 'документов в базе', en: 'documents in base' },
  kb_no_history:   { ru: 'Нет истории', en: 'No history' },
  kb_no_hist_sub:  { ru: 'Вопросы появятся здесь', en: 'Questions will appear here' },
  kb_answered:     { ru: '✓ Отвечено', en: '✓ Answered' },
  kb_no_data:      { ru: '⚠ Нет данных', en: '⚠ No data' },
  kb_new_doc:      { ru: 'Новый KB-документ', en: 'New KB Document' },
  kb_content:      { ru: 'Содержимое', en: 'Content' },
  kb_added:        { ru: 'Документ добавлен в базу знаний', en: 'Document added to knowledge base' },

  // ── Arch Studio ───────────────────────────────────────────────────────────
  studio_title:    { ru: 'Архитектурная студия', en: 'Architecture Studio' },
  studio_subtitle: { ru: 'Рекомендации архитектуры, ADR, API Design, диаграммы и спецификации', en: 'Architecture recommendations, ADR, API Design, diagrams and specifications' },
  studio_select:   { ru: 'Выберите документ', en: 'Select document' },
  studio_none:     { ru: 'Нет документов', en: 'No documents' },
  studio_empty:    { ru: 'Выберите документ', en: 'Select a document' },
  studio_empty_sub:{ ru: 'Затем запустите нужный генератор', en: 'Then run the desired generator' },
  studio_arch_btn: { ru: '🏛 Рекомендовать архитектуру', en: '🏛 Recommend Architecture' },
  studio_adr_btn:  { ru: '📋 Создать ADR', en: '📋 Create ADR' },
  studio_api_btn:  { ru: '🔌 Создать API Spec', en: '🔌 Create API Spec' },
  studio_diag_btn: { ru: '🗺 Сгенерировать диаграммы', en: '🗺 Generate Diagrams' },
  studio_urs_btn:  { ru: '📝 URS', en: '📝 URS' },
  studio_srs_btn:  { ru: '📄 SRS', en: '📄 SRS' },
  studio_pattern:  { ru: 'Рекомендованный паттерн', en: 'Recommended Pattern' },
  studio_rationale:{ ru: 'Обоснование', en: 'Rationale' },
  studio_alts:     { ru: 'Альтернативы', en: 'Alternatives' },
  studio_integr:   { ru: 'Интеграции', en: 'Integrations' },
  studio_analyzing:{ ru: 'Анализирую архитектуру…', en: 'Analyzing architecture…' },
  studio_generating:{ ru: 'Генерирую диаграммы…', en: 'Generating diagrams…' },
  studio_no_diags: { ru: 'Диаграммы не сгенерированы', en: 'No diagrams generated' },

  // ── Memory page ───────────────────────────────────────────────────────────
  mem_title:       { ru: 'Фреймворк памяти', en: 'Memory Framework' },
  mem_subtitle:    { ru: 'Семантическая, эпизодическая, решенческая, рисковая и требовательная память', en: 'Semantic, episodic, decision, risk and requirement memory' },
  mem_recent:      { ru: '🕐 Последние', en: '🕐 Recent' },
  mem_search_tab:  { ru: '🔍 Поиск', en: '🔍 Search' },
  mem_store_tab:   { ru: '+ Добавить', en: '+ Add' },
  mem_dedup:       { ru: '↺ Дедупликация', en: '↺ Deduplicate' },
  mem_all_types:   { ru: 'Все типы', en: 'All types' },
  mem_empty:       { ru: 'Память пуста', en: 'Memory is empty' },
  mem_empty_sub:   { ru: 'Добавьте первый элемент памяти', en: 'Add your first memory item' },
  mem_type:        { ru: 'Тип памяти', en: 'Memory Type' },
  mem_content:     { ru: 'Содержимое', en: 'Content' },
  mem_content_ph:  { ru: 'Описание знания, решения или риска...', en: 'Description of knowledge, decision or risk...' },
  mem_tags:        { ru: 'Теги (через запятую)', en: 'Tags (comma-separated)' },
  mem_project:     { ru: 'Проект', en: 'Project' },
  mem_saved:       { ru: 'Сохранено в памяти', en: 'Saved to memory' },
  mem_save_err:    { ru: 'Ошибка сохранения', en: 'Save error' },
  mem_new:         { ru: 'Новый элемент памяти', en: 'New Memory Item' },
  mem_relevant:    { ru: 'релевантно', en: 'relevant' },
  mem_sem:         { ru: '🔷 Семантическая', en: '🔷 Semantic' },
  mem_epi:         { ru: '📅 Эпизодическая', en: '📅 Episodic' },
  mem_dec:         { ru: '⚖️ Решения', en: '⚖️ Decisions' },
  mem_risk:        { ru: '⚠️ Риски', en: '⚠️ Risks' },
  mem_req:         { ru: '📋 Требования', en: '📋 Requirements' },

  // ── Audit page ────────────────────────────────────────────────────────────
  audit_title:     { ru: 'Аудит-центр', en: 'Audit Center' },
  audit_subtitle:  { ru: 'Полная история всех AI-операций', en: 'Full history of all AI operations' },
  audit_total:     { ru: 'Всего операций', en: 'Total operations' },
  audit_ok:        { ru: '✓ Успешно',  en: '✓ Successful' },
  audit_review:    { ru: '⚠ На проверку', en: '⚠ Needs review' },
  audit_errors:    { ru: '✗ Ошибки',   en: '✗ Errors' },
  audit_avg_time:  { ru: 'Среднее время ответа', en: 'Avg response time' },
  audit_nr_pct:    { ru: 'Требует проверки', en: 'Needs review rate' },
  audit_all_ops:   { ru: 'Все операции', en: 'All operations' },
  audit_all_stat:  { ru: 'Все статусы', en: 'All statuses' },
  audit_empty:     { ru: 'Нет записей аудита', en: 'No audit records' },
  audit_empty_sub: { ru: 'Операции появятся после первого запроса', en: 'Operations will appear after first request' },
  audit_time:      { ru: 'Время',      en: 'Time' },
  audit_action:    { ru: 'Операция',   en: 'Operation' },
  audit_status:    { ru: 'Статус',     en: 'Status' },
  audit_duration:  { ru: 'Время (мс)', en: 'Duration (ms)' },
  audit_err_col:   { ru: 'Ошибка',     en: 'Error' },
  audit_prev:      { ru: '← Назад',    en: '← Prev' },
  audit_next:      { ru: 'Вперёд →',   en: 'Next →' },
  audit_page:      { ru: 'Страница',   en: 'Page' },
  audit_input:     { ru: 'Входные данные', en: 'Input data' },
  audit_output:    { ru: 'Результат',  en: 'Result' },

  // ── Settings page ─────────────────────────────────────────────────────────
  set_title:       { ru: 'Настройки',  en: 'Settings' },
  set_subtitle:    { ru: 'Конфигурация LLM-провайдеров и API ключей', en: 'LLM provider configuration and API keys' },
  set_providers:   { ru: 'AI Провайдеры', en: 'AI Providers' },
  set_active:      { ru: 'Активный провайдер', en: 'Active Provider' },
  set_activate:    { ru: 'Сделать активным', en: 'Set Active' },
  set_activated:   { ru: 'Активирован', en: 'Activated' },
  set_edit:        { ru: '✎ Редактировать', en: '✎ Edit' },
  set_test:        { ru: '⚡ Тест связи', en: '⚡ Test Connection' },
  set_api_key:     { ru: 'API Ключ',   en: 'API Key' },
  set_api_key_ph:  { ru: 'sk-... (оставьте пустым, чтобы не менять)', en: 'sk-... (leave empty to keep existing)' },
  set_model:       { ru: 'Модель',     en: 'Model' },
  set_base_url:    { ru: 'Base URL (опционально)', en: 'Base URL (optional)' },
  set_temperature: { ru: 'Температура', en: 'Temperature' },
  set_max_tokens:  { ru: 'Макс. токенов', en: 'Max Tokens' },
  set_saved:       { ru: 'Настройки сохранены', en: 'Settings saved' },
  set_save_err:    { ru: 'Ошибка сохранения', en: 'Save error' },
  set_test_ok:     { ru: 'Подключение работает', en: 'Connection works' },
  set_test_err:    { ru: 'Ошибка подключения', en: 'Connection error' },
  set_no_key:      { ru: 'API ключ не задан', en: 'No API key set' },
  set_masked:      { ru: 'ключ задан', en: 'key set' },
  set_proxyapi_info: { ru: 'ProxyAPI — OpenAI-совместимый прокси с поддержкой Claude. Документация: proxyapi.ru', en: 'ProxyAPI — OpenAI-compatible proxy supporting Claude. Docs: proxyapi.ru' },
  set_openai_info: { ru: 'Официальный API OpenAI. Поддерживает GPT-4o, GPT-4-turbo и другие модели.', en: 'Official OpenAI API. Supports GPT-4o, GPT-4-turbo and other models.' },
  set_anthropic_info: { ru: 'Официальный API Anthropic. Поддерживает Claude 3.5 Sonnet, Claude 3 Opus и другие.', en: 'Official Anthropic API. Supports Claude 3.5 Sonnet, Claude 3 Opus and more.' },
  set_current:     { ru: 'Текущий активный', en: 'Currently active' },
  set_openrouter_info: { ru: 'OpenRouter — универсальный шлюз к 200+ LLM. Поддерживает Claude, GPT, Gemini, Llama, DeepSeek и другие. По умолчанию — openrouter/free (только бесплатные модели).', en: 'OpenRouter — unified gateway to 200+ LLMs. Supports Claude, GPT, Gemini, Llama, DeepSeek and more. Default: openrouter/free (free models only).' },
  set_ollama_info: { ru: 'Ollama — локальный запуск моделей (Llama, Qwen, Mistral, DeepSeek и др.) на вашей машине или сервере внутри контура. API-ключ не требуется. Запросы не покидают сеть — подходит для конфиденциальных проектов (NDA, банковские данные).', en: 'Ollama — run models (Llama, Qwen, Mistral, DeepSeek, etc.) locally on your machine or in-network server. No API key needed. Requests never leave your network — suitable for confidential projects (NDA, banking data).' },
  set_local_badge:  { ru: '🔒 Локальный контур', en: '🔒 Local network only' },
  set_ollama_no_models: { ru: 'Нет скачанных моделей. Выполните: ollama pull qwen2.5:14b-instruct', en: 'No models downloaded. Run: ollama pull qwen2.5:14b-instruct' },
  set_ollama_models_err: { ru: 'Не удалось получить список моделей — проверьте, что Ollama запущена', en: 'Could not fetch model list — check that Ollama is running' },

  // ── Document detail ───────────────────────────────────────────────────────
  det_back:        { ru: '← Документы', en: '← Documents' },
  det_source:      { ru: 'Исходный текст', en: 'Source Text' },
  det_tab_text:    { ru: '📄 Текст',    en: '📄 Text' },
  det_tab_review:  { ru: '🔍 Рецензия', en: '🔍 Review' },
  det_tab_arch:    { ru: '🏛 Архитектура', en: '🏛 Architecture' },
  det_tab_adr:     { ru: '📋 ADR',      en: '📋 ADR' },
  det_tab_api:     { ru: '🔌 API',      en: '🔌 API' },
  det_tab_diag:    { ru: '🗺 Диаграммы', en: '🗺 Diagrams' },
  det_tab_specs:   { ru: '📝 Спецификации', en: '📝 Specifications' },
  det_run:         { ru: 'Запустить:',  en: 'Run:' },
  det_analyzing:   { ru: 'AI анализирует документ…', en: 'AI is analyzing the document…' },
  det_run_review:  { ru: 'Нажмите «Рецензия» для запуска AI-анализа', en: 'Click "Review" to start AI analysis' },
  det_run_arch:    { ru: 'Нажмите «Архитектура» для генерации', en: 'Click "Architecture" to generate' },
  det_run_gen:     { ru: 'Нажмите для генерации', en: 'Click to generate' },
  det_swagger:     { ru: 'Открыть в Swagger Editor ↗', en: 'Open in Swagger Editor ↗' },
  det_context:     { ru: 'Контекст',   en: 'Context' },
  det_problem:     { ru: 'Проблема',   en: 'Problem' },
  det_decision:    { ru: 'Решение',    en: 'Decision' },
  det_rejected:    { ru: 'Отклонённые альтернативы', en: 'Rejected alternatives' },
  det_positive:    { ru: 'Позитивные последствия', en: 'Positive consequences' },
  det_negative:    { ru: 'Негативные последствия', en: 'Negative consequences' },
  det_integrations:{ ru: 'Интеграции', en: 'Integrations' },
  det_arch_risks:  { ru: 'Архитектурные риски', en: 'Architecture Risks' },

  // ── Risk Catalog ──────────────────────────────────────────────────────────
  risk_title:      { ru: 'Каталог рисков', en: 'Risk Catalog' },
  risk_subtitle:   { ru: 'Управление рисками проектов', en: 'Project risk management' },
  risk_new:        { ru: '+ Новый риск', en: '+ New Risk' },
  risk_empty:      { ru: 'Рисков нет', en: 'No risks' },
  risk_empty_sub:  { ru: 'Риски автоматически добавляются из рецензий', en: 'Risks are auto-added from reviews' },
  risk_saved:      { ru: 'Риск сохранён', en: 'Risk saved' },
  risk_deleted:    { ru: 'Риск удалён', en: 'Risk deleted' },
  risk_edit:       { ru: 'Редактировать риск', en: 'Edit Risk' },
  risk_create:     { ru: 'Новый риск', en: 'New Risk' },
  risk_title_f:    { ru: 'Название', en: 'Title' },
  risk_desc:       { ru: 'Описание', en: 'Description' },
  risk_prob:       { ru: 'Вероятность (1-5)', en: 'Probability (1-5)' },
  risk_impact:     { ru: 'Влияние (1-5)', en: 'Impact (1-5)' },
  risk_severity:   { ru: 'Серьёзность', en: 'Severity' },
  risk_category:   { ru: 'Категория', en: 'Category' },
  risk_status:     { ru: 'Статус', en: 'Status' },
  risk_owner:      { ru: 'Ответственный', en: 'Owner' },
  risk_mitigation: { ru: 'Меры', en: 'Mitigation' },
  risk_source:     { ru: 'Источник', en: 'Source' },
  risk_project:    { ru: 'Проект', en: 'Project' },
  risk_stats:      { ru: '📊 Статистика', en: '📊 Statistics' },
  risk_cat_tech:   { ru: 'Технический', en: 'Technical' },
  risk_cat_proc:   { ru: 'Процессный', en: 'Process' },
  risk_cat_biz:    { ru: 'Бизнес', en: 'Business' },
  risk_cat_sec:    { ru: 'Безопасность', en: 'Security' },
  risk_st_open:    { ru: 'Открыт', en: 'Open' },
  risk_st_mit:     { ru: 'Смягчён', en: 'Mitigated' },
  risk_st_closed:  { ru: 'Закрыт', en: 'Closed' },
  risk_st_acc:     { ru: 'Принят', en: 'Accepted' },
  risk_st_reopen:  { ru: 'Переоткрыт', en: 'Reopened' },
  risk_sev_low:    { ru: 'Низкая', en: 'Low' },
  risk_sev_med:    { ru: 'Средняя', en: 'Medium' },
  risk_sev_high:   { ru: 'Высокая', en: 'High' },
  risk_sev_crit:   { ru: 'Критическая', en: 'Critical' },
  risk_total:      { ru: 'Всего', en: 'Total' },
  risk_export_csv: { ru: '📥 CSV', en: '📥 CSV' },

  // ── Lessons ────────────────────────────────────────────────────────────────
  less_title:      { ru: 'Уроки проектов', en: 'Project Lessons' },
  less_subtitle:   { ru: 'База знаний из опыта выполнения проектов', en: 'Knowledge base from project experience' },
  less_new:        { ru: '+ Новый урок', en: '+ New Lesson' },
  less_empty:      { ru: 'Нет уроков', en: 'No lessons' },
  less_empty_sub:  { ru: 'Уроки автоматически добавляются из рецензий', en: 'Lessons are auto-added from reviews' },
  less_saved:      { ru: 'Урок сохранён', en: 'Lesson saved' },
  less_deleted:    { ru: 'Урок удалён', en: 'Lesson deleted' },
  less_edit:       { ru: 'Редактировать урок', en: 'Edit Lesson' },
  less_create:     { ru: 'Новый урок', en: 'New Lesson' },
  less_title_f:    { ru: 'Название', en: 'Title' },
  less_desc:       { ru: 'Описание', en: 'Description' },
  less_category:   { ru: 'Категория', en: 'Category' },
  less_impact:     { ru: 'Тип влияния', en: 'Impact Type' },
  less_impact_pos: { ru: 'Позитивный', en: 'Positive' },
  less_impact_neg: { ru: 'Негативный', en: 'Negative' },
  less_root_cause: { ru: 'Корневая причина', en: 'Root Cause' },
  less_recommend:  { ru: 'Рекомендация', en: 'Recommendation' },
  less_source:     { ru: 'Источник', en: 'Source' },
  less_project:    { ru: 'Проект', en: 'Project' },
  less_cat_tech:   { ru: 'Технология', en: 'Technology' },
  less_cat_proc:   { ru: 'Процесс', en: 'Process' },
  less_cat_comm:   { ru: 'Коммуникация', en: 'Communication' },
  less_cat_est:    { ru: 'Оценка', en: 'Estimation' },
  less_export_csv: { ru: '📥 CSV', en: '📥 CSV' },

  // ── Dashboard ──────────────────────────────────────────────────────────────
  nav_dashboard:     { ru: 'Дашборд',    en: 'Dashboard' },
  dash_title:        { ru: 'Дашборд',    en: 'Dashboard' },
  dash_subtitle:     { ru: 'Сводная панель аналитики и метрик', en: 'Analytics and metrics overview' },
  dash_empty:        { ru: 'Нет данных', en: 'No data' },
  dash_empty_sub:    { ru: 'Начните с создания документов и рецензий', en: 'Start by creating documents and reviews' },
  dash_docs:         { ru: 'Документов', en: 'Documents' },
  dash_reviews:      { ru: 'Рецензий',   en: 'Reviews' },
  dash_audit:        { ru: 'Операций',   en: 'Operations' },
  dash_projects:     { ru: 'Проектов',   en: 'Projects' },
  dash_need_review_rate: { ru: 'Требуют проверки', en: 'Needs review rate' },
  dash_avg_duration: { ru: 'Ср. время ответа', en: 'Avg response time' },
  dash_recent:       { ru: 'Последняя активность', en: 'Recent Activity' },
  dash_no_activity:  { ru: 'Нет активности', en: 'No activity' },
  dash_no_activity_sub: { ru: 'Операции появятся после первого запроса', en: 'Activity will appear after the first request' },
  dash_avg_roi:      { ru: 'Ср. ROI (12 мес)', en: 'Avg ROI (12 mo)' },
  dash_avg_payback:  { ru: 'Ср. окупаемость', en: 'Avg payback' },
  dash_months:       { ru: 'мес',          en: 'mo' },

  // ── Layout ────────────────────────────────────────────────────────────────
  layout_ai_copilot: { ru: 'AI Copilot', en: 'AI Copilot' },
} as const;

type TKey = keyof typeof T;

// ── Context ───────────────────────────────────────────────────────────────────
interface I18nCtx {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: TKey) => string;
}

const I18nContext = createContext<I18nCtx>({
  lang: 'ru',
  setLang: () => {},
  t: (key) => T[key]?.ru ?? key,
});

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const stored = (localStorage.getItem('lang') as Lang) || 'ru';
  const [lang, setLangState] = useState<Lang>(stored);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    localStorage.setItem('lang', l);
  }, []);

  const t = useCallback((key: TKey): string => {
    return T[key]?.[lang] ?? T[key]?.ru ?? key;
  }, [lang]);

  return (
    <I18nContext.Provider value={{ lang, setLang, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  return useContext(I18nContext);
}

// ── Language Toggle Button ─────────────────────────────────────────────────────
export function LangToggle() {
  const { lang, setLang } = useI18n();
  return (
    <button
      onClick={() => setLang(lang === 'ru' ? 'en' : 'ru')}
      title={lang === 'ru' ? 'Switch to English' : 'Переключить на русский'}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-border 
                 hover:border-accent/40 hover:bg-accent/10 transition-all duration-200
                 text-xs font-medium text-slate-muted hover:text-accent"
    >
      <span className="text-base leading-none">{lang === 'ru' ? '🇬🇧' : '🇷🇺'}</span>
      <span className="font-mono">{lang === 'ru' ? 'EN' : 'RU'}</span>
    </button>
  );
}
