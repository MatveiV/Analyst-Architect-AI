# RESULTS.md — Прогон тестовых данных (пункт 10.4 промпта)

> Здесь фиксируется, что реально вернула система на тестовых входных наборах.
> Два уровня проверки: **(A) офлайн/контрактные** (не требуют LLM-ключа, выполняются всегда) и
> **(B) end-to-end с LLM-провайдером** (нужен `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`PROXYAPI_KEY`/Ollama).

---

## A. Офлайн-проверки (выполнены, проходят)

| Проверка | Как | Результат |
|---|---|---|
| **Полный прогон всего набора** | `pytest -q` (чистая `data/test_api.db`) | ✅ **153 passed, 0 failed** (117.9 с) |
| Наличие всех 8 обязательных эндпоинтов групп A и B | `pytest backend/tests/test_graduation_requirements.py` | ✅ 7 passed (включая `POST /ai/answer_with_sources`) |
| `specs.jsonl` — 10 записей, ≥2 с `expected_needs_review=true` | та же тест-команда | ✅ |
| `kb_documents.jsonl` — 5 документов с title+text (20–50 строк) | та же тест-команда | ✅ (22–50 строк) |
| `kb_questions.jsonl` — 10 (7 с ответом, 3 без) | та же тест-команда | ✅ |
| Лимит входа `text` (max 30 000), минимум 10 | та же тест-команда | ✅ |
| Юнит-логика ручной проверки: `TOO_VAGUE`/`CONTRADICTORY` → `needs_review=true` | `pytest tests/test_main.py::TestAIReviewerLogic` | ✅ 10 passed |
| Воспроизводимость: повторный прогон без «залипания» данных | `pytest -q` дважды подряд | ✅ (conftest пересоздаёт тестовую БД) |

## B. End-to-end с LLM (ожидаемые значения из разметки)
> Прогон требует провайдера и выполняется списком ниже. **Заполнить фактические значения после прогона.**

### Вариант 2 — `tests_data/specs/specs.jsonl`
| № | Ожидаемый `needs_review` | Причина (разметка) | Факт (заполнить) |
|---|---|---|---|
| 1–6 | false | нормальные мини-ТЗ | ⏳ |
| 7 | true | `TOO_VAGUE_INPUT` | ⏳ |
| 8 | true | вырожденный ввод | ⏳ |
| 9 | true | `CONTRADICTORY_INPUT` | ⏳ |
| 10 | true | `CONTRADICTORY_INPUT` | ⏳ |

Как прогнать:
```bash
# 1) загрузить 10 ТЗ в БД (админ)
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -d "username=admin&password=admin123" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -X POST http://localhost:8000/seed/documents -H "Authorization: Bearer $TOKEN"
# 2) для каждого документа поочерёдно вызвать рецензию
curl -X POST http://localhost:8000/documents/{DOC_ID}/review -H "Authorization: Bearer $TOKEN"
# 3) факты взять из `GET /reviews` (needs_review) и `GET /audit?action=review` (error/причина)
```

### Вариант 5 — `tests_data/kb_questions.jsonl`
| № | Ожидаемый `needs_review` | Опора (документ) | Факт (заполнить) |
|---|---|---|---|
| 1–7 | false | правила/FAQ/шаблоны/словарь/процесс | ⏳ |
| 8–10 | true | документа в базе нет | ⏳ |

Как прогнать:
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -d "username=admin&password=admin123" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -X POST http://localhost:8000/seed/kb-documents -H "Authorization: Bearer $TOKEN"
# затем для каждого вопроса:
curl -X POST http://localhost:8000/kb/ask -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"question":"<вопрос>"}'
# источники/needs_review → ответ; в `GET /kb/history` и `GET /audit` фиксируются причины
```

---

## Статус на дату последнего прогона
- **Офлайн/контрактные проверки:** ✅ выполнены (см. раздел A) — полный `pytest` даёт **153 passed / 0 failed**, включая `tests/test_graduation_requirements.py` и `tests/test_main.py::TestAIReviewerLogic`.
- **E2E-инфраструктура (локальная Ollama вместо API-ключа):** ✅ настроена и проверена.
  - `.env`: `LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL=http://127.0.0.1:11434/v1`, `OLLAMA_MODEL=qwen2.5:7b`.
  - `ollama list`: `qwen2.5:7b` (7.6B, Q4) и `gemma4:26b`.
  - Механика подтверждена: OpenAI-совместимый клиент (`app/services/llm_client.py::_call_ollama` → `_call_openai_compat(force_json=True)`) успешно получил валидный JSON от `qwen2.5:7b`. Это тот же код-путь, что использует `POST /ai/review` и `POST /kb/ask`.
  - **Производительность (важно):** один вызов на чистом CPU ≈ **6–7 минут**. Полный E2E на 20 входов (`specs.jsonl` ×10 + `kb_questions.jsonl` ×10) занял бы **~2 часа** на данном железе — поэтому в этой сессии полный прогон не выполнялся.
- **Как пройти полный E2E (ожидает CPU/GPU):** выполнить команды из раздела B и заполнить колонки «Факт». На машинах с GPU (Ollama + CUDA/ROCm) вызовы ускоряются в 10–50 раз.