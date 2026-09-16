# Руководство администратора AnalystGuru

> Версия: 1.0.0 | Аудитория: системные администраторы, DevOps, тимлиды

---

## Содержание

1. [Архитектура развёртывания](#1-архитектура-развёртывания)
2. [Установка и запуск](#2-установка-и-запуск)
3. [Ролевая модель и авторизация](#3-ролевая-модель-и-авторизация)
4. [Управление пользователями](#4-управление-пользователями)
5. [Настройка AI-провайдеров](#5-настройка-ai-провайдеров)
6. [База данных](#6-база-данных)
7. [Мониторинг и аудит](#7-мониторинг-и-аудит)
8. [Безопасность](#8-безопасность)
9. [Диаграммы инфраструктуры](#9-диаграммы-инфраструктуры)

---

## 1. Архитектура развёртывания

```
Internet
    │
    ▼
Nginx (порт 3000) ──── React SPA (статика, экран логина)
    │
    ▼
FastAPI (порт 8000) ── JWT Auth + RBAC ── SQLite / PostgreSQL
    │
    ▼
LLM API (Anthropic / OpenAI / ProxyAPI)
```

### Минимальные требования сервера

| Компонент | Минимум | Рекомендуется |
|-----------|---------|---------------|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 2 GB | 4 GB |
| Диск | 10 GB | 20 GB SSD |
| ОС | Ubuntu 22.04 | Ubuntu 22.04 / Debian 12 |
| Docker | 24.x | 25.x |

---

## 2. Установка и запуск

```bash
git clone <repo-url>
cd analyst-guru
cp .env.example .env
nano .env   # Вставьте API ключ и APP_SECRET_KEY

docker-compose up --build -d

curl http://localhost:8000/health
# → {"status":"ok","service":"AnalystGuru API"}

open http://localhost:3000
```

### Переменные окружения (.env)

| Переменная | Описание | Обязательна |
|-----------|----------|-------------|
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `PROXYAPI_KEY` | Ключ LLM-провайдера | Один из трёх |
| `LLM_PROVIDER` | Активный провайдер | ✅ |
| `APP_SECRET_KEY` | Секретный ключ для подписи JWT (мин. 32 символа) | ✅ |
| `DATABASE_URL` | URL базы данных | ✅ |
| `MAX_DOCUMENT_LENGTH` | Макс. длина документа | ❌ (30000) |
| `RAG_TOP_K` | Число фрагментов для RAG | ❌ (5) |

### Первый запуск: автоматическое создание учётных записей

При первом старте (`lifespan` в `main.py`) система автоматически создаёт 3 учётные записи по умолчанию:

```python
admin      / admin123     → роль admin
analyst    / analyst123   → роль analyst
architect  / architect123 → роль architect
```

> ⚠️ **ОБЯЗАТЕЛЬНО смените пароли перед продакшн-деплоем** (см. раздел 4).

---

## 3. Ролевая модель и авторизация

### Механизм авторизации

- Аутентификация: **логин + пароль**, эндпоинт `POST /auth/login` (OAuth2PasswordRequestForm)
- Пароли хранятся хешированными через **bcrypt** (никогда в открытом виде)
- После успешного входа выдаётся **JWT access token** (алгоритм HS256, срок жизни 8 часов)
- Токен передаётся в заголовке `Authorization: Bearer <token>` на каждый защищённый запрос
- Frontend хранит токен в `localStorage`, прикрепляет автоматически через axios-интерцептор
- При истечении/невалидности токена backend возвращает `401` → frontend сбрасывает сессию и возвращает на экран входа

### Три роли и их права

| Роль | Права |
|------|-------|
| `admin` | Все бизнес-функции + `/auth/register`, `/auth/users` |
| `architect` | Все бизнес-функции (включая настройки AI-провайдеров `/settings/*`) |
| `analyst` | Документы, рецензии, база знаний, память, аудит + настройки LLM-провайдеров `/settings/*` (свой ключ и тест соединения) |

### Как проверяется роль на backend

Ограничения задаются **на уровне роутеров** в `app/main.py`, а не в каждом отдельном эндпоинте — это гарантирует, что забыть защитить новый эндпоинт невозможно:

```python
app.include_router(documents.router,       dependencies=[Depends(require_analyst)])
app.include_router(reviews.router,         dependencies=[Depends(require_analyst)])
app.include_router(knowledge_base.router,  dependencies=[Depends(require_analyst)])
app.include_router(memory.router,          dependencies=[Depends(require_analyst)])
app.include_router(diagrams.router,        dependencies=[Depends(require_analyst)])
app.include_router(audit.router,           dependencies=[Depends(require_analyst)])
app.include_router(settings_router.router, dependencies=[Depends(require_analyst)])
```

`require_analyst` пропускает любую из трёх ролей (admin/analyst/architect) — то есть **каждый** пользователь может настроить себе LLM-провайдера, сохранить API-ключ и протестировать соединение. `require_admin` — только admin (управление пользователями, seed-данные).

Отдельные эндпоинты `/auth/register`, `/auth/users`, `/auth/users/{id}` защищены персонально через `Depends(require_admin)`.

### Проверка защиты

```bash
# Без токена — 401
curl -i http://localhost:8000/documents

# С токеном analyst — 200
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -d "username=analyst&password=analyst123" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/documents

# Настройки доступны любой роли (с токеном аналитика — 200)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/settings/providers
```

---

## 4. Управление пользователями

### Через веб-интерфейс

Войдите как `admin` → **👥 Пользователи** → **+ Добавить пользователя**.

### Через REST API

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -d "username=admin&password=admin123" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Создать пользователя
curl -X POST http://localhost:8000/auth/register \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"username":"analyst2","email":"analyst2@company.ru","password":"Str0ng!Pass","full_name":"Мария Иванова","role":"analyst"}'

# Список пользователей
curl http://localhost:8000/auth/users -H "Authorization: Bearer $TOKEN"

# Изменить роль
curl -X PATCH http://localhost:8000/auth/users/{USER_ID} \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"role":"architect"}'

# Заблокировать
curl -X PATCH http://localhost:8000/auth/users/{USER_ID} \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"is_active":false}'

# Сбросить пароль
curl -X POST http://localhost:8000/auth/users/{USER_ID}/reset-password \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"new_password":"NewStr0ng!Pass"}'
```

### Смена паролей по умолчанию (обязательно!)

```bash
for u in admin analyst architect; do
  ID=$(curl -s http://localhost:8000/auth/users -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys,json
users=json.load(sys.stdin)
print([x['id'] for x in users if x['username']=='$u'][0])")
  curl -X POST http://localhost:8000/auth/users/$ID/reset-password \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"new_password\":\"$(openssl rand -base64 16)\"}"
done
```

---

## 5. Настройка AI-провайдеров

Доступно **любому аутентифицированному пользователю** (admin / analyst / architect). Провайдера можно выбрать вручную или **определить автоматически** по API-ключу (`POST /settings/detect`), а ключ проверить тестом соединения **до сохранения** (`POST /settings/test` с телом формы).

```bash
# Сохранить настройки Anthropic
curl -X POST http://localhost:8000/settings/providers \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"provider":"anthropic","api_key":"sk-ant-...","model":"claude-sonnet-4-20250514","temperature":0.2,"max_tokens":4096}'

# Активировать
curl -X POST "http://localhost:8000/settings/providers/activate?provider=anthropic" \
  -H "Authorization: Bearer $TOKEN"

# Тест подключения
curl -X POST "http://localhost:8000/settings/test?provider=anthropic" \
  -H "Authorization: Bearer $TOKEN"
```

### ProxyAPI (российский OpenAI-совместимый прокси)

```bash
curl -X POST http://localhost:8000/settings/providers \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"provider":"proxyapi","api_key":"sk-...","model":"claude-sonnet-4-20250514","base_url":"https://api.proxyapi.ru/anthropic","temperature":0.2,"max_tokens":4096}'
```

---

## 6. Модуль экономики и экспорт

### Экономические расчёты

Система рассчитывает CAPEX, OPEX, ROI и срок окупаемости по прозрачным формулам:

```
CAPEX = Σ(часы_по_ролям × ставка_роли)
OPEX/мес = хостинг + LLM_API + часы_поддержки × ставка
Выгода/мес = часы_экономии_сотрудников × средняя_ставка
Окупаемость = CAPEX / (Выгода − OPEX)
ROI_12мес = ((Выгода − OPEX) × 12 − CAPEX) / CAPEX × 100
```

### Экспорт бизнес-кейса

| Формат | Эндпоинт | Описание |
|--------|----------|----------|
| DOCX | `GET /build-projects/{id}/export/docx` | Microsoft Word |
| PDF | `GET /build-projects/{id}/export/pdf` | Adobe PDF с кириллицей |

### Загрузка демо-данных

Кнопка **"Загрузить примеры для всех процессов"** на странице Settings → Quick start:
- Загружает 10 примеров ТЗ/BRD/SRS/User Story
- Создаёт 5 KB-статей
- Добавляет примеры в Risk Catalog, Project Lessons, Memory Items

### Миграции БД

Система поддерживает два режима:
1. **Alembic** — автоматический при запуске (основной путь). Если зависает (Windows/SQLite), пробует:
2. **create_all()** — `Base.metadata.create_all` (fallback для локальной разработки)

Для ручного запуска миграций:
```bash
cd backend
alembic upgrade head
```

---

## 7. База данных

### Схема (ключевые таблицы)

```sql
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(200) UNIQUE NOT NULL,
    full_name VARCHAR(200),
    hashed_password VARCHAR(256) NOT NULL,  -- bcrypt hash
    role VARCHAR(20) DEFAULT 'analyst',     -- admin|analyst|architect
    is_active BOOLEAN DEFAULT TRUE,
    last_login DATETIME
);

CREATE TABLE spec_documents (...);  -- Вариант 2: рецензируемые ТЗ/BRD/US/SRS/Markdown
CREATE TABLE kb_documents (...);    -- Вариант 5: статьи базы знаний
CREATE TABLE kb_snippets (...);     -- фрагменты KB для RAG (document_id -> kb_documents)
CREATE TABLE reviews (...);         -- review_json, needs_review, confidence, error (причина)
CREATE TABLE qa_runs (...);         -- question, answer, sources_json, needs_review, error
CREATE TABLE audit_runs (...);   -- action, input, output, status, error, duration_ms
CREATE TABLE memory_items (...);
CREATE TABLE provider_settings (...);
```

### Резервное копирование

```bash
cp data/analyst_architect_ai.db backups/analyst_architect_ai_$(date +%Y%m%d_%H%M%S).db

# Просмотр пользователей
sqlite3 data/analyst_architect_ai.db "SELECT username, role, is_active, last_login FROM users;"

# Просмотр аудита
sqlite3 data/analyst_architect_ai.db "SELECT created_at, action, status, error FROM audit_runs ORDER BY created_at DESC LIMIT 10;"
```

### Переключение на PostgreSQL

```env
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/analyst_architect_ai
```

---

## 7. Мониторинг и аудит

```bash
curl http://localhost:8000/audit/stats -H "Authorization: Bearer $TOKEN"
# → {"total":150,"ok":142,"errors":3,"needs_review":5,"avg_duration_ms":2341.5}
```

| Метрика | Норма | Внимание | Проблема |
|---------|-------|----------|---------|
| `error_rate_pct` | < 5% | 5–15% | > 15% |
| `needs_review_pct` | < 20% | 20–40% | > 40% |

---

## 8. Безопасность

### Чеклист для продакшн

- [ ] Сменить все пароли по умолчанию
- [ ] Сгенерировать `APP_SECRET_KEY`: `openssl rand -hex 32`
- [ ] Настроить HTTPS (nginx + Let's Encrypt)
- [ ] Ограничить `CORS allow_origins` конкретными доменами
- [ ] Firewall: открыть только 80/443
- [ ] PostgreSQL вместо SQLite для продакшн-нагрузки
- [ ] Регулярное резервное копирование БД
- [ ] API ключи — в secrets manager, не в `.env` на сервере
- [ ] Ротация `APP_SECRET_KEY` каждые 90 дней (инвалидирует все текущие токены)
- [ ] Мониторинг `error_rate` с алертами

### Особенности JWT-реализации

- Алгоритм: HS256 (симметричный, единый секрет на весь backend)
- Срок жизни токена: 8 часов (`ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8`)
- Механизма refresh-токенов нет в v1.0 — после истечения требуется повторный вход
- Токен содержит `sub` (user_id) и `role` — роль встроена в токен для быстрой проверки без похода в БД, но актуальный `is_active` статус всё равно проверяется в БД при каждом запросе через `get_current_user`

---

## 9. Диаграммы инфраструктуры

### Deployment Diagram

```mermaid
graph TB
    subgraph Client["🖥️ Клиент"]
        Browser["Браузер\nhttps://host:3000"]
    end

    subgraph Server["🖥️ Сервер / VPS (Docker Compose)"]
        Nginx["nginx:alpine\nПорт 3000\nSPA + /api прокси"]
        FastAPI["python:3.11-slim\nПорт 8000\n15 роутеров · JWT+RBAC\nFAISS-индексы in-memory"]
        Kroki["yuzutech/kroki:0.25\nПорт 8001\nЛокальный рендер\nPlantUML/Mermaid/GraphViz"]
        Ollama["ollama/ollama\nПорт 11434\nПрофиль local-llm\n(опционально)"]
        DB[("SQLite / PostgreSQL\n25 моделей · 7 Alembic-миграций\nvolume: ./data")]
        VolOllama[("ollama_models\nnamed volume")]
    end

    subgraph External["☁️ Внешние LLM-сервисы"]
        Claude["Anthropic Claude"]
        OpenAI["OpenAI"]
        ProxyAPI["ProxyAPI (RU)"]
        OpenRouter["OpenRouter"]
    end

    Browser -->|"HTTPS :443"| Nginx
    Nginx -->|"HTTP API :8000"| FastAPI
    FastAPI -->|"SQLAlchemy async"| DB
    FastAPI -->|"HTTP :8001\nрендер диаграмм"| Kroki
    FastAPI -.->|"HTTP :11434\n(профиль local-llm)"| Ollama
    Ollama --- VolOllama

    FastAPI -->|"HTTPS REST"| Claude
    FastAPI -->|"HTTPS REST"| OpenAI
    FastAPI -->|"HTTPS REST"| ProxyAPI
    FastAPI -->|"HTTPS REST"| OpenRouter

    note["⬛ ENFORCE_LOCAL_ONLY=true → все исходящие HTTPS к внешним LLM блокируются;\nостаются только локальные Ollama + Kroki (air-gapped режим)"]
    FastAPI -.->|"соблюдает флаг"| note
```

**Volumes:** `./data` (bind-mount, SQLite + `analyst_architect_ai.db`) и `ollama_models` (named-volume, модели Ollama).

**Профили docker-compose:**
- по умолчанию поднимаются `backend`, `frontend`, `kroki` (лёгкий, always-on);
- `ollama` — только с `--profile local-llm`;
- если Ollama уже на хосте, вместо профиля задайте `OLLAMA_BASE_URL=http://host.docker.internal:11434` (Win/Mac) или `http://172.17.0.1:11434` (Linux).

### Sequence: JWT авторизация + RBAC-проверка

```mermaid
sequenceDiagram
    actor U as Пользователь
    participant FE as Frontend
    participant API as FastAPI
    participant Dep as require_analyst + JWT
    participant DB as Database

    U->>FE: Вводит логин/пароль
    FE->>API: POST /auth/login
    API->>DB: SELECT user, bcrypt.verify
    API->>API: jwt.encode({sub: user_id, role})
    API-->>FE: access_token

    Note over FE,API: Все последующие запросы
    FE->>API: GET /settings/providers\nAuthorization: Bearer <token>
    API->>Dep: Проверка роли
    Dep->>API: jwt.decode(token) → user_id, role
    Dep->>DB: SELECT user WHERE id=? (проверка is_active)
    alt любая роль (analyst | architect | admin)
        Dep-->>API: OK, пропускаем
        API->>DB: SELECT * FROM provider_settings
        API-->>FE: 200 + конфиг 5 провайдеров
    else нет / невалидный токен
        Dep-->>API: 401 Unauthorized
        API-->>FE: 401
    end
```
