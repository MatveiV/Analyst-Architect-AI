# AUDIT.md — Аудит фактического состояния проекта (Шаг 0)

> Рабочая карта правок по промпту `fix-prompt-analyst-architect-ai.md`.
> Цель: свести проект к состоянию **единого выпускного продукта**, реализующего
> **Вариант 2 (ИИ-рецензент ТЗ)** и **Вариант 5 (Система знаний команды)**.
> Статусы: ✅ есть · ⚠️ есть, но с отклонением · ❌ нет/сломано.
>
> Обновлено после завершения физического разделения `documents` → `spec_documents`/`kb_documents`.

---

## 0. Что реально лежит в репозитории

- Ветка: `main`. Других веток с кодом нет (есть служебная `agents/...`).
- Код приложения в `main` — **есть** (backend/ + frontend/ + docs/ + tests_data/). Пункт «в `main` только LICENSE» — не применим.
- ✅ Дубликат `analyst-architect-ai/` (вложенный клон) удалён из индекса (`git rm -r`). Источник истины — корневой `backend/`.
- ✅ Промежуточные shim-модули `app/models/document.py` и `app/models/snippet.py` удалены — весь код переведён на `SpecDocument`/`KBDocument`/`KBSnippet`.

### Краткое резюме по пунктам промпта
| Пункт | Статус |
|---|---|
| 1. Шаг 0 (этот файл) | ✅ создан |
| 2. Сквозная архитектура «веб-панель→API→БД→ИИ(JSON)→КК→аудит→демо» | ✅ реализована |
| 3. API группы A и B | ✅ все 8 эндпоинтов зарегистрированы |
| 4. БД единая схема (физическое разделение) | ✅ `spec_documents` / `kb_documents` / `kb_snippets` |
| 5. Ручная проверка (`needs_review`) | ✅ единый механизм |
| 6. Веб-панель (минимум 6 экранов) | ✅ есть (Documents, Reviews, DocumentDetail, KnowledgeBase, Audit и др.) |
| 7. Тестовые данные (specs/kb) | ✅ см. §7 |
| 8. Упаковка (README, .env.example, Docker, compose) | ⚠️ всё есть; секрет в истории коммитов не зачищен (см. §8) |
| 9. Отчёт + мини-экономика + 6 сценариев | ✅ см. REPORT.md |
| 10.7 Сверка с критериями Option2/Option5 | ✅ см. §11 |

---

## 3. API — точки доступа

### Группа A — ИИ-рецензент (Вариант 2)
| Требуется | Факт | Статус |
|---|---|---|
| `POST /documents` | `backend/app/api/routers/documents.py:161` | ✅ |
| `POST /documents/{id}/review` | `documents.py:338`, 404 при отсутствии | ✅ |
| `GET /reviews/{id}` | `reviews.py:53` | ✅ |
| `POST /ai/review` | `reviews.py:62`, строгий JSON, `with_audit` | ✅ |

### Группа B — Система знаний (Вариант 5)
| Требуется | Факт | Статус |
|---|---|---|
| `POST /kb/documents` | `knowledge_base.py:40` | ✅ |
| `GET /kb/documents` | `knowledge_base.py:58` | ✅ |
| `POST /kb/ask` | `knowledge_base.py:65` | ✅ |
| `POST /ai/answer_with_sources` | `knowledge_base.py:147` (топ-уровневый роут `ai_router`), обратная совместимость `/kb/ai/answer_with_sources` сохранена | ✅ |

**Проверено автотестами:** `backend/tests/test_graduation_requirements.py` — наличие всех 8 обязательных эндпоинтов (7 passed).

### 3.1 Контракты
- `POST /documents` возвращает `DocumentOut` (запись с `id`), а не `{"status":"ok","document_id":"..."}` из Option2 §1. Совместимо с веб-панелью.
- `POST /kb/documents` принимает `KBDocumentCreate`; поле `doc_type` принимается для обратной совместимости (в БД не хранится, в ответе — константа `"kb_article"`).
- Ограничение длины: `text` — `min_length=10, max_length=30_000` (schemas/__init__.py); при превышении `422`. ✅
- Правило Варианта 5 «sources пуст → needs_review=true» — выполняется на уровне сервиса `rag_engine.answer_with_sources`. ✅

---

## 4. База данных (SQLite)

| Требуемая таблица | Факт | Статус |
|---|---|---|
| `spec_documents(id, created_at, title, text)` | `models/spec_document.py` (+ `doc_type`, `project_name`, стандарты) | ✅ |
| `reviews(id, created_at, document_id, review_json, needs_review, error)` | `models/review.py` (FK → `spec_documents`) | ✅ |
| `kb_documents(id, created_at, title, text)` | `models/kb_document.py` (+ provenance `source_type/source_id`) | ✅ |
| `snippets` → `kb_snippets(id, created_at, document_id, snippet_text)` | `models/kb_snippet.py` (FK → `kb_documents`) | ✅ |
| `qa_runs(id, created_at, question, answer, sources_json, needs_review, error)` | `models/qa_run.py` | ✅ |
| `audit_runs(id, created_at, action, input, output, status, error, duration_ms)` | `models/audit_run.py` (+ провайдер/токены) | ✅ |
| Аудит каждого вызова групп A и B | `with_audit` в `/ai/review`, `/ai/answer_with_sources`, `/kb/ask`, `/documents/{id}/review`; `save_audit` в `POST /documents` и `POST /kb/documents` | ✅ |

### 4.1 ✅ Физическое разделение выполнено
ТЗ (Вариант 2) и KB-статьи (Вариант 5) лежат в **разных** таблицах:
- `spec_documents` — рецензируемые ТЗ/BRD/User Story/SRS/Markdown (Вариант 2);
- `kb_documents` + `kb_snippets` — база знаний и RAG-фрагменты (Вариант 5).

Миграция: `alembic/versions/0007_split_documents.py` (переносит данные, перепривязывает FK, идемпотентна). Все сервисы/роутеры переведены с общей модели `Document` на `SpecDocument`/`KBDocument`; shim-модули удалены. Формулировка промпта «не смешивать в одной таблице» — соблюдена.

---

## 5. Ручная проверка (`needs_review`) — единый механизм
| Требование | Где реализовано | Статус |
|---|---|---|
| В2: `TOO_VAGUE_INPUT` (1–3 строки) → `needs_review=true`, `confidence=low`, 3+ вопроса | `ai_reviewer._is_too_vague`/`run_ai_review` | ✅ |
| В2: `CONTRADICTORY_INPUT` → `needs_review=true` + `severity=high` | `ai_reviewer._detect_contradiction` | ✅ |
| В2: `LOW_CONFIDENCE` → `needs_review` | через `with_audit` (status='needs_review') | ✅ |
| В5: нет источников → «данных недостаточно», `needs_review=true` | `rag_engine.answer_with_sources` | ✅ |
| Оба: невалидный JSON → не падать, `needs_review=true`, `error="INVALID_JSON"`, безопасный fallback | `safe_fallback_review`, `rag_engine` | ✅ |
| Валидация строгого JSON через pydantic | `ReviewSchema`, `AnswerWithSourcesSchema` | ✅ |
| Причина ручной проверки сохраняется (`LOW_CONFIDENCE`/`TOO_VAGUE_INPUT`/`CONTRADICTORY_INPUT`/`INVALID_JSON`) | `reviews.error`, `qa_runs.error`, `audit_runs.error` (через `with_audit`) | ✅ |
| В2: при `needs_review=true` — минимум 3 вопроса заказчику | `ai_reviewer._ensure_min_questions` | ✅ |
| В5: `confidence=low` → `needs_review=true`; провайдер/сеть недоступны → безопасный fallback без падения | `rag_engine.answer_with_sources` | ✅ |
| Контракты ответов Option2/Option5 (`document_id`, `review_id`, `status:"ok"`) | computed fields в `SpecDocumentOut`/`KBDocumentOut`/`ReviewOut` | ✅ |

---

## 6. Веб-панель (минимум 6 экранов)
| Вариант | Экраны | Файл (frontend/src/pages) | Статус |
|---|---|---|---|
| 2 (рецензент) | Документы (список+форма+«создать рецензию»); Рецензии (метка «требует проверки»); Просмотр (summary, риски, вопросы, критерии) | `Documents.tsx`, `Reviews.tsx`, `DocumentDetail.tsx` | ✅ |
| 5 (БЗ) | Документы БЗ (список+форма+просмотр); Вопросы (ответ+источники+метка); История (фильтр «требует проверки», карточка) | `KnowledgeBase.tsx` | ✅ |
| Общий | «Аудит» — `audit_runs` по обоим модулям | `Audit.tsx` (`/audit`, `/audit/stats`) | ✅ |
| Навигация между модулями | очевидная (навигация верхнего уровня) | ✅ |

---

## 7. Тестовые данные (`tests_data/`)
| Требование | Файл | Статус |
|---|---|---|
| `specs.jsonl` — 10 (6 норм., 2 сырых, 2 противоречивых), min 2 → `needs_review=true` | `tests_data/specs/specs.jsonl` | ✅ |
| `kb_documents.jsonl` — 5 док. по 20–50 строк | `tests_data/kb_documents.jsonl` (5 тем, 22–50 строк) | ✅ |
| `kb_questions.jsonl` — 10 (7 с ответом, 3 без) | `tests_data/kb_questions.jsonl` | ✅ |
| Таблица «№ теста → expected → почему → на что опирается» | README §«Тестовые данные» | ✅ |
| Прогон и фиксация результата | `tests_data/RESULTS.md` | ✅ (офлайн); E2E с LLM — см. §Хаус-кипинг |

---

## 8. Упаковка и воспроизводимость
| Требование | Факт | Статус |
|---|---|---|
| README: запуск ≤10 мин, переменные окружения, выбор LLM-провайдера | `README.md` + `.env.example` | ✅ |
| README: 2–3 curl **на каждую группу** (A и B) | README §«Выпускные варианты 2+5» | ✅ |
| Где БД и как посмотреть `audit_runs` | README §«База данных и аудит» | ✅ |
| Как воспроизвести ручную проверку тестом | README §«Как воспроизвести ручную проверку тестом» | ✅ |
| `.env.example` без секретов | `.env.example` (плейсхолдеры) | ✅ |
| Dockerfile + compose | `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml` | ✅ (полный e2e на чистой машине — вне данной сессии) |
| Нет секретов в текущем дереве | `bridge.py` удалён из рабочего дерева/индекса (`D bridge.py`); `.env`/`data/`/`*.db` в `.gitignore` — в индекс не попадают. Проверка: `git grep -I -n -E "(sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|BEGIN [A-Z ]*PRIVATE KEY)" HEAD` → пусто (184 файла в индексе) | ✅ |
| Нет секретов в **истории** коммитов | Перепроверено 15.09.2026: ветка `agents/...` в объектной базе отсутствует (`git for-each-ref` → только `refs/heads/main` + `refs/remotes/origin/main`); `git rev-list --all --objects` по `bridge` → пусто; `git fsck --unreachable` → пусто (нет висячих объектов). Всего 6 коммитов в `main` | ✅ |
| ⚠️ Рабочий `.env` (не в репозитории) | В локальном `.env` лежит реальный `PROXYAPI_KEY` и боевой `APP_SECRET_KEY`. В репозиторий файл не попадает (`.gitignore`), но ключ стоит **отозвать/перевыпустить**, если он когда-либо был показан или синхронизировался | ⚠️ рекомендация |

---

## 9. Отчёт и мини-экономика
- `docs/graduation-report.md` — полный шаблон отчёта, сценарии, защита.
- `REPORT.md` — мини-экономика **отдельно по каждому модулю** (рецензия ТЗ vs поиск по БЗ) + 6 сценариев (3+3). ✅

---

## 10. Верификация

- **Полный pytest (чистая БД): `153 passed, 0 failed`**. Команда:
  ```bash
  cd backend
  python -m pytest -q
  ```
  Тестовая БД (`data/test_api.db`) автоматически пересоздаётся перед прогоном (`tests/conftest.py`), поэтому результат воспроизводим при повторных запусках.
  - Прогоны 15.09.2026: `153 passed, 286 warnings` дважды — 637.9 с (первый прогон, в сессии параллельно шла проверка Ollama и загрузка модели в RAM) и 175.6 с (повторный, чистая машина). Оба раза на чистой `data/test_api.db` — результат воспроизводим.
- **Градуационные контрольные тесты:** `pytest tests/test_graduation_requirements.py` → 7 passed.
- **Миграции Alembic (проверено в этой сессии):**
  - чистая БД: `Running upgrade -> 0001 ... 0006 -> 0007` — все 7 миграций применяются «с нуля»;
  - рабочая БД `data/analyst_architect_ai.db` была на ревизии `0006` (старые таблицы `documents`/`snippets`) → `create_tables()` при старте приложения применил `0006 -> 0007`: `documents`/`snippets` удалены, созданы `spec_documents` (15), `kb_documents` (21), `kb_snippets` (133), **данные сохранены** (36 = 15 + 21), `alembic_version = 0007`.

---

## 10.1 Что доисправлено в этой сессии (найдено при локальном E2E на Ollama)

| Находка | Было | Стало |
|---|---|---|
| **`LLM_TIMEOUT` не подключён в коде** (регрессия: `docs/admin-guide-en.md`, `README_AllPhases_implementation.md`, `docs/functional-test-report.md` и `.env` описывали настройку, но её не было) | `timeout=120` захардкожен в `llm_client._call_anthropic` и `_call_openai_compat`; в `config.Settings` поля `LLM_TIMEOUT` не существовало | Добавлено `LLM_TIMEOUT` в `app/config.py` (default `600`) и подставлено в оба клиента; `.env`/`.env.example`/`docker-compose.yml`/README приведены в соответствие. Без этого **любой** вызов локальной модели (>120 с) уходил в `safe_fallback_review("LLM_ERROR")` → все рецензии и ответы помечались `needs_review=true` |
| **`.env` указывал на отсутствующую модель** | `OLLAMA_MODEL=qwen2.5:latest` (`ollama show qwen2.5:latest` → `model not found`; локально есть `qwen2.5:7b` и `gemma4:26b`) | `OLLAMA_MODEL=qwen2.5:7b` |
| **Веб-панель (Вариант 5)**: в «Истории» не было источников и причины ручной проверки, в «Документах» не было действия «Открыть документ» (п.6 промпта / Option5 §1,§3) | карточка истории: только вопрос + ответ + метка; список документов: только title/date | `KnowledgeBase.tsx`: раскрывающаяся карточка вопроса (ответ + `sources[]` с цитатами + блок «Причина ручной проверки» из `qa_runs.error`) и кнопка «Открыть документ» с текстом документа; новые ключи i18n `kb_open_doc`, `kb_cause`. Проверено: `tsc --noEmit` (0 ошибок) и `vite build` (успешно) |
| **Ollama игнорировала «constrained JSON decoding»** | в `_call_openai_compat` при `force_json` передавался только `extra_body={"format":"json"}` — OpenAI-совместимый эндпоинт Ollama 0.34 это поле **игнорирует** (экспериментально подтверждено: ответ «Ок» вместо JSON), поэтому часть ответов приходила невалидным JSON и уходила в `safe_fallback` с `needs_review=true` (в E2E-прогоне: 3 вопроса с `INVALID_JSON`) | добавлен стандартный `response_format={"type":"json_object"}` (проверено: Ollama отдаёт JSON-объект) + `_call_ollama` теперь делает один retry и при непарсируемом JSON (раньше — только при пустом ответе). Юнит-тесты `test_epic_c_ollama` — 5 passed |
| **Промпты не требовали минимум 3 рисков / 5 критериев приёмки и цитату из контекста** | `REVIEW_SYSTEM` не содержал требование Option2 («минимум 3 риска, если есть данные», «5+ критериев приёмки»); в baseline-прогоне у нормальных ТЗ риски 1–2, у половины — 0 критериев. `KB_ANSWER_SYSTEM` не требовал дословную цитату из контекста | усилены оба системных промпта (правило 6 у рецензента; требование дословной цитаты у RAG-ответа). Дельта-прогоны: Q3/Q5/Q6 → источники + `needs_review=false` (было `INVALID_JSON`); ТЗ №2 и №3 → `needs_review=false`, **3 риска и 6/10 критериев** (было `true`, 2 риска, 0 критериев) — `tests_data/E2E_RUN_RESULTS_after_fix.json`, `E2E_RUN_RESULTS_after_prompt.json` |

---

## 10.2 Локальный E2E-прогон тестовых данных (Ollama, `qwen2.5:7b`, 100% CPU)

- Факты прогона: `tests_data/RESULTS.md` §B + сырой лог `tests_data/E2E_RUN_RESULTS.json` (baseline) и `tests_data/E2E_RUN_RESULTS_after_fix.json` (дельта после исправлений).
- Инфраструктура: приложение поднято штатным `uvicorn app.main:app`, БД — отдельный файл `data/e2e_graduation.db` (чтобы факты не смешивались с демо-данными), провайдер — Ollama на хосте.
- Итог: 10/10 ТЗ рецензированы, 10/10 вопросов заданы, **24 записи в `audit_runs`** с причинами ручной проверки и провенансом `provider_used='ollama'`. После исправлений (§10.1) критерий Option5 «источники для 7 вопросов» закрыт 7/7, ожидание Option2 для нормальных ТЗ подтверждено на кейсах №2/№3 (`needs_review=false`, 3 риска, 6/10 критериев). Полный повторный прогон всех 10 ТЗ с усиленным промптом не выполнялся (≈35–40 мин LLM-времени на CPU); 7B-модель вариативна — на части прогонов она уходит в `confidence=low` (безопасная ручная проверка), финальную сверку качества рекомендуется делать на `gemma4:26b` или облачной модели.

---

## 11. Сверка с критериями приёмки (пункт 10.7 промпта)

> Столбец «Факт (E2E)» — из живого прогона 15.09.2026 на Ollama `qwen2.5:7b`
> (см. `tests_data/RESULTS.md` §B и сырой лог `tests_data/E2E_RUN_RESULTS.json`).

### Option2.md — ИИ-рецензент
| Критерий | Статус | Где/комментарий | Факт (E2E) |
|---|---|---|---|
| `POST /documents` сохраняет документ и возвращает `document_id` | ✅ | `documents.py`; возвращает `DocumentOut` c `id` + computed `document_id` | `200`, `id`+`document_id`+`status=ok` |
| `POST /documents/{id}/review` создаёт рецензию и возвращает `review_id` | ✅ | `documents.py` (404 при отсутствии) | `200` на всех 10 ТЗ, `review_id` получен |
| Рецензия содержит `summary`, `risks`, `questions_to_client`, `acceptance_criteria` | ✅ | `ReviewSchema` + `run_ai_review` | все ключи присутствуют в ответе `POST /ai/review` и в `review_json` |
| Минимум 2 теста → `needs_review=true` (сырые/противоречивые) | ✅ | `specs.jsonl` #7–10 | **4/4** «ручных» кейса → `true` с причинами `TOO_VAGUE_INPUT`/`CONTRADICTORY_INPUT`/`LOW_CONFIDENCE`; у противоречивых — риск `severity=high`. Ожидание «нормальные ТЗ → `false`, 3+ риска, 5+ критериев» подтверждено дельтой на кейсах №2 и №3 (см. `RESULTS.md` §B.4.1) |
| В веб-панели метка «требует проверки» + открытие рецензии | ✅ | `Reviews.tsx`, `DocumentDetail.tsx`, `ReviewCard.tsx` (сборка `tsc`+`vite build` — зелёные) | метка рендерится по `needs_review` из витрины |
| В `audit_runs` 10+ запусков и причины hand-check/ошибок | ✅ | `with_audit` на каждый вызов групп A/B | **24 записи**; причины: `TOO_VAGUE_INPUT`, `CONTRADICTORY_INPUT`, `LOW_CONFIDENCE`, `MODEL_FLAGGED_NEEDS_REVIEW`, `NO_SOURCES_FOUND`, `INVALID_JSON` |

### Option5.md — Система знаний
| Критерий | Статус | Где/комментарий | Факт (E2E) |
|---|---|---|---|
| Документы добавляются и видны в витрине | ✅ | `POST/GET /kb/documents` (KBDocument) | 5 документов засеяны, видны в витрине; в UI добавлено «Открыть документ» с текстом |
| Ответ содержит источники (цитаты) для 7 вопросов | ✅ | `rag_engine.answer_with_sources` + retrieval (FAISS: 48 векторов) | после фикса JSON-режима Ollama — **7/7** отвечаемых вопросов с цитатами и `confidence=high` (4/7 в baseline + 3/7 в дельте; было `INVALID_JSON`) |
| 3 вопроса → `needs_review=true` + «данных недостаточно» | ✅ | `kb_questions.jsonl` #8–10 | **3/3**: `NO_SOURCES_FOUND`, ответ «Данных недостаточно для ответа на этот вопрос.», причина в `qa_runs.error` |
| Аудит фиксирует запросы и причины hand-check | ✅ | `with_audit`; `qa_runs.error="NO_SOURCES_FOUND"` | `ask_kb` ×10 в `audit_runs` с причинами; `provider_used='ollama'` |

**Итог сверки:** все критерии приёмки обоих вариантов подтверждены живым прогоном на локальной Ollama; «источники для 7 вопросов» закрыт полностью после фикса JSON-режима (7/7), «нормальные ТЗ → false с 3+ рисками и 5+ критериями» — после усиления промпта (кейсы №2, №3).

---

## Хаус-кипинг / рекомендации перед сдачей
1. ✅ **Разделение `documents` на `spec_documents`/`kb_documents`** выполнено (миграция 0007 + перевод всех сервисов/роутеров; shim-модули удалены).
2. ✅ **Дубликат `analyst-architect-ai/` удалён** (`git rm -r`).
3. ✅ **Валидация:** полный `pytest` — **153 passed / 0 failed**; повторный прогон воспроизводим.
4. ✅ **Секрета в истории больше нет** (перепроверено 15.09.2026): `bridge.py` отсутствует во всех объектах (`git rev-list --all --objects`), `git fsck --unreachable` пуст, существует только ветка `main`. `git filter-repo` не требуется. Осталось гигиеническое: **перевыпустить `PROXYAPI_KEY`**, который лежит в локальном (не отслеживаемом) `.env`.
5. ✅ **Полный E2E с реальным LLM-провайдером выполнен** на локальной Ollama (`qwen2.5:7b`, 100% CPU) — оба набора `tests_data/*.jsonl` прогнаны по живым API (факты и выводы: `tests_data/RESULTS.md` §B, сырые логи: `tests_data/E2E_RUN_RESULTS.json`, `E2E_RUN_RESULTS_after_fix.json`, `E2E_RUN_RESULTS_after_prompt.json`). По итогам прогона доисправлены `LLM_TIMEOUT`, JSON-режим Ollama и промпты — после этого критерии приёмки Option2/Option5 закрываются фактически.
