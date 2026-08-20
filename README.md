# Analyst-Architect-AI

> **AI-копилот системного аналитика и архитектора решений** — объединяет функциональность
> [MatveiV/Analyst-Guru](https://github.com/MatveiV/Analyst-Guru) и расширенного прототипа
> с авторизацией/RBAC/i18n в единый продукт, дополненный **модулем экономической оценки
> и окупаемости** для приложений, создаваемых через платформу.

Цель проекта — максимально заменить рутинные обязанности аналитика и архитектора:
рецензия ТЗ, проектирование архитектуры, генерация ADR/URS/SRS/API/диаграмм, управление
знаниями команды **и теперь — расчёт бизнес-кейса (CAPEX/OPEX/ROI/срок окупаемости)**
для каждого проекта, который команда строит с помощью системы.

---

## Что нового по сравнению с исходными проектами

Этот репозиторий — результат слияния двух источников. Подробное сравнение и план
объединения — в [docs/MERGE_PLAN.md](docs/MERGE_PLAN.md). Кратко:

| Взято из | Что именно |
|---|---|
| Прототип (RBAC/i18n) | JWT-авторизация, роли admin/analyst/architect, i18n RU/EN (200+ ключей), 3-провайдерные настройки AI |
| `MatveiV/Analyst-Guru` | Reasoning-режимы (Chain-of-Thought / ReAct), Dashboard-эндпоинты, Seed-примеров через API |
| **Новое в этом репозитории** | **Модуль экономики**: build-проекты, AI-декомпозиция задач, расчёт CAPEX/OPEX/ROI/payback, план/факт, экспорт бизнес-кейса в DOCX/PDF |

---

## Архитектура системы

```
3A/
├── backend/                    # FastAPI + SQLAlchemy (async)
│   ├── app/
│   │   ├── main.py             # FastAPI app, lifespan, RBAC на роутерах
│   │   ├── config.py           # Настройки из .env (os.getenv)
│   │   ├── database.py         # async engine, Base, Alembic→create_all fallback
│   │   ├── models/             # 24 SQLAlchemy модели
│   │   ├── schemas/            # Pydantic v2 схемы
│   │   ├── services/
│   │   │   ├── llm_client.py        # 5 провайдеров: Anthropic / OpenAI / ProxyAPI / OpenRouter / Ollama
│   │   │   ├── llm_pricing.py       # Тарификация токенов по провайдерам (для usage_economics)
│   │   │   ├── ai_reviewer.py        # Рецензия ТЗ, reasoning modes (direct/cot/react)
│   │   │   ├── rag_engine.py         # Гибридный RAG (keyword 40% + semantic 60%)
│   │   │   ├── embeddings.py         # sentence-transformers all-MiniLM-L6-v2
│   │   │   ├── diagram_engine.py     # C4/UML/ERD, Kroki-рендер, версионирование
│   │   │   ├── adr_generator.py      # Генерация ADR
│   │   │   ├── architecture_engine.py # Рекомендации по архитектуре
│   │   │   ├── doc_generator.py      # URS/SRS генерация
│   │   │   ├── memory_service.py     # 5-типовой фреймворк памяти
│   │   │   ├── audit_service.py      # with_audit(): провенанс всех AI-операций
│   │   │   ├── diff_service.py       # Сравнение двух рецензий (до/после изменения ТЗ)
│   │   │   ├── task_estimator.py     # ★ AI-декомпозиция задач
│   │   │   ├── economics_service.py  # ★ CAPEX/OPEX/ROI/payback (детерминированно)
│   │   │   ├── usage_economics_service.py # ★ Факт LLM-расходов из audit_runs
│   │   │   ├── batch_review_service.py # ★ Пакетная рецензия (до 50 ТЗ)
│   │   │   ├── kb_autoindex.py       # ★ Авто-индексация URS/SRS/ADR в KB
│   │   │   ├── review_to_catalog.py  # ★ Извлечение рисков из рецензий
│   │   │   ├── standards_seed.py     # ГОСТ 34 / ISO 29148 / IEEE 830
│   │   │   ├── export_service.py     # DOCX/PDF/CSV/JSON экспорт
│   │   │   └── auth_service.py       # JWT (HS256) + bcrypt
│   │   └── api/routers/        # 16 роутеров
│   │       ├── auth.py, documents.py, reviews.py, knowledge_base.py,
│   │       │   memory.py, diagrams.py, audit.py, standards.py, settings.py
│   │       ├── build_projects.py     # ★ Экономический модуль
│   │       ├── dashboard.py          # ★ Сводная панель + actual-usage
│   │       ├── batch_reviews.py      # ★ Пакетная рецензия
│   │       ├── risk_catalog.py, lessons.py
│   │       └── seed.py               # ★ Демо-данные одной кнопкой (admin only)
│   ├── alembic/versions/       # 6 миграций (0001–0006)
│   └── tests/                  # 146 pytest тестов
├── frontend/                   # React 18 + TypeScript + Vite + Tailwind
│   └── src/pages/               # Login, Documents, DocumentDetail, Reviews,
│                                 # BatchReview, ArchStudio, KnowledgeBase, Memory,
│                                 # Audit, RiskCatalog, Lessons, Economics ★,
│                                 # Dashboard ★, Settings, Users
├── tests_data/                 # 10 тестовых ТЗ + KB-документы + вопросы
├── docs/
│   ├── MERGE_PLAN.md            # План объединения и роадмап
│   ├── user-guide-{ru,en}.md   # Руководство пользователя (C4/UML)
│   ├── admin-guide-{ru,en}.md  # Руководство администратора (deployment)
│   ├── graduation-report.md
│   └── defense-script.md
├── docker-compose.yml           # backend + frontend + kroki (+ ollama profile)
└── .env.example
```

### C4 Level 1 — Контекст системы

```mermaid
C4Context
    title Analyst-Architect-AI — Системный контекст

    Person(analyst, "Аналитик", "Рецензирует ТЗ, генерирует URS/SRS/ADR, считает экономику")
    Person(architect, "Архитектор", "Проектирует архитектуру, настраивает AI-провайдеров")
    Person(admin, "Администратор", "Управляет пользователями и демо-данными")

    System(ag, "Analyst-Architect-AI", "AI-копилот для аналитика и архитектора")

    System_Ext(claude, "Anthropic Claude", "LLM по умолчанию (claude-sonnet-4)")
    System_Ext(openai, "OpenAI", "gpt-4o")
    System_Ext(proxyapi, "ProxyAPI", "OpenAI-совместимый RU-прокси")
    System_Ext(openrouter, "OpenRouter", "Шлюз к 200+ моделям")
    System_Ext(ollama, "Ollama", "Локальный LLM (air-gapped, qwen2.5)")
    System_Ext(kroki, "Kroki", "Локальный рендер PlantUML/Mermaid → SVG/PNG")

    Rel(analyst, ag, "Работает с документами, рецензиями, экономикой")
    Rel(architect, ag, "Генерирует архитектуру, диаграммы, настраивает LLM")
    Rel(admin, ag, "Управляет пользователями, загружает seed-данные")
    Rel(ag, claude, "Вызывает LLM API", "HTTPS/REST")
    Rel(ag, openai, "Вызывает LLM API (опционально)", "HTTPS/REST")
    Rel(ag, proxyapi, "Вызывает через RU-прокси (опционально)", "HTTPS/REST")
    Rel(ag, openrouter, "Вызывает через шлюз (опционально)", "HTTPS/REST")
    Rel(ag, ollama, "Локальный LLM (без выхода в интернет)", "HTTP :11434")
    Rel(ag, kroki, "Рендер диаграмм (без выхода в интернет)", "HTTP :8001")

    UpdateRelConfig(ag, claude, "При ENFORCE_LOCAL_ONLY=true — заблокирован")
    UpdateRelConfig(ag, openai, "При ENFORCE_LOCAL_ONLY=true — заблокирован")
```

### C4 Level 2 — Контейнеры

```mermaid
C4Container
    title Analyst-Architect-AI — Контейнеры

    Person(user, "Пользователь", "analyst / architect / admin")

    Container_Boundary(spa, "Клиент") {
        Container(frontend, "React SPA", "React 18 + TS + Vite + Tailwind", "Тёмная тема, JWT в localStorage, i18n RU/EN, экраны: документы, рецензии, KB, экономика, диаграммы")
    }

    Container_Boundary(server, "Сервер (Docker Compose)") {
        Container(backend, "FastAPI", "Python 3.11 + SQLAlchemy async + Pydantic v2", "15 роутеров, JWT+RBAC, AI-операции, детерминированная экономика, with_audit()")
        ContainerDb(db, "База данных", "SQLite (aiosqlite) / PostgreSQL (asyncpg)", "24 модели: users, documents, snippets, reviews, audit_runs, build_projects, economic_* и др.")
        Container(faiss, "FAISS-индексы", "faiss-cpu + sentence-transformers", "In-memory IndexFlatIP: KB-snippets + memory_items, перестраивается на старте")
        Container(kroki_c, "Kroki", "yuzutech/kroki:0.25", "Локальный рендер PlantUML/Mermaid/GraphViz → SVG/PNG")
    }

    System_Ext(ollama_c, "Ollama", "Локальный LLM (профиль local-llm)")
    System_Ext(llm, "Облачные LLM", "Anthropic / OpenAI / ProxyAPI / OpenRouter")

    Rel(user, frontend, "Использует браузер", "HTTPS :3000")
    Rel(frontend, backend, "REST API + JWT Bearer", "HTTP/JSON :8000")
    Rel(backend, db, "Async-запросы", "SQLAlchemy")
    Rel(backend, faiss, "Гибридный поиск (keyword + semantic)", "IndexFlatIP, cosine")
    Rel(backend, kroki_c, "Рендер диаграмм", "HTTP :8001")
    Rel(backend, ollama_c, "Локальный LLM (air-gapped)", "HTTP :11434")
    Rel(backend, llm, "AI-вызовы (блокируются при ENFORCE_LOCAL_ONLY)", "HTTPS/REST")
```

---

## Роли и авторизация

| Роль | Доступ |
|------|--------|
| **Аналитик** (`analyst`) | Документы, рецензии, batch-рецензии, KB, память, диаграммы, аудит, стандарты, risk-catalog, lessons, **build-проекты и оценка экономики** |
| **Архитектор** (`architect`) | Всё аналитика + **настройки AI-провайдеров** (включая Ollama) |
| **Администратор** (`admin`) | Всё + **управление пользователями** + **seed-данные** (bulk-загрузка) |

Аутентификация: OAuth2 password flow → JWT (HS256, срок 8 часов), пароли — bcrypt. Проверка роли через зависимости `require_analyst` / `require_architect` / `require_admin`.

Тестовые учётные записи (сменить перед продакшн!):

```
admin      / admin123
analyst    / analyst123
architect  / architect123
```

---

## Быстрый старт

```bash
git clone https://github.com/MatveiV/Analyst-Architect-AI.git
cd Analyst-Architect-AI
cp .env.example .env
nano .env   # вставьте API-ключ и APP_SECRET_KEY (openssl rand -hex 32)

docker-compose up --build
# Backend:  http://localhost:8000/docs
# Frontend: http://localhost:3000
```

### Быстрая загрузка демо-данных (после первого входа как admin)

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -d "username=admin&password=admin123" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -X POST http://localhost:8000/seed/examples -H "Authorization: Bearer $TOKEN"
```

---

## Флагманская фича: модуль экономики и окупаемости

Каждый ТЗ/BRD, загруженный в систему, можно превратить в **build-проект** и получить
для него полноценный бизнес-кейс без единой ручной формулы в Excel:

```bash
# 1. Создать build-проект на основе документа
curl -X POST http://localhost:8000/build-projects -H "Authorization: Bearer $TOKEN" \
  -d '{"document_id":"<id>","name":"CRM для отдела продаж"}'

# 2. AI-декомпозиция требований на задачи (story points → часы по ролям)
curl -X POST http://localhost:8000/build-projects/<id>/estimate-tasks \
  -H "Authorization: Bearer $TOKEN"

# 3. Расчёт CAPEX/OPEX/ROI/payback по прозрачной формуле
curl -X POST http://localhost:8000/build-projects/<id>/economic-estimate \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"time_saved_hours_monthly": 100, "avg_employee_rate": 2500}'

# 4. После внедрения — внести факт для план/факт анализа
curl -X POST http://localhost:8000/build-projects/<id>/actuals \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"actual_capex": 620000, "actual_benefit_monthly": 380000}'

# 5. Экспорт готового бизнес-кейса в DOCX
curl http://localhost:8000/build-projects/<id>/export/docx \
  -H "Authorization: Bearer $TOKEN" -o business_case.docx
```

### Формулы (прозрачные, без чёрного ящика)

```
CAPEX          = Σ(hours_by_role × hourly_rate_by_role)
OPEX/мес       = hosting + LLM-токены + support_hours × ставка
Выгода/мес     = time_saved_hours × средняя ставка сотрудника
Payback (мес)  = CAPEX / (Выгода/мес − OPEX/мес)
ROI 12мес, %   = ((Выгода/мес − OPEX/мес) × 12 − CAPEX) / CAPEX × 100
```

AI участвует только в оценке часов (`task_estimator.py`); все финансовые расчёты
выполняются детерминированно в Python (`economics_service.py`) — воспроизводимо и
проверяемо, без "галлюцинаций" в цифрах.

---

## Reasoning-режимы (Chain-of-Thought / ReAct)

Для AI-рецензии доступны три режима — управляются полем `reasoning_mode`
(`direct` | `cot` | `react`):

```bash
curl -X POST http://localhost:8000/ai/review -H "Authorization: Bearer $TOKEN" \
  -d '{"text": "...", "reasoning_mode": "cot"}'
```

- **direct** — прямой вызов (по умолчанию, самый быстрый/дешёвый)
- **cot** — модель рассуждает по шагам в блоке `<thinking>` перед выдачей JSON
- **react** — цикл Thought/Action/Observation в блоке `<reasoning>` перед JSON

---

## Конфигурация (.env)

| Переменная | Описание | По умолчанию |
|-----------|----------|-------------|
| `LLM_PROVIDER` | `anthropic` \| `openai` \| `proxyapi` \| `openrouter` \| `ollama` | `anthropic` |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | Ключи облачных провайдеров | — |
| `PROXYAPI_KEY` / `PROXYAPI_BASE_URL` / `PROXYAPI_MODEL` | RU-прокси (OpenAI-совместимый) | — |
| `OPENROUTER_API_KEY` / `OPENROUTER_BASE_URL` / `OPENROUTER_ROUTE` | Шлюз к 200+ моделям | — |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | Локальный LLM (air-gapped) | `http://ollama:11434/v1` / `qwen2.5:14b-instruct` |
| `ENFORCE_LOCAL_ONLY` | `true` = запрет любых внешних сетевых вызовов | `false` |
| `DIAGRAM_RENDERER_URL` / `DIAGRAM_RENDERER_TIMEOUT` | Kroki для локального рендера диаграмм | `http://kroki:8000` / `30` |
| `APP_SECRET_KEY` | Секрет для подписи JWT (мин. 32 символа) | — (обязательно сменить) |
| `DATABASE_URL` | SQLite или PostgreSQL | `sqlite+aiosqlite:///./data/analyst_architect_ai.db` |
| `MAX_DOCUMENT_LENGTH` | Макс. длина документа | `30000` |
| `RAG_TOP_K` | Число фрагментов для RAG | `5` |
| `LLM_TEMPERATURE` / `LLM_MAX_TOKENS` | Параметры LLM | `0.2` / `4096` |
| `LLM_COST_USD_TO_RUB` | Курс для пересчёта факт. расходов LLM | `90.0` |

> Рантайм-переключение провайдера возможно через БД (`/settings/providers`, роль architect+) — настройки в БД имеют приоритет над `.env`.

---

## API эндпоинты (полный список)

### Аутентификация
`POST /auth/login` · `GET /auth/me` · `POST /auth/register` (admin) · `GET /auth/users` (admin) ·
`PATCH /auth/users/{id}` (admin) · `POST /auth/users/{id}/reset-password` (admin)

### Документы и рецензии
`POST /documents` · `GET /documents` · `POST /documents/upload-markdown` ·
`POST /documents/{id}/review?reasoning_mode=cot` ·
`POST /documents/{id}/generate-{urs,srs,adr}` · `POST /documents/{id}/recommend-architecture` ·
`POST /documents/{id}/design-api` · `POST /documents/{id}/generate-diagrams` ·
`PATCH /documents/{id}/standards` ·
`GET /documents/{id}/requirements-documents` ·
`GET /documents/{id}/export/{docx,markdown}` · `GET /documents/{id}/export/full-package/docx` ·
`POST /ai/review` · `GET /reviews` · `GET /reviews/{id}` · `GET /reviews/diff?from_id=&to_id=` ·
`GET /reviews/{id}/export/{json,csv}` ·
`GET /requirements-documents/{id}` · `GET /documents/{id}/coverage`

### ★ Batch-рецензии (Phase 2)
`POST /batch-reviews` (до 50 ТЗ) · `GET /batch-reviews` · `GET /batch-reviews/{id}` · `GET /batch-reviews/{id}/export/csv`

### База знаний (RAG) + автоиндексация (Phase 3)
`POST /kb/documents` · `GET /kb/documents` · `POST /kb/ask` · `GET /kb/history` · `POST /kb/reindex` · `POST /ai/answer_with_sources`
> Сгенерированные URS/SRS/ADR/диаграммы автоматически индексируются в KB (миграция 0006, сервис `kb_autoindex.py`)

### Память (5 типов)
`POST /memory/store` · `POST /memory/search` · `GET /memory/recent?memory_type=` · `POST /memory/consolidate`

### Диаграммы + версионирование (Phase 1)
`GET /diagrams/{id}` · `GET /diagrams/document/{id}?notation=` ·
`POST /diagrams/generate-{c4,uml,erd}` · `PUT /diagrams/{id}` ·
`GET /diagrams/{id}/versions` · `POST /diagrams/{id}/rollback/{n}`

### Стандарты, риски, уроки
`GET /standards?family=requirements|diagram` · `PATCH /documents/{id}/standards` ·
`GET /risk-catalog` · `POST /risk-catalog` · `GET /risk-catalog/{id}` ·
`PUT /risk-catalog/{id}` · `DELETE /risk-catalog/{id}` ·
`GET /risk-catalog/stats` · `GET /risk-catalog/export/csv` ·
`GET /lessons` · `POST /lessons` · `GET /lessons/{id}` · `PUT /lessons/{id}` · `DELETE /lessons/{id}` ·
`GET /lessons/export/csv`

### Аудит
`GET /audit` · `GET /audit/stats`

### ★ Экономика (build-проекты)
`POST /build-projects` · `GET /build-projects` · `POST /build-projects/{id}/estimate-tasks` ·
`POST /build-projects/{id}/economic-estimate?use_actual_llm_cost=true` · `POST /build-projects/{id}/actuals` (architect+) ·
`GET /build-projects/{id}/report` · `GET /build-projects/{id}/export/{docx,pdf}`

### ★ Dashboard
`GET /dashboard/stats` · `GET /dashboard/recent-activity` · `GET /dashboard/stats-by-provider` · `GET /dashboard/actual-usage`

### ★ Seed (демо-данные, admin only)
`POST /seed/documents` · `POST /seed/kb-documents` · `POST /seed/examples`
> `/seed/examples` идемпотентно загружает 10 ТЗ/BRD/US + 5 KB-статей + риски/уроки/память (если ещё не загружено). В UI запускается кнопкой «Загрузить примеры для всех процессов» в Settings.

### Настройки AI-провайдеров (architect/admin)
`GET /settings/providers` · `POST /settings/providers` · `POST /settings/providers/activate?provider=` ·
`POST /settings/test?provider=` · `GET /settings/active` ·
`GET /settings/providers/ollama/models`

---

## Тестирование

```bash
cd backend
python -m pytest tests/ -v --asyncio-mode=auto
```

| Категория | Тестов |
|-----------|--------|
| Авторизация и RBAC | auth |
| AI Reviewer + RAG + Reasoning modes (CoT/ReAct) | main |
| **Phase 1 / Epic A** — diagram engine, Kroki, версионирование, rollback | epic_a_diagrams |
| **Phase 1 / Epic B** — стандарты документации (ГОСТ 34 / ISO 29148 / IEEE 830) | epic_b_standards |
| **Phase 1 / Epic C** — Ollama, ENFORCE_LOCAL_ONLY | epic_c_ollama |
| **Phase 2** — batch-review (до 50 ТЗ), coverage-счётчики, review diff | phase2_* |
| **Phase 3** — KB-autoindexing, usage↔economics (actual LLM cost) | phase3_* |
| Экономический модуль (CAPEX/OPEX/ROI формулы + API) | economics |
| **Итого** | **146** ✅ |

> 146/146 тестов проходят; TypeScript: 0 ошибок (`tsc --noEmit`); production-build фронтенда — чистый. Frontend E2E-тестов нет (в roadmap).

---

## Документация

| Документ | Описание |
|---------|----------|
| [docs/MERGE_PLAN.md](docs/MERGE_PLAN.md) | Сравнение проектов, план объединения, роадмап |
| [docs/user-guide-ru.md](docs/user-guide-ru.md) / [-en.md](docs/user-guide-en.md) | Руководство пользователя с C4/UML |
| [docs/admin-guide-ru.md](docs/admin-guide-ru.md) / [-en.md](docs/admin-guide-en.md) | Руководство администратора |
| [docs/graduation-report.md](docs/graduation-report.md) | Отчёт с мини-экономикой (курсовой формат) |
| [docs/defense-script.md](docs/defense-script.md) | Сценарий защиты проекта |

---

## Roadmap

- **v1.0** — текущий релиз: FastAPI + 16 роутеров, 24 модели, 21 сервис, 146 pytest, React 18 + Vite, модуль экономики
- **v1.1** — Alembic-миграции (6 шт., 0001–0006) ✅, batch-рецензия (Phase 2) ✅, webhook при `needs_review` — в работе
- **v1.2** — Vite + Tailwind ✅, OpenRouter provider ✅, ENFORCE_LOCAL_ONLY ✅, Kroki-рендер ✅; shadcn/ui / TanStack Query — в работе
- **v1.3** — Интеграция Economic Actuals с тайм-трекерами (Toggl/Harvest) для автосбора факта
- **v2.0** — Fine-tuned модель на корпоративных ТЗ, портфельный dashboard ROI по всем build-проектам компании

---

## Лицензия

Apache-2.0 (см. `LICENSE`)
