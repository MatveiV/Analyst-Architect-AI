# Руководство пользователя Analyst-Architect-AI

> **Analyst-Architect-AI** — AI-копилот системного аналитика и архитектора решений.
> Версия: 1.0.0 | Языки интерфейса: 🇷🇺 Русский / 🇬🇧 English | 15 экранов, 15 API-роутеров, 25 моделей

---

## Содержание

1. [Введение и роли](#1-введение-и-роли)
2. [Архитектура системы (C4)](#2-архитектура-системы-c4)
3. [Вход в систему](#3-вход-в-систему)
4. [Бизнес-сценарии по ролям](#4-бизнес-сценарии-по-ролям)
5. [Настройка AI-провайдеров](#5-настройка-ai-провайдеров)
6. [Работа с документами](#6-работа-с-документами)
7. [AI-рецензия документа](#7-ai-рецензия-документа)
8. [Архитектурная студия](#8-архитектурная-студия)
9. [База знаний (RAG)](#9-база-знаний-rag)
10. [Фреймворк памяти](#10-фреймворк-памяти)
11. [Аудит-центр](#11-аудит-центр)
12. [Экономика проектов — ROI и окупаемость](#12-экономика-проектов--roi-и-окупаемость)
13. [Экспорт бизнес-кейса](#13-экспорт-бизнес-кейса)
14. [Дополнительные модули: Batch, Risk Catalog, Lessons, Dashboard, Settings, Users, Standards](#14-дополнительные-модули-batch-risk-catalog-lessons-dashboard-settings-users-standards)
15. [UML-диаграммы рабочих процессов](#15-uml-диаграммы-рабочих-процессов)

---

## 1. Введение и роли

### Для кого этот продукт

Analyst-Architect-AI решает проблему **дорогостоящего ручного анализа** технических заданий и архитектурных решений. Без системы аналитик тратит 2–4 часа на рецензию одного ТЗ; с Analyst-Architect-AI — 5–10 минут. Система объединяет AI-рецензию, генерацию URS/SRS/ADR/API, диаграммы, базу знаний (RAG), фреймворк памяти и **модуль экономики** для расчёта CAPEX/OPEX/ROI по каждому build-проекту.

### Главная страница: обзор экранов

После входа в боковом меню доступны 15 экранов:

| # | Раздел | Назначение |
|---|--------|------------|
| 1 | 📊 **Dashboard** | Сводная статистика: документы, рецензии, AI-операции, провайдер, факт. расход LLM |
| 2 | 📄 **Документы** | Список ТЗ/BRD/SRS/User Story, загрузка .md, рецензия, экспорт |
| 3 | 🔍 **Рецензии** | Список AI-рецензий, сравнение двух рецензий (diff), экспорт JSON/CSV |
| 4 | 📦 **Batch-рецензии** | Пакетная рецензия до 50 ТЗ за один запрос |
| 5 | 🏛 **Арх. студия** | Рекомендации архитектуры, ADR, OpenAPI, C4/UML/ERD, версионирование |
| 6 | 📚 **База знаний** | Внутренние KB-статьи, семантический вопрос-ответ с цитатами |
| 7 | 🧠 **Память** | 5-типовой фреймворк: семантика / эпизоды / решения / риски / требования |
| 8 | 🛡 **Аудит** | Журнал всех AI-операций с метриками ok / needs_review / error |
| 9 | ⚠️ **Risk Catalog** | Каталог типовых рисков с категориями и экспортом CSV |
| 10 | 📘 **Уроки** | Уроки проектов (положительные и отрицательные) |
| 11 | 💰 **Экономика** | Build-проекты: AI-декомпозиция, CAPEX/OPEX/ROI, план/факт, DOCX/PDF |
| 12 | ⚙️ **Настройки** | AI-провайдеры (Anthropic / OpenAI / ProxyAPI / OpenRouter / Ollama) |
| 13 | 👥 **Пользователи** | Управление командой (только admin) |

### Роли пользователей

Доступ к системе строится на **обязательной авторизации по логину и паролю** (JWT-токен, срок жизни 8 часов). Каждому пользователю назначается одна из трёх ролей:

| Роль | Описание | Возможности |
|------|----------|-------------|
| **Аналитик** (`analyst`) | Специалист по требованиям | Документы, рецензии, batch-рецензии, KB, память, диаграммы, аудит, стандарты, risk-catalog, lessons, **build-проекты и экономика**, **настройки AI-провайдеров** |
| **Архитектор** (`architect`) | Архитектор ПО | Всё что аналитик + внесение факта в build-проекты |
| **Администратор** (`admin`) | Системный администратор | Всё + **управление пользователями** (создание, роли, блокировка, сброс паролей) + **seed-данные** |

### Матрица доступа

| Функция | Аналитик | Архитектор | Администратор |
|---------|:---:|:---:|:---:|
| Вход по логину/паролю | ✅ | ✅ | ✅ |
| Создание / рецензия документов | ✅ | ✅ | ✅ |
| Batch-рецензии (до 50 ТЗ) | ✅ | ✅ | ✅ |
| AI-рецензия (CoT / ReAct) | ✅ | ✅ | ✅ |
| Архитектурные рекомендации, ADR, OpenAPI | ✅ | ✅ | ✅ |
| C4 / UML / ERD + версионирование | ✅ | ✅ | ✅ |
| База знаний / RAG | ✅ | ✅ | ✅ |
| Память (5 типов) | ✅ | ✅ | ✅ |
| Стандарты (ГОСТ 34 / ISO 29148 / IEEE 830) | ✅ | ✅ | ✅ |
| Risk Catalog / Уроки проектов | ✅ | ✅ | ✅ |
| **Build-проекты и экономика (CAPEX/OPEX/ROI)** | ✅ | ✅ | ✅ |
| Внесение факта (actuals) в build-проект | ❌ (403) | ✅ | ✅ |
| Просмотр аудита | ✅ | ✅ | ✅ |
| **Настройки AI-провайдеров** | ✅ | ✅ | ✅ |
| **Управление пользователями** | ❌ (403) | ❌ (403) | ✅ |
| **Seed демо-данных (`/seed/...`)** | ❌ (403) | ❌ (403) | ✅ |

> Все ограничения проверяются **на backend** (JWT + роль) через `require_admin` / `require_architect` / `require_analyst` в `app/main.py`, а не только скрываются в интерфейсе — попытка вызвать защищённый эндпоинт без нужной роли вернёт HTTP 403.

---

## 2. Архитектура системы (C4)

### C4 Level 1 — Контекст системы

```mermaid
flowchart LR
    classDef person fill:#08427b,stroke:#052e56,color:#ffffff
    classDef sys fill:#1168bd,stroke:#0b4884,color:#ffffff
    classDef ext fill:#999999,stroke:#666666,color:#ffffff

    analyst(["Аналитик<br/>рецензирует ТЗ, генерирует URS/SRS/ADR, считает экономику"])
    architect(["Архитектор<br/>проектирует архитектуру, настраивает AI-провайдеры"])
    admin(["Администратор<br/>управляет пользователями и демо-данными"])

    ag["Analyst-Architect-AI<br/>AI-копилот для системного аналитика и архитектора"]

    claude["Anthropic Claude<br/>LLM по умолчанию (claude-sonnet-4)"]
    openai["OpenAI<br/>gpt-4o"]
    proxyapi["ProxyAPI<br/>OpenAI-совместимый RU-прокси"]
    openrouter["OpenRouter<br/>шлюз к 200+ моделям"]
    ollama["Ollama<br/>локальный LLM (air-gapped, qwen2.5)"]
    kroki["Kroki<br/>локальный рендер PlantUML/Mermaid → SVG/PNG"]

    analyst -->|"документы, рецензии, экономика"| ag
    architect -->|"архитектура, диаграммы, настройки LLM"| ag
    admin -->|"пользователи, seed-данные"| ag
    ag -->|"Вызывает LLM API · HTTPS/REST"| claude
    ag -->|"Вызывает LLM API (опционально) · HTTPS/REST"| openai
    ag -->|"RU-прокси (опционально) · HTTPS/REST"| proxyapi
    ag -->|"Шлюз (опционально) · HTTPS/REST"| openrouter
    ag -->|"Локальный LLM без выхода в интернет · HTTP :11434"| ollama
    ag -->|"Рендер диаграмм без выхода в интернет · HTTP :8001"| kroki

    class analyst,architect,admin person
    class ag sys
    class claude,openai,proxyapi,openrouter,ollama,kroki ext
```

> При `ENFORCE_LOCAL_ONLY=true` вызовы облачных LLM (Anthropic/OpenAI) из этой схемы заблокированы.

### C4 Level 2 — Контейнеры

```mermaid
flowchart LR
    classDef person fill:#08427b,stroke:#052e56,color:#ffffff
    classDef cont fill:#1168bd,stroke:#0b4884,color:#ffffff
    classDef storage fill:#999999,stroke:#666666,color:#ffffff
    classDef ext fill:#a0a0a0,stroke:#666666,color:#ffffff,stroke-width:1px

    user(["Пользователь<br/>analyst / architect / admin"])

    subgraph spa["Клиент"]
        frontend["React SPA<br/>React 18 + TS + Vite + Tailwind<br/>тёмная тема, JWT в localStorage, i18n RU/EN, экраны: документы, рецензии, batch, KB, экономика, диаграммы"]
    end

    subgraph server["Сервер (Docker Compose)"]
        backend["FastAPI<br/>Python 3.11 + SQLAlchemy async + Pydantic v2<br/>15 роутеров, JWT+RBAC, AI-операции, детерминированная экономика, with_audit()"]
        db[("База данных<br/>SQLite (aiosqlite) / PostgreSQL (asyncpg)<br/>25 моделей: users, spec_documents, kb_documents, kb_snippets, reviews, qa_runs, audit_runs, build_projects, economic_* и др.")]
        faiss["FAISS-индексы<br/>faiss-cpu + sentence-transformers<br/>in-memory IndexFlatIP: KB-snippets + memory_items"]
        kroki_c["Kroki<br/>yuzutech/kroki:0.25<br/>локальный рендер PlantUML/Mermaid/GraphViz → SVG/PNG"]
    end

    ollama_c["Ollama<br/>локальный LLM (профиль local-llm)"]
    llm["Облачные LLM<br/>Anthropic / OpenAI / ProxyAPI / OpenRouter"]

    user -->|"браузер · HTTPS :3000"| frontend
    frontend -->|"REST API + JWT Bearer · HTTP/JSON :8000"| backend
    backend -->|"async-запросы · SQLAlchemy"| db
    backend -->|"гибридный поиск · IndexFlatIP, cosine"| faiss
    backend -->|"рендер диаграмм · HTTP :8001"| kroki_c
    backend -->|"локальный LLM (air-gapped) · HTTP :11434"| ollama_c
    backend -->|"AI-вызовы (блок. при ENFORCE_LOCAL_ONLY) · HTTPS/REST"| llm

    class user person
    class frontend,backend,faiss,kroki_c cont
    class db storage
    class ollama_c,llm ext
```

### C4 Level 3 — Компоненты Backend

```mermaid
flowchart LR
    classDef router fill:#1168bd,stroke:#0b4884,color:#ffffff
    classDef svc fill:#438dd5,stroke:#1168bd,color:#ffffff
    classDef storage fill:#999999,stroke:#666666,color:#ffffff

    subgraph api["FastAPI Application"]
        direction TB
        auth_r["Auth Router · JWT + bcrypt<br/>логин, профиль, управление пользователями"]
        deps["Auth Dependencies · OAuth2PasswordBearer<br/>require_analyst / require_architect / require_admin"]
        docs_r["Documents Router · FastAPI<br/>CRUD документов, URS/SRS/ADR/API, рецензии, экспорт"]
        batch_r["Batch Reviews Router · FastAPI<br/>пакетная рецензия до 50 ТЗ"]
        kb_r["KB Router · FastAPI<br/>база знаний, RAG-поиск, автоиндексация"]
        mem_r["Memory Router · FastAPI<br/>5-типовой фреймворк памяти"]
        diag_r["Diagrams Router · FastAPI<br/>C4/UML/ERD, версионирование + rollback"]
        std_r["Standards Router · FastAPI<br/>ГОСТ 34 / ISO 29148 / IEEE 830"]
        risk_r["Risk Catalog Router · FastAPI<br/>CRUD рисков"]
        less_r["Lessons Router · FastAPI<br/>уроки проектов"]
        econ_r["Build Projects Router · FastAPI<br/>экономика: CAPEX/OPEX/ROI"]
        dash_r["Dashboard Router · FastAPI<br/>статистика, actual-usage"]
        audit_r["Audit Router · FastAPI<br/>просмотр аудит-журнала"]
        settings_r["Settings Router · FastAPI (любая роль)<br/>настройки 5 AI-провайдеров: ключ, детекция, тест, активация"]
        ai_rev["AI Reviewer · Python<br/>рецензия ТЗ, reasoning modes (direct/cot/react), safe_fallback"]
        rag["RAG Engine · sentence-transformers + FAISS<br/>гибридный поиск (keyword 40% + semantic 60%)"]
        diag_eng["Diagram Engine · Python<br/>генерация + Kroki-рендер, версионирование"]
        econ_svc["Economics Service · Python<br/>CAPEX/OPEX/ROI/payback — детерминированно"]
        task_est["Task Estimator · Python + LLM<br/>AI-декомпозиция требований в часы по ролям"]
        audit_svc["Audit Service · Python<br/>with_audit(): провенанс всех AI-операций"]
    end

    db[("База данных<br/>SQLite/PostgreSQL")]
    faiss["FAISS · in-memory<br/>IndexFlatIP для KB + memory"]

    docs_r -->|"JWT + роль"| deps
    batch_r -->|"JWT + роль"| deps
    settings_r -->|"любая роль (admin / analyst / architect)"| deps
    docs_r -->|"запуск рецензии"| ai_rev
    batch_r -->|"пакетная рецензия"| ai_rev
    kb_r -->|"RAG-поиск"| rag
    rag -->|"semantic-поиск"| faiss
    diag_r -->|"генерация + рендер"| diag_eng
    econ_r -->|"расчёт экономики"| econ_svc
    econ_r -->|"декомпозиция задач"| task_est
    ai_rev -->|"with_audit()"| audit_svc
    econ_svc -->|"факт LLM-расходов"| audit_svc
    audit_svc -->|"сохраняет audit_runs"| db

    class auth_r,deps,docs_r,batch_r,kb_r,mem_r,diag_r,std_r,risk_r,less_r,econ_r,dash_r,audit_r,settings_r router
    class ai_rev,rag,diag_eng,econ_svc,task_est,audit_svc svc
    class db,faiss storage
```

### C4 Level 4 — Code: AI Reviewer + Audit (ядро системы)

```mermaid
classDiagram
    direction LR
    class LLMClient {
        +provider: str
        +call(prompt) str
        +get_last_call_meta() dict
        -anthropic_call()
        -openai_call()
        -ollama_call()
    }

    class AIReviewer {
        +reasoning_mode: str
        +review(text, context) Review
        -pre_validate(text)
        -build_prompt(text, mode)
        -parse_strict_json(raw) dict
        -safe_fallback(text, reason) Review
    }

    class ReasoningModes {
        <<enumeration>> режимы
        DIRECT
        COT
        REACT
    }

    class AuditService {
        +with_audit(action, fn) Result
        -record(action, input, output, status)
        -capture_tokens(meta)
    }

    class Review {
        +summary: str
        +risks: list
        +missing_requirements: list
        +questions: list
        +confidence: float
        +needs_review: bool
        +reasoning: str
    }

    class AuditRun {
        +action: str
        +provider: str
        +is_local: bool
        +tokens_in: int
        +tokens_out: int
        +estimated_cost_usd: float
        +status: str
        +duration_ms: int
    }

    AIReviewer ..> ReasoningModes : использует режим
    AIReviewer --> LLMClient : вызывает
    AIReviewer ..> AuditService : оборачивается в with_audit()
    AIReviewer ..> Review : возвращает
    AuditService --> AuditRun : пишет запись
    LLMClient ..> AuditService : отдаёт meta через get_last_call_meta()
```

> **Почему этот уровень**: AI Reviewer — ядро продукта. Диаграмма показывает три reasoning-режима (direct/cot/react), обязательное оборачивание каждого LLM-вызова в `with_audit()` (провенанс + учёт токенов/стоимости), и `safe_fallback()` — гарантированная рецензия даже при сбое LLM. `is_local` в `AuditRun` доказывает (для compliance), покинули ли данные корпоративный периметр.

---

## 3. Вход в систему

### Шаги авторизации

1. Откройте браузер и перейдите по адресу `http://localhost:3000`
2. Система показывает экран **входа** (без авторизации приложение недоступно)
3. Введите **логин** и **пароль**
4. Нажмите кнопку **→ Войти**

После успешного входа backend выдаёт **JWT-токен** (действует 8 часов), который сохраняется в браузере и автоматически прикладывается ко всем запросам. Вы попадёте на главную страницу — список документов.

### Тестовые учётные записи

| Логин | Пароль | Роль |
|-------|--------|------|
| `admin` | `admin123` | Администратор |
| `analyst` | `analyst123` | Аналитик |
| `architect` | `architect123` | Архитектор |

На экране входа есть кнопки быстрого заполнения для каждой из трёх ролей — удобно для демонстрации.

> ⚠️ Смените пароли по умолчанию перед переводом в продакшн!

### Что происходит при неверном пароле

Backend возвращает `401 Unauthorized`, интерфейс показывает сообщение "Неверный логин или пароль" без уточнения, что именно неверно (логин или пароль) — это стандартная практика безопасности.

### Выход из системы

Кнопка **⎋** рядом с именем пользователя в боковом меню — удаляет токен из браузера и возвращает на экран входа.

### Переключение языка

Кнопка 🇬🇧 EN / 🇷🇺 RU находится:
- **На странице входа** — правый верхний угол
- **В боковом меню** — нижняя часть sidebar

Выбор языка сохраняется в браузере независимо от сессии авторизации.

---

## 4. Бизнес-сценарии по ролям

### Сценарий А: Аналитик рецензирует техническое задание

**Участник:** Аналитик (роль `analyst`)  
**Цель:** Получить структурированную рецензию ТЗ за 5 минут вместо 2 часов

```
Шаг 0: Вход в систему — analyst / analyst123
Шаг 1: Аналитик → [Документы] → [+ Новый документ]
Шаг 2: Заполняет поля: название, тип = ТЗ, проект, текст
Шаг 3: Нажимает [🔍 Рецензия] в списке документов
Шаг 4: AI анализирует документ (15–45 сек)
Шаг 5: Аналитик изучает:
        - Резюме документа
        - Риски (высокий / средний / низкий)
        - Вопросы заказчику
        - Критерии приёмки
Шаг 6: Если needs_review=true — ⚠️ требует ручной проверки
Шаг 7: Экспорт рецензии в JSON / CSV / DOCX
```

### Сценарий Б: Архитектор создаёт архитектурное решение

**Участник:** Архитектор (роль `architect`)  
**Цель:** Выбрать архитектурный паттерн, задокументировать в ADR, настроить AI-провайдера

```
Шаг 0: Вход в систему — architect / architect123
Шаг 1: Архитектор → [Арх. студия]
Шаг 2: Выбирает документ (ТЗ) из списка
Шаг 3: Нажимает [🏛 Рекомендовать архитектуру]
        → Получает: паттерн + обоснование + альтернативы + риски
Шаг 4: Нажимает [📋 Создать ADR]
        → Получает: ADR с контекстом, решением, последствиями
Шаг 5: Нажимает [🔌 Создать API Spec] → OpenAPI 3.1 (JSON + YAML)
Шаг 6: Нажимает [🗺 Сгенерировать диаграммы] → C4, UML, ERD, Mermaid

Настройка AI-провайдера (доступно любой роли):
Шаг 7: Открыть [⚙️ Настройки]
Шаг 8: При желании — 🔍 «Определить провайдера» по введённому ключу, затем ввести ключ и модель
Шаг 9: ⚡ «Тест связи» (проверка до сохранения), сохранить, нажать «Сделать активным»
Шаг 10: Для OpenRouter можно выбрать Route (режим маршрутизации):
      • `openrouter/free` — только бесплатные модели (по умолчанию)
      • `openrouter/fusion` — ансамбль из 2+ моделей, возвращает лучший результат
      • `openrouter/pareto-code` — оптимизация для задач программирования
Шаг 10: Настраивает модель, температуру, макс. токенов (для всех провайдеров)
Шаг 11: Активирует провайдер для всей команды
```

### Сценарий В: Аналитик работает с базой знаний команды

**Участник:** Аналитик  
**Цель:** Быстро найти ответ во внутренних документах

```
Шаг 1: Аналитик → [База знаний] → [📚 Документы]
Шаг 2: Добавляет внутренние документы (правила, стандарты, FAQ)
Шаг 3: Переходит на вкладку [💬 Задать вопрос]
Шаг 4: Вводит вопрос на естественном языке
Шаг 5: Система ищет в базе знаний и формирует ответ с цитатами
Шаг 6: Если needs_review=true — база знаний не содержит ответа
```

### Сценарий Г: Администратор управляет командой

**Участник:** Администратор (роль `admin`)  
**Цель:** Добавить нового сотрудника, назначить роль, при необходимости заблокировать

```
Шаг 0: Вход в систему — admin / admin123
Шаг 1: Администратор → [👥 Пользователи] → [+ Добавить]
Шаг 2: Заполняет: логин, email, пароль, имя, роль (analyst/architect/admin)
Шаг 3: Новый пользователь может войти с указанными данными
Шаг 4: При необходимости: изменить роль (dropdown в таблице),
        сбросить пароль (🔑), заблокировать/разблокировать (🚫/✓)
```

---

## 5. Настройка AI-провайдеров

### Поддерживаемые провайдеры

| Провайдер | Тип API | Base URL по умолчанию | Особенности |
|-----------|---------|----------------------|-------------|
| **Anthropic Claude** | Native | — | Claude 3.5 Sonnet, Claude 3 Opus |
| **OpenAI GPT** | OpenAI-compat | `https://api.openai.com/v1` | GPT-4o, GPT-4o-mini |
| **ProxyAPI** | OpenAI-compat | `https://api.proxyapi.ru/anthropic` | Доступ к Claude через РФ-прокси |
| **OpenRouter** | OpenAI-compat | `https://openrouter.ai/api/v1` | Шлюз к 200+ моделям |

### OpenRouter Route

OpenRouter поддерживает три режима маршрутизации (выбираются в интерфейсе Настроек):

| Route | Описание |
|-------|----------|
| `openrouter/free` | Только бесплатные модели (лимит: 20 req/min) |
| `openrouter/fusion` | Запрос отправляется на 2+ модели, возвращается лучший ответ |
| `openrouter/pareto-code` | Оптимизирован для генерации и анализа кода |

Route передаётся HTTP-заголовком `X-Route` в каждом запросе к OpenRouter API.

### Параметры модели (для всех провайдеров)

- **Модель** — строковое наименование (выпадающий список + ручной ввод)
- **Температура** — слайдер 0.0–2.0 (0 — детерминированно, 2 — максимально творчески)
- **Макс. токенов** — выбор из предустановленных значений (256–32768)

---

## 6. Работа с документами

### Загрузка Markdown с диаграммами

На странице **Документы** есть кнопка **📄 Загрузить .md**. При загрузке файла `.md` система:

1. Сохраняет документ как `doc_type = markdown`
2. Автоматически извлекает блоки ` ```mermaid ` и ` ```plantuml ` / `@startuml...@enduml` и сохраняет их как отдельные артефакты диаграмм
3. На странице просмотра документа markdown-контент отображается с рендерингом диаграмм:
   - **Mermaid** — рендеринг через браузерную библиотеку mermaid.js
   - **PlantUML** — отображение через сервис plantuml.com (SVG-изображение)

### Создание итогового документа

На странице детального просмотра документа доступна кнопка **📄 Итоговый MD**, которая генерирует консолидированный markdown-файл, включающий:

- Исходный текст документа
- Последнюю AI-рецензию (summary, риски)
- ADR (если есть)
- Сгенерированные диаграммы (mermaid / plantuml)

---

### Поддерживаемые типы документов

| Тип | Код | Описание |
|-----|-----|----------|
| Техническое задание | `tz` | Классическое ТЗ на разработку |
| BRD | `brd` | Business Requirements Document |
| User Story | `user_story` | Пользовательские истории |
| SRS | `srs` | Software Requirements Specification |
| KB Article | `kb_article` | Статья базы знаний — создаётся отдельно в разделе «База знаний» (`POST /kb/documents`, таблица `kb_documents`); в `/documents` не принимается |

### Создание документа

1. Перейдите в **Документы**
2. Нажмите **+ Новый документ**
3. Заполните поля: **Название**, **Тип**, **Проект** (опционально), **Текст** (до 30 000 символов)
4. Нажмите **✓ Создать**

### Детальная страница документа

Нажмите на документ в списке, чтобы открыть детальную страницу со вкладками: **📄 Текст**, **🔍 Рецензия**, **🏛 Архитектура**, **📋 ADR**, **🔌 API**, **🗺 Диаграммы**, **📝 Спецификации**.

---

## 7. AI-рецензия документа

### Что анализирует AI

| Раздел | Описание |
|--------|----------|
| **Резюме** | 2–6 предложений о документе |
| **Риски** | Список с метками: ВЫСОКИЙ / СРЕДНИЙ / НИЗКИЙ |
| **Вопросы заказчику** | Список вопросов для снятия неопределённости |
| **Критерии приёмки** | Проверяемые условия завершения работы |
| **Отсутствующие требования** | Что не хватает для начала разработки |
| **Архитектурные риски** | Технические риски реализации |
| **Уверенность** | Высокая / Средняя / Низкая |

### Режимы рассуждения (Reasoning)

Перед запуском рецензии на детальной странице документа можно выбрать один из трёх режимов:

| Режим | Обозначение | Описание |
|-------|------------|----------|
| **Direct** | По умолчанию | Модель сразу возвращает JSON-рецензию. Самый быстрый и дешёвый режим. |
| **CoT** | 🧠 CoT | Chain-of-Thought — модель сначала расписывает ход рассуждений по шагам (в блоке `<thinking>`), затем выдаёт JSON. Повышает качество на сложных/противоречивых документах. |
| **ReAct** | 🔄 ReAct | Reasoning + Acting — модель чередует Thought/Action/Observation (в блоке `<reasoning>`), имитируя итеративный анализ. Полезен для многоаспектных документов. |

После выбора режима нажмите **🔍 Рецензия** — блоки рассуждений будут автоматически отфильтрованы из финального ответа.

### Авто-сохранение в память проекта

После успешной рецензии система автоматически извлекает из результата:
- **Риски** (в т.ч. архитектурные) → сохраняются как `MemoryItem` с типом `risk`
- **Отсутствующие требования** → сохраняются как `requirement`
- **Принятые решения** → сохраняются как `decision`
- **Уроки проектов** → сохраняются как `episodic`

Все эти данные привязываются к проекту (если он указан в документе) и становятся доступны для **контекста будущих генераций**. Эмбеддинги сохраняются в FAISS-индекс для быстрого семантического поиска.

### Флаг ⚠ Требует проверки

Флаг `needs_review = true` устанавливается если: документ слишком краткий (< 8 слов), обнаружены противоречивые требования, уверенность AI низкая, или AI вернул некорректный формат JSON.

**Что делать при флаге:** прочитайте вопросы заказчику → уточните требования → создайте новую версию → запустите рецензию повторно.

### Экспорт рецензии

**JSON** (полные данные), **CSV** (Excel, UTF-8 BOM), **DOCX** (форматированный отчёт).

---

## 8. Архитектурная студия

### Контекст проекта в генерациях

Все инструменты архитектурной студии (URS, SRS, ADR, архитектура, API, диаграммы) автоматически получают **контекст проекта**:
- риски, извлечённые из предыдущих рецензий
- архитектурные решения, принятые ранее
- уроки аналогичных проектов

Если документ привязан к проекту (`project_name`), система передаёт эти данные в промпт LLM, что повышает связность документации внутри одного проекта.

### Генерация архитектурных рекомендаций

| Паттерн | Когда подходит |
|---------|---------------|
| Monolith | Небольшая команда, простой домен, MVP |
| Modular Monolith | Средняя команда, умеренная сложность |
| Microservices | Большая команда, высокая нагрузка |
| Event-Driven | Слабая связанность, асинхронные операции |
| CQRS | Разные требования к чтению/записи |
| Serverless | Непредсказуемая нагрузка, низкий бюджет |
| Hexagonal | Сложный домен, тестируемость |

### Диаграммы

**PlantUML** → [plantuml.com](https://plantuml.com) или IDE-плагин. **Mermaid** → [mermaid.live](https://mermaid.live).

---

## 9. База знаний (RAG)

```
Документы → Разбивка на фрагменты → Векторизация
                                            ↓
Вопрос → Keyword search + Semantic search → Top-K фрагментов
                                            ↓
                              LLM формирует ответ с цитатами
```

Если в базе знаний нет ответа → `needs_review = true`, ответ "Данных недостаточно". Все ответы сопровождаются цитатами-источниками.

---

## 10. Фреймворк памяти

| Тип | Назначение | Пример |
|-----|-----------|--------|
| 🔷 Семантическая | Концепции и стандарты | "В команде используем CQRS для высоконагруженных сервисов" |
| 📅 Эпизодическая | Уроки проектов | "Проект X: недооценили интеграцию с SAP — +3 недели" |
| ⚖️ Решения | Принятые решения | "Выбрали Kafka вместо RabbitMQ для хранения истории" |
| ⚠️ Риски | Типовые риски | "Интеграция с legacy — всегда +30% к оценке" |
| 📋 Требования | Извлечённые требования | "Клиент требует GDPR для EU рынка" |

### Механизм поиска

Каждый элемент памяти хранится с векторным эмбеддингом (модель `all-MiniLM-L6-v2`, 384-мерный вектор). Поиск использует **FAISS-индекс** (IndexFlatIP — косинусная близость) для быстрого семантического поиска. При недоступности FAISS используется гибридный скоринг: 40% keyword (Jaccard-пересечение) + 60% косинусная близость.

### Автоматическое пополнение

При запуске AI-рецензии документа система автоматически сохраняет найденные риски, требования, решения и уроки в память проекта. Это означает, что каждый новый документ в проекте видит контекст предыдущих рецензий.

### Применение

Элементы памяти автоматически учитываются при AI-рецензии и генерации документации: типовые риски, уроки проектов и решения обогащают промпт всех инструментов архитектурной студии (URS, SRS, ADR, архитектура, API, диаграммы).

---

## 11. Аудит-центр

Каждая AI-операция логируется: время выполнения, входные данные, результат, статус (✓ OK / ⚠ Требует проверки / ✗ Ошибка). На странице отображается статистика: процент успешных/требующих проверки/ошибочных операций, среднее время ответа AI.

---

## 12. Экономика проектов — ROI и окупаемость

**Где:** Боковое меню → 💰 Экономика

Экономический модуль автоматизирует расчёт стоимости разработки, окупаемости и ROI.

### Жизненный цикл

1. **Создание проекта** — привяжите документ (ТЗ/BRD/SRS) к build-проекту
2. **AI-декомпозиция задач** — AI разбивает требования на задачи по ролям (backend, frontend, QA, DevOps, Analyst) с оценкой часов
3. **Расчёт экономики** — введите ставки через слайдеры (живой предпросмотр ROI) → "Сохранить в БД"
4. **План/факт** — после внедрения введите фактические затраты

### Слайдеры с живым предпросмотром

В разделе "Economics" доступны слайдеры для каждой роли. При изменении любого слайдера CAPEX, ROI и срок окупаемости пересчитываются мгновенно на клиенте.

### График безубыточности

После расчёта отображается столбчатая диаграмма Cumulative Cost vs Cumulative Benefit на 12 месяцев. Точка пересечения = break-even.

### Формулы

```
CAPEX = Σ(часы × ставка)
OPEX/мес = хостинг + LLM + поддержка
Выгода/мес = часы_экономии × ставка
Окупаемость = CAPEX / (Выгода − OPEX)
ROI_12мес = ((Выгода − OPEX) × 12 − CAPEX) / CAPEX × 100
```

---

## 13. Экспорт бизнес-кейса

Из карточки проекта: кнопки ⬇ DOCX (Word) и ⬇ PDF — с CAPEX, OPEX, ROI и декомпозицией задач.

---

## 15. UML-диаграммы рабочих процессов

### 14.1 📦 Batch-рецензии

**Где:** Боковое меню → 📦 Batch-рецензии

Позволяет запустить AI-рецензию сразу для **нескольких ТЗ (до 50)** одним запросом — например, при массовом аудите бэклога требований.

| Шаг | Действие |
|-----|----------|
| 1 | Нажать **+ Новая batch-рецензия** |
| 2 | Указать название batch'а (например, «Аудит Q3-2026») |
| 3 | Добавить до 50 элементов: заголовок + текст ТЗ |
| 4 | Выбрать `reasoning_mode` (direct / cot / react) |
| 5 | Запустить — backend обрабатывает элементы по очереди через `with_audit()` |
| 6 | После завершения — список рецензий, ссылки на отдельные результаты |
| 7 | Экспорт сводного CSV по всему batch'у |

**REST:** `POST /batch-reviews`, `GET /batch-reviews`, `GET /batch-reviews/{id}`, `GET /batch-reviews/{id}/export/csv`.

### 14.2 ⚠️ Risk Catalog — каталог типовых рисков

**Где:** Боковое меню → ⚠️ Риски

Централизованный каталог рисков, который команда накапливает из рецензий (через `review_to_catalog.py`) и дополняет вручную. Содержит поля: `title`, `description`, `probability` (1–5), `impact` (1–5), `category` (infrastructure / requirements / integration / …), `status` (open / mitigated / closed), `mitigation`, `source`.

**REST:** `GET /risk-catalog`, `POST /risk-catalog`, `GET /risk-catalog/{id}`, `PUT /risk-catalog/{id}`, `DELETE /risk-catalog/{id}`, `GET /risk-catalog/stats`, `GET /risk-catalog/export/csv`.

### 14.3 📘 Уроки проектов (Lessons)

**Где:** Боковое меню → 📘 Уроки

Положительные и отрицательные уроки с прошлых проектов. Поля: `title`, `description`, `category` (architecture / devops / qa / process / …), `impact_type` (positive / negative), `root_cause`, `recommendation`. Экспорт в CSV.

**REST:** `GET /lessons`, `POST /lessons`, `GET /lessons/{id}`, `PUT /lessons/{id}`, `DELETE /lessons/{id}`, `GET /lessons/export/csv`.

### 14.4 📊 Dashboard

**Где:** Главный экран после входа → 📊 Dashboard

Сводка по системе: количество документов, рецензий, процент `needs_review`, средняя длительность AI-операций, разбивка по AI-провайдерам, **фактические расходы LLM за период** (Phase 3 — питает модуль экономики).

**REST:** `GET /dashboard/stats`, `GET /dashboard/recent-activity?limit=`, `GET /dashboard/stats-by-provider`, `GET /dashboard/actual-usage?days=30`.

### 14.5 ⚙️ Настройки AI-провайдеров

**Где:** Боковое меню → ⚙️ Настройки

Доступно **любому аутентифицированному пользователю** (admin / analyst / architect). Можно **определить провайдера автоматически** по API-ключу или Base URL, **проверить соединение до сохранения**, а затем сохранить настройку и активировать провайдера.

| Провайдер | Конфигурация |
|-----------|--------------|
| **Anthropic Claude** | `api_key`, `model` (claude-sonnet-4-20250514 по умолчанию), `temperature`, `max_tokens` |
| **OpenAI GPT** | `api_key`, `base_url`, `model` (gpt-4o), `temperature`, `max_tokens` |
| **ProxyAPI** (RU-прокси) | `api_key`, `base_url` (https://api.proxyapi.ru/anthropic), `model`, `temperature` |
| **OpenRouter** | `api_key`, `base_url`, `route` (`openrouter/free` \| `openrouter/fusion` \| `openrouter/pareto-code`), `model` |
| **Ollama** (локально) | `base_url`, `model` (qwen2.5:14b-instruct); список реально скачанных моделей подтягивается с `/v1/models` через `GET /settings/providers/ollama/models` |

> **Как использовать локальную модель через Ollama (без API-ключей, работа offline):**
>
> 1. Установите Ollama: <https://ollama.com/download> (Windows / macOS / Linux).
> 2. Скачайте модель: `ollama pull qwen2.5` (≈ 4.7 ГБ; можно также `qwen2.5:14b-instruct` для лучшего качества).
> 3. На странице **⚙️ Настройки** нажмите **+ Добавить провайдера** и выберите **Ollama**. В поле `base_url` введите `http://127.0.0.1:11434/v1` (если Ollama работает на хосте) или `http://host.docker.internal:11434` (если приложение в Docker). Нажмите **⚡ Тест связи** — должен появиться список скачанных моделей. Выберите нужную и сохраните.
> 4. *(Опционально)* В файле `.env` задайте `ENFORCE_LOCAL_ONLY=true` для полного отключения исходящих HTTPS-вызовов к облачным LLM (air-gapped-режим).
> 5. *(Важно)* Если модель работает медленно (CPU без GPU), увеличьте таймаут: `LLM_TIMEOUT=2400` в `.env`. Без этого долгие генерации URS/SRS обрываются и уходят в safe-fallback с `needs_review=true`.
> 6. Стоимость LLM-вызовов при работе через Ollama всегда равна **$0** — это подтверждено модулем экономики (фактические расходы `actual_llm_cost=0` в `audit_runs`).

**Действия:**
- **Определить провайдера** — `POST /settings/detect` по API-ключу / Base URL (эвристики: sk-ant- → Anthropic, sk-or- → OpenRouter и др.)
- Сохранить настройки провайдера → запись в `provider_settings` (приоритет над `.env`)
- **Тест подключения** (`POST /settings/test` с телом формы) — проверяет соединение по введённым / сохранённым данным (можно **до сохранения**)
- **Активировать** — переключить активного провайдера без перезапуска

В нижней части — кнопка **📥 Загрузить примеры для всех процессов**, которая вызывает `POST /seed/examples` (admin).

**REST:** `GET /settings/providers`, `POST /settings/providers`, `POST /settings/providers/activate?provider=`, `POST /settings/test`, `POST /settings/detect`, `GET /settings/active`, `GET /settings/providers/ollama/models`.

### 14.6 👥 Пользователи (только admin)

**Где:** Боковое меню → 👥 Пользователи (видна только админу)

CRUD по пользователям: создание, изменение роли, блокировка (`is_active=false`), сброс пароля. Кнопка **+ Добавить** открывает форму с полями `username`, `email`, `password` (мин. 6 символов), `full_name`, `role`.

**REST:** `GET /auth/users`, `POST /auth/register`, `PATCH /auth/users/{id}`, `POST /auth/users/{id}/reset-password`.

### 14.7 Стандарты документации (ГОСТ 34 / ISO 29148 / IEEE 830)

**Где:** На детальной странице документа — вкладка **Стандарты**

Система при генерации URS/SRS и диаграмм опирается на выбранные стандарты. Список стандартов хранится в таблице `documentation_standards` и засеян при первом запуске через `seed_default_standards()` (Alembic-миграция 0003 + fallback в lifespan).

Доступные семейства: `requirements` (ГОСТ 34, ISO 29148, IEEE 830) и `diagram` (C4, UML, ERD).

**REST:** `GET /standards?family=requirements|diagram`, `PATCH /documents/{id}/standards` (назначение стандартов документу).

---

### Sequence Diagram: Авторизация + AI-рецензия документа

```mermaid
sequenceDiagram
    actor U as Аналитик
    participant FE as Frontend
    participant API as FastAPI
    participant DB as Database
    participant LLM as LLM API

    U->>FE: Вводит логин/пароль
    FE->>API: POST /auth/login
    API->>DB: Проверка bcrypt-хеша
    API-->>FE: JWT access_token (8 часов)
    FE->>FE: Сохраняет токен в localStorage

    U->>FE: Создаёт документ
    FE->>API: POST /documents\nAuthorization: Bearer <token>
    API->>API: Проверка JWT + роль (require_analyst)
    API->>DB: Сохраняет документ
    API-->>FE: {document_id}

    U->>FE: Запускает рецензию
    FE->>API: POST /documents/{id}/review
    API->>DB: Читает текст + контекст памяти
    API->>LLM: Промпт + текст
    LLM-->>API: Строгий JSON ответ
    API->>API: Валидация Pydantic схемы

    alt Валидация успешна
        API->>DB: Сохраняет review (needs_review=false)
        API-->>FE: Рецензия с данными
    else Ошибка JSON / низкая уверенность
        API->>DB: Сохраняет review (needs_review=true)
        API-->>FE: Рецензия с флагом ⚠
    end
```

### Activity Diagram: Рабочий процесс аналитика

```mermaid
flowchart TD
    A([Начало]) --> B[Войти в систему\nлогин/пароль]
    B --> C{Документ уже\nсоздан?}
    C -->|Нет| D[Создать документ]
    C -->|Да| E[Открыть документ]
    D --> E
    E --> F[Запустить AI-рецензию]
    F --> G{needs_review?}
    G -->|true| H[⚠ Изучить вопросы\nзаказчику]
    G -->|false| I[Изучить рецензию]
    H --> J[Уточнить требования]
    J --> D
    I --> K{Нужна архитектура?}
    K -->|Да| L[Арх. студия:\nрекомендации + ADR]
    K -->|Нет| M[Экспорт рецензии]
    L --> M
    M --> N([Конец])
```

### State Diagram: Жизненный цикл рецензии

```mermaid
stateDiagram-v2
    [*] --> Создан : Документ загружен
    Создан --> В_обработке : Запуск рецензии
    В_обработке --> Готов : needs_review=false
    В_обработке --> НаПроверке : needs_review=true
    НаПроверке --> Создан : Аналитик уточнил требования
    Готов --> Экспортирован : Скачан JSON/CSV/DOCX
    Экспортирован --> [*]
```

### Class Diagram: Доменная модель (включая пользователей)

```mermaid
classDiagram
    class User {
        +String id
        +String username
        +String email
        +String hashed_password
        +String role
        +Boolean is_active
        +DateTime last_login
        +login()
        +hasPermission(permission)
    }

    class SpecDocument {
        +String id
        +String title
        +String text
        +String doc_type
        +String project_name
    }

    class KBDocument {
        +String id
        +String title
        +String text
        +String source_type
        +String source_id
    }

    class KBSnippet {
        +String id
        +String document_id
        +String snippet_text
        +Bytes embedding
    }

    class Review {
        +String id
        +String document_id
        +String review_json
        +Boolean needs_review
        +String confidence
        +String error
    }

    class QARun {
        +String id
        +String question
        +String answer
        +String sources_json
        +Boolean needs_review
        +String error
    }

    class AuditRun {
        +String id
        +String action
        +String status
        +String error
        +Integer duration_ms
    }

    class MemoryItem {
        +String id
        +String memory_type
        +String content
        +Float relevance_score
    }

    SpecDocument "1" --> "*" Review : имеет
    KBDocument "1" --> "*" KBSnippet : разбивается на
    KBDocument "1" --> "*" QARun : источник ответа
    AuditRun "*" --> "1" User : выполнен пользователем
```
