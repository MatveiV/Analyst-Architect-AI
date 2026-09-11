# План: актуализация документации с C4-диаграммами на Mermaid

## Контекст и обоснование

Текущая документация **отстала от кода на 3 фазы разработки** (Phases 1–3). Изучение выявило системные расхождения:

| Факт | В документации | В коде (реально) |
|---|---|---|
| Модели БД | 17 | **24** |
| Тестов | 63 | **146** |
| LLM-провайдеры | 3 (Anthropic/OpenAI/ProxyAPI) | **5** (+OpenRouter, +Ollama) |
| Роутеры | ~8 | **15** |
| Alembic миграции | — (roadmap) | **6** (выполнено) |
| Batch-review | — (roadmap) | **выполнено** |
| Kroki (локальный рендер диаграмм) | не упомянут | есть, порт 8001 |
| FAISS / sentence-transformers | не упомянут | есть, 2 индекса |
| Версионирование диаграмм + rollback | не упомянут | есть (migration 0002) |
| KB-autoindexing | не упомянут | есть (migration 0006) |
| `ENFORCE_LOCAL_ONLY` (air-gapped) | не упомянут | есть |

Существующие C4-диаграммы в `user-guide` (L1–L3) и `admin-guide` (deployment) нарисованы под старую архитектуру — без Kroki, Ollama, FAISS, модуля экономики, batch-review.

## Область изменений (5 файлов, обновление на месте, RU + EN синхронно)

1. `README.md`
2. `docs/user-guide-ru.md`
3. `docs/user-guide-en.md`
4. `docs/admin-guide-ru.md`
5. `docs/admin-guide-en.md`

---

## Детальный план по файлам

### 1. `README.md` — актуализация фактов + краткие C4

**Обновления текста:**
- Раздел «Архитектура системы»: дерево обновить — `models/` → **24 модели**, `services/` → 21 модуль (добавить `rag_engine`, `embeddings`, `diagram_engine`, `task_estimator`, `economics_service`, `batch_review_service`, `kb_autoindex`, `review_to_catalog`, `audit_service`, `usage_economics_service`, `adr_generator`, `architecture_engine`, `doc_generator`, `memory_service`, `standards_seed`), `api/routers/` → 15 роутеров (добавить `batch_reviews`, `risk_catalog`, `lessons`, `standards`, `build_projects`, `dashboard`), упомянуть `alembic/versions/` → 6 миграций, `services/llm_client.py` → 5 провайдеров.
- Раздел «Роли»: матрица доступа актуализирована (добавить batch-reviews, risk-catalog, lessons, standards — для analyst+; settings — architect+; seed — admin).
- Раздел «Конфигурация (.env)»: расширить таблицу — `LLM_PROVIDER` ∈ `anthropic|openai|proxyapi|openrouter|ollama`, добавить строки `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `ENFORCE_LOCAL_ONLY`, `DIAGRAM_RENDERER_URL`, `DIAGRAM_RENDERER_TIMEOUT`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_COST_USD_TO_RUB`.
- Раздел «API эндпоинты»: добавить группы — **Batch-reviews** (`/batch-reviews`), **Risk-catalog** (`/risk-catalog`), **Lessons** (`/lessons`), **Standards** (`/standards`), расширить **Dashboard** (`/dashboard/stats`, `/recent-activity`, `/stats-by-provider`, `/actual-usage`), расширить **Economics** (`/export/pdf`, `use_actual_llm_cost`), добавить **Diagrams** (`/generate-{c4,uml,erd}`, `/{id}/versions`, `/{id}/rollback/{n}`).
- Раздел «Тестирование»: таблицу категорий актуализировать до 146 (Epic A diagrams, Epic B standards, Epic C ollama, Phase 2 batch/coverage/diff, Phase 3 kb-autoindex/usage-economics).
- Раздел «Roadmap»: пометить v1.1 (Alembic+batch) и v1.2 (Vite+OpenRouter) как **выполнено**, оставить v1.3 / v2.0.

**Новые диаграммы (встраиваются в раздел «Архитектура системы»):**
- **C4 Level 1 — Context** (mermaid `C4Context`): 3 Person (analyst/architect/admin), System AnalystGuru, `System_Ext` ×5: Anthropic / OpenAI / ProxyAPI / OpenRouter / Ollama(local), Kroki. Rel-связи с подписями протоколов. Отметить `ENFORCE_LOCAL_ONLY`.
- **C4 Level 2 — Container** (mermaid `C4Container`): React SPA (Vite) → FastAPI → SQLite/PostgreSQL (ContainerDb) + FAISS-индексы (in-memory) + Kroki (Container) + Ollama (Container, optional profile). Rel: HTTPS/REST, SQLAlchemy async, FAISS IP-index, Kroki render.

### 2. `docs/user-guide-ru.md` + `docs/user-guide-en.md` — замена устаревших C4 (секция «Архитектура системы (C4)»)

**C4 Level 1 — Context** (заменить строки ~64–86): добавить `System_Ext(kroki)`, `System_Ext(ollama, "Ollama (локальный LLM)")`, OpenRouter. Подписи Rel уточнить. EN-версия — тот же набор, английские лейблы.

**C4 Level 2 — Container** (заменить строки ~90–106): 
- Container: React SPA (Vite + TS + Tailwind)
- Container: FastAPI (Python 3.11, SQLAlchemy async, 15 роутеров, JWT RBAC)
- ContainerDb: SQLite/PostgreSQL (24 модели)
- Container: Kroki (локальный рендер PlantUML/Mermaid → SVG/PNG)
- Container_Ext: Ollama (локальный LLM, опционально через `--profile local-llm`)
- System_Ext: облачные LLM (Anthropic/OpenAI/ProxyAPI/OpenRouter)
- Rel-связи с реальными портами (8000, 8001, 11434) и пометкой `ENFORCE_LOCAL_ONLY` блокирует внешние вызовы.

**C4 Level 3 — Component** (заменить строки ~110–136): расширить `Container_Boundary(backend)` — добавить:
- Component: Documents / Reviews / KB / Memory / **Batch Reviews** / **Diagrams (versioning)** / **Standards** / **Risk Catalog** / **Lessons** / **Build Projects (economics)** / Dashboard / Audit / Settings / Auth роутеры
- Component (services): AI Reviewer (reasoning modes), RAG Engine (FAISS + sentence-transformers), Diagram Engine (Kroki), Economics Service, Task Estimator, KB Autoindex, Memory Service, Audit Service (`with_audit`)
- ComponentDb: SQLite/PostgreSQL
- Rel-связи: роутер→зависимости (require_*), роутер→сервис, сервис→БД, RAG→FAISS, Diagram Engine→Kroki.

**C4 Level 4 — Code (НОВЫЙ)** (добавить после L3): mermaid `classDiagram` для ключевого сервиса — **AI Reviewer + Audit interaction** (классы `LLMClient`, `AIReviewer`, `ReasoningModes` (direct/cot/react), `AuditService.with_audit()`, `SafeFallbackReview`) ИЛИ альтернативно диаграмма потоков RAG. Выберу AI Reviewer как наиболее показательный (показывает reasoning modes + audit wrapping + fallback — это ядро системы).

> Примечание: существующие sequence/activity/state/class диаграммы в секции 14 user-guide (строки ~497–600+) — **не трогаю**, они корректны концептуально; обновляются только C4-блоки секции 2.

### 3. `docs/admin-guide-ru.md` + `docs/admin-guide-en.md` — обновление инфраструктурных диаграмм

**Deployment Diagram** (заменить строки ~350–376): добавить в `Docker Compose` subgraph — `Kroki["yuzutech/kroki:0.25\nПорт 8001\nЛокальный рендер диаграмм"]`, `Ollama["ollama/ollama\nПорт 11434\nПрофиль local-llm (опционально)"]`, обновить FastAPI-узел (пометить 15 роутеров, RBAC, FAISS, Kroki-клиент), обновить External subgraph (5 провайдеров + OpenRouter). Добавить отдельный узел/примечание про `ENFORCE_LOCAL_ONLY=true` → блокирует все исходящие внешние вызовы (air-gapped режим). Volumes: `./data` (SQLite), `ollama_models` (named volume).

**Sequence: JWT + RBAC** (строки ~380+): по необходимости точечно дополнить шаг LLM-выбора провайдера через `/settings/providers` (DB-backed `ProviderSettings`), если это уместно без раздувания.

### Принципы оформления диаграмм
- Все mermaid-блоки используют **кириллицу** в лейблах (RU-версии) и английские (EN-версии) — mermaid `C4*` поддерживает UTF-8.
- Единый стиль именования узлов (`camelCase` id, человекочитаемые лейблы).
- Реальные порты и технологии в подписях (HTTP/JSON, SQLAlchemy async, FAISS IndexFlatIP, JWT Bearer).
- Соблюдается нативный синтаксис C4 (`C4Context`/`C4Container`/`C4Component`) — рендерится и Kroki, и GitHub, и mermaid.live.

## Проверка после внесения изменений
- `grep -c "mermaid"` в каждом файле — подтвердить рост числа блоков.
- Визуальная проверка синтаксиса: каждый C4-блок имеет парный `C4*`/``` и корректные `Rel()`/`Component()` вызовы.
- Сверка фактических чисел (24 модели, 146 тестов, 5 провайдеров, 15 роутеров, 6 миграций) с кодом — уже выполнена на этапе исследования.

## Что НЕ делаю (границы)
- Не создаю новых файлов (`docs/architecture.md` и т.п.) — обновление строго на месте, по выбору пользователя.
- Не трогаю концептуально верные sequence/activity/state диаграммы секции 14 user-guide.
- Не правлю `MERGE_PLAN.md`, `graduation-report.md`, `defense-script.md` (они исторические/отчётные).
- Не меняю исходный код — только документация.