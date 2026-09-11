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
| **Новое в этом репозитории** | **Модуль экономики**: build-проекты, AI-декомпозиция задач, расчёт CAPEX/OPEX/ROI/payback, план/факт, экспорт бизнес-кейса в DOCX |

---

## Архитектура системы

```
analyst-architect-ai/
├── backend/                    # FastAPI + SQLAlchemy (async)
│   ├── app/
│   │   ├── main.py             # FastAPI app + RBAC на роутерах
│   │   ├── models/             # 17 SQLAlchemy моделей (включая экономику)
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── llm_client.py        # Anthropic / OpenAI / ProxyAPI
│   │   │   ├── ai_reviewer.py        # + Reasoning modes (direct/cot/react)
│   │   │   ├── rag_engine.py         # Гибридный RAG
│   │   │   ├── auth_service.py       # JWT + bcrypt
│   │   │   ├── task_estimator.py     # ★ AI-декомпозиция задач
│   │   │   ├── economics_service.py  # ★ CAPEX/OPEX/ROI/payback (детерминированно)
│   │   │   └── ...
│   │   └── api/routers/
│   │       ├── auth.py, documents.py, reviews.py, knowledge_base.py,
│   │       │   memory.py, diagrams.py, audit.py, settings.py
│   │       ├── build_projects.py     # ★ Экономический модуль
│   │       ├── dashboard.py          # ★ Сводная панель
│   │       └── seed.py               # ★ Демо-данные одной кнопкой
│   └── tests/                  # 63 pytest теста
├── frontend/                   # React 18 + TypeScript + Tailwind
│   └── src/pages/               # Documents, Reviews, KB, ArchStudio, Memory,
│                                 # Audit, Settings, Users, Economics ★
├── tests_data/                 # 10 тестовых ТЗ + 5 KB-документов + вопросы
├── docs/
│   ├── MERGE_PLAN.md            # ★ План объединения и роадмап
│   ├── user-guide-{ru,en}.md
│   ├── admin-guide-{ru,en}.md
│   ├── graduation-report.md
│   └── defense-script.md
├── docker-compose.yml
└── .env.example
```

---

## Роли и авторизация

| Роль | Доступ |
|------|--------|
| **Аналитик** (`analyst`) | Документы, рецензии, KB, память, аудит, **build-проекты и оценка экономики** |
| **Архитектор** (`architect`) | Всё аналитика + настройки AI-провайдеров |
| **Администратор** (`admin`) | Всё + управление пользователями + seed-данные |

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

curl -X POST http://localhost:8000/seed/all -H "Authorization: Bearer $TOKEN"
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
| `LLM_PROVIDER` | `anthropic` \| `openai` \| `proxyapi` | `anthropic` |
| `APP_SECRET_KEY` | Секрет для подписи JWT (мин. 32 символа) | — (обязательно сменить) |
| `DATABASE_URL` | SQLite или PostgreSQL | `sqlite:///./data/analyst_architect_ai.db` |
| `MAX_DOCUMENT_LENGTH` | Макс. длина документа | `30000` |
| `RAG_TOP_K` | Число фрагментов для RAG | `5` |

---

## API эндпоинты (полный список)

### Аутентификация
`POST /auth/login` · `GET /auth/me` · `POST /auth/register` (admin) · `GET /auth/users` (admin) ·
`PATCH /auth/users/{id}` (admin) · `POST /auth/users/{id}/reset-password` (admin)

### Документы и рецензии
`POST /documents` · `GET /documents` · `POST /documents/{id}/review?reasoning_mode=cot` ·
`POST /documents/{id}/generate-{urs,srs,adr}` · `POST /documents/{id}/recommend-architecture` ·
`POST /documents/{id}/design-api` · `POST /documents/{id}/generate-diagrams` ·
`GET /documents/{id}/export/docx` · `POST /ai/review`

### База знаний (RAG)
`POST /kb/documents` · `GET /kb/documents` · `POST /kb/ask` · `GET /kb/history` · `POST /kb/reindex`

### ★ Экономика (build-проекты)
`POST /build-projects` · `GET /build-projects` · `POST /build-projects/{id}/estimate-tasks` ·
`POST /build-projects/{id}/economic-estimate` · `POST /build-projects/{id}/actuals` ·
`GET /build-projects/{id}/report` · `GET /build-projects/{id}/export/docx`

### ★ Dashboard
`GET /dashboard/stats` · `GET /dashboard/recent-activity`

### ★ Seed (демо-данные, admin only)
`POST /seed/documents` · `POST /seed/kb-documents` · `POST /seed/all`

### Память, диаграммы, аудит, настройки
`POST /memory/store` · `POST /memory/search` · `GET /memory/recent` ·
`GET /diagrams/document/{id}` · `POST /diagrams/generate-{c4,uml,erd}` ·
`GET /audit` · `GET /audit/stats` ·
`GET/POST /settings/providers` (architect/admin) · `POST /settings/providers/activate` · `POST /settings/test`

---

## Тестирование

```bash
cd backend
python -m pytest tests/ -v --asyncio-mode=auto
```

| Категория | Тестов |
|-----------|--------|
| AI Reviewer + RAG (unit) | 10 |
| API бизнес-логика (documents/kb/memory/audit) | 12 |
| Авторизация и RBAC | 15 |
| Reasoning modes (CoT/ReAct) | 8 |
| Экономический модуль (формулы + API) | 16 |
| Dashboard / Seed | 2 |
| **Итого** | **63** ✅ |

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

- **v1.1** — Alembic-миграции, batch-рецензия, webhook при needs_review
- **v1.2** — Frontend на Vite + shadcn/ui + TanStack Query, OpenRouter provider
- **v1.3** — Интеграция Economic Actuals с тайм-трекерами (Toggl/Harvest)
- **v2.0** — Портфельный dashboard ROI по всем build-проектам компании

---

## Лицензия

Apache-2.0 (см. `LICENSE`)
