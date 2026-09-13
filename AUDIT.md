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
| Аудит каждого вызова групп A и B | `with_audit` в `/ai/review`, `/ai/answer_with_sources`, `/kb/ask`, `/documents/{id}/review`, `/kb/*` | ✅ |

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
| Нет секретов в текущем дереве | `bridge.py` удалён из рабочего дерева/индекса (`D bridge.py`), `.env` в историю не попадал | ✅ |
| Нет секретов в **истории** коммитов | ❌ `TR_KEY = "<redacted>..."` (`bridge.py`) остаётся в коммите `b4c27f5` ветки `agents/...` | ❌ требует `git filter-repo` + force-push (согласовать) |

---

## 9. Отчёт и мини-экономика
- `docs/graduation-report.md` — полный шаблон отчёта, сценарии, защита.
- `REPORT.md` — мини-экономика **отдельно по каждому модулю** (рецензия ТЗ vs поиск по БЗ) + 6 сценариев (3+3). ✅

---

## 10. Верификация

- **Полный pytest (чистая БД): `153 passed, 0 failed`** (117.9 с). Команда:
  ```bash
  cd backend
  python -m pytest -q
  ```
  Тестовая БД (`data/test_api.db`) автоматически пересоздаётся перед прогоном (`tests/conftest.py`), поэтому результат воспроизводим при повторных запусках.
- **Градуационные контрольные тесты:** `pytest tests/test_graduation_requirements.py` → 7 passed.

---

## 11. Сверка с критериями приёмки (пункт 10.7 промпта)

### Option2.md — ИИ-рецензент
| Критерий | Статус | Где/комментарий |
|---|---|---|
| `POST /documents` сохраняет документ и возвращает `document_id` | ✅ | documents.py:161; возвращает `DocumentOut` c `id` |
| `POST /documents/{id}/review` создаёт рецензию и возвращает `review_id` | ✅ | documents.py:338; 404 при отсутствии |
| Рецензия содержит `summary`, `risks`, `questions_to_client`, `acceptance_criteria` | ✅ | `ReviewSchema` + `run_ai_review` |
| Минимум 2 теста → `needs_review=true` (сырые/противоречивые) | ✅ | `specs/specs.jsonl` #7–10 |
| В веб-панели метка «требует проверки» + открытие рецензии | ✅ | `Reviews.tsx`, `DocumentDetail.tsx` |
| В `audit_runs` 10+ запусков и причины hand-check/ошибок | ✅ | `with_audit` на каждый вызов групп A/B |

### Option5.md — Система знаний
| Критерий | Статус | Где/комментарий |
|---|---|---|
| Документы добавляются и видны в витрине | ✅ | `POST/GET /kb/documents` (KBDocument) |
| Ответ содержит источники (цитаты) для 7 вопросов | ✅ (структурно; фактический LLM-прогон — см. RESULTS.md) | `kb_questions.jsonl` #1–7 |
| 3 вопроса → `needs_review=true` + «данных недостаточно» | ✅ (структурно) | `kb_questions.jsonl` #8–10 |
| Аудит фиксирует запросы и причины hand-check | ✅ | `with_audit`; `qa_runs.error="NO_SOURCES_FOUND"` |

---

## Хаус-кипинг / рекомендации перед сдачей
1. ✅ **Разделение `documents` на `spec_documents`/`kb_documents`** выполнено (миграция 0007 + перевод всех сервисов/роутеров; shim-модули удалены).
2. ✅ **Дубликат `analyst-architect-ai/` удалён** (`git rm -r`).
3. ✅ **Валидация:** полный `pytest` — **153 passed / 0 failed**; повторный прогон воспроизводим.
4. ⚠️ **Секрет в истории:** `TR_KEY = "<redacted>..."` из `bridge.py` (файл удалён из рабочего дерева). Текущее состояние чистое. Для полной зачистки нужен переписывающий историю инструмент:
   ```bash
   pip install git-filter-repo
   git filter-repo --path bridge.py --invert-paths --force
   # затем force-push (согласовать с командой) и перевыпустить ключ у провайдера
   ```
5. ⚠️ **Полный E2E с реальным LLM-провайдером** не выполнялся (нет ключа; локальная Ollama ≈6–7 мин/вызов на CPU). Инфраструктура подтверждена, офлайн-проверки зелёные — детали в `tests_data/RESULTS.md`.
