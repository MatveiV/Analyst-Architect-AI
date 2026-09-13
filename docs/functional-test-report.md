# Отчёт о функциональном тестировании

> Дата: 20.08.2026
> Окружение: Windows 11, Python 3.14, Node 18+, FastAPI (uvicorn), Vite, Ollama `qwen2.5:latest`
> Данные: `filesdocs/demo-documents/` — 3 темы × 6 файлов (полное ТЗ, сырое ТЗ, 3 KB-статьи, уроки)
> Скрипт прогона: `filesdocs/test_demo_flow.py` (пофазовый, с сохранением состояния в `filesdocs/test_state.json`)
> ⚠️ Одноразовые скрипты прогона (`test_demo_flow.py`, `arch_step.py`, `check_*.py`, `debug_*.py` и др.) позже удалены из репозитория при зачистке артефактов — этот отчёт сохранён как исторический снимок; воспроизвести сценарий сегодня можно через `POST /seed/examples` (admin) и curl-примеры из README.

---

## Сводка

| # | Сценарий | Результат | Детали |
|---|----------|-----------|--------|
| 1 | Загрузка документов | ✅ PASS | 6 ТЗ + 9 KB-статей |
| 2 | AI-рецензии | ✅ PASS | 6/6, все сырые ТЗ → `needs_review=true` |
| 3 | Пакетная рецензия | ✅ PASS | 6/6 обработано, 0 ошибок |
| 4 | База знаний (RAG) | ✅ PASS | Ответы с источниками, confidence=high |
| 5 | Уроки проекта | ✅ PASS | 2 ручных + автоиндексация в KB |
| 6 | Экономика | ✅ PASS | 411.6 ч, CAPEX/OPEX/ROI, фактический расход LLM |
| 7 | ArchStudio (URS/SRS/ADR/диаграммы) | ✅ PASS | URS 20 тр., SRS 20 тр., ADR, 8 диаграмм, coverage=полное |
| 8 | Аудит и дашборд | ✅ PASS | 22 запуска, provider=ollama, 0 ошибок |
| 9 | Сравнение рецензий (diff) | ✅ PASS | Показывает изменения summary/рисков |
| 10 | Экспорты | ✅ PASS* | Markdown/DOCX/full-package — после фикса бага (см. §5) |

\* — в ходе тестирования обнаружен и исправлен баг (экспорты падали с 500 на кириллице в заголовке).

---

## 1. Документы

Загружено через `POST /documents` (полное и сырое ТЗ каждой темы) и `POST /kb/documents` (KB-статьи):

| Тема | full ТЗ | raw ТЗ | KB-статьи |
|------|---------|--------|-----------|
| crm (CRM для заказов на разработку) | ✅ | ✅ | 3 |
| trading (Торговая платформа) | ✅ | ✅ | 3 |
| insurance (Страховые продукты) | ✅ | ✅ | 3 |

Всего: 6 документов типа `tz` + 9 статей типа `kb_article`.

## 2. AI-рецензии (`POST /documents/{id}/review`)

| Документ | needs_review | confidence | risks | missing | criteria |
|----------|--------------|------------|-------|---------|----------|
| crm_full | **false** | medium | 2 | 3 | 4 |
| crm_raw | **true** | low | 2 | 2 | 2 |
| trading_full | true | medium | 2 | 3 | 4 |
| trading_raw | **true** | low | 4 | 4 | 3 |
| insurance_full | true | medium | 2 | 2 | 4 |
| insurance_raw | **true** | low | 2 | 4 | 2 |

**Ключевой результат (соответствует требованиям демо):**
- ✅ Все 3 «сырых» ТЗ честно помечены `needs_review=true`, confidence=low — система не делает вид, что уверена при недостатке данных.
- ✅ Полное CRM-ТЗ рецензировано уверенно (`needs_review=false`).
- ℹ️ `trading_full` и `insurance_full` тоже помечены `needs_review=true` — это честное поведение (в ТЗ торговой платформы есть противоречие «без плеча» vs «Margin Call»; в страховом ТЗ — открытые комплаенс-вопросы).

## 3. Пакетная рецензия (`POST /batch-reviews`)

- Статус: **completed**, total=6, completed=6, needs_review=5, **errors=0**
- Каждый элемент обработан независимо; сводка и фильтр `?needs_review=true` работают.
- CSV-экспорт пакета: ✅ (692 байта, BOM для Excel).

## 4. База знаний (`POST /kb/ask`)

| Вопрос | sources | confidence | needs_review |
|--------|---------|------------|--------------|
| «Что делать, если аналитик оценил проект, а клиент изменил требования?» | 1 (KB crm #2 — FAQ) | high | false |
| «Как формируется себестоимость проекта по часам разработчиков?» | 1 (KB crm #3 — словарь) | high | false |

- ✅ Гибридный поиск подтягивает правильные источники.
- ✅ Автоиндексация артефактов в KB: 10 статей с бейджами `URS`/`SRS`/`ADR`/`диаграммы`/`урок` (всего 21 KB-документ).

## 5. Уроки проекта, риски

- Уроки: 2 созданы вручную (negative estimation + positive process) → автоматически попали в KB.
- Risk Catalog: 18 рисков автозаполнены из рецензий (`review_to_catalog.py`).

## 6. Экономика (`/build-projects`)

| Шаг | Результат |
|-----|-----------|
| Создание проекта | ✅ статус draft |
| AI-декомпозиция задач | ✅ 411.6 ч, confidence=high |
| Экономический расчёт | ✅ CAPEX=967 000 ₽, OPEX/мес=25 000 ₽, ROI(12м)=-131% |
| Фактический расход LLM | ✅ `llm_cost_source=actual_usage` — токены из audit_runs за 30 дней |

ℹ️ Отрицательный ROI — ожидаемо при дефолтных параметрах выгоды (time_saved_hours=0): формула прозрачная, меняется ручным вводом выгоды.

## 7. ArchStudio (`/documents/{id}/generate-*`)

Стандарты на документе: **ГОСТ 34.602-2020** (требования) + **UML** (диаграммы) — через `PATCH /documents/{id}/standards`.

| Артефакт | Результат | Стандарт |
|----------|-----------|----------|
| URS | ✅ 20 пользовательских требований, needs_review=false, confidence=medium | GOST_34_602 |
| SRS | ✅ 20 функциональных требований, needs_review=false, confidence=high | GOST_34_602 |
| ADR | ✅ «ADR-001: Реализация единой CRM для управления заказами» | — |
| Диаграммы | ✅ 8 типов (c4_context…flowchart), render_status=external_fallback | UML |
| Coverage | ✅ is_fully_covered=true (требования+диаграммы+критерии) | — |

ℹ️ `external_fallback` для рендера диаграмм — ожидаемое поведение без локального Kroki: диаграммы сохраняются кодом (PlantUML/Mermaid), в DOCX-экспорте — с пометкой «рендер недоступен».

## 8. Аудит и дашборд

- `GET /audit` — 22 записи, у каждой `provider_used=ollama`, `is_local_provider=true`.
- `GET /audit/stats` — total=22, ok=9, errors=0, needs_review=13, error_rate_pct=0%.
- `GET /dashboard/stats-by-provider` — ollama: 22 запуска, avg_duration=400 с.
- `GET /dashboard/actual-usage` — 34 622 входных / 13 465 выходных токенов за 30 дней.

## 9. Сравнение рецензий (`GET /reviews/diff`)

- ✅ Два прогона рецензии одного документа сравниваются: summary diff (было/стало), риски added/removed, флаги confidence/needs_review.

## 10. Экспорты

| Экспорт | До фикса | После фикса |
|---------|----------|-------------|
| `GET /documents/{id}/export/markdown` | 500 | ✅ 200 |
| `GET /documents/{id}/export/docx` | 500 | ✅ 200 |
| `GET /documents/{id}/export/full-package/docx` | 500 | ✅ 200 |
| `GET /batch-reviews/{id}/export/csv` | — | ✅ 200 |
| `GET /lessons/export/csv` | — | ✅ 200 |
| `GET /reviews/{id}/export/json` | — | ✅ 200 |

---

## Найденные и исправленные баги

### Баг 1: 500 на всех экспортах документов с кириллицей в названии
- **Симптом:** `GET /documents/{id}/export/{markdown,docx,full-package/docx}` → 500.
- **Причина:** заголовок `Content-Disposition: attachment; filename={doc.title}.docx` содержит кириллицу; Starlette кодирует HTTP-заголовки в latin-1 → `UnicodeEncodeError`.
- **Фикс:** `documents.py` — `filename*=UTF-8''{quote(doc.title)}` (RFC 5987). Затронуты 3 эндпоинта.

### Баг 2: URS/SRS-генерация падала в safe-fallback на локальной модели
- **Симптом:** `generate-urs`/`generate-srs` возвращали `needs_review=true` с 0 элементов за ~30 минут «работы».
- **Причина:** дефолтный таймаут openai SDK 600с; qwen2.5 локально генерирует URS/SRS 19–20 мин → timeout → safe-fallback.
- **Фикс:** добавлена настройка `LLM_TIMEOUT` (`config.py`, `.env`, `llm_client.py`); в `.env` установлено `2400`. После фикса: URS 20 требований (19.7 мин), SRS 20 требований (19.1 мин), оба `needs_review=false`.

---

## Ограничения локального окружения (не баги)

1. **Один воркер uvicorn** — пока идёт LLM-вызов (2–30 мин), остальные запросы ждут. Для параллельной работы нужен `uvicorn --workers N` или очередь задач (Celery/RQ).
2. **Рендер диаграмм** — без Kroki все диаграммы `external_fallback` (код сохраняется, картинки нет).
3. **Производительность LLM** — рецензия 2–8 мин, URS/SRS ~20 мин на qwen2.5 (CPU). На облачных провайдерах в десятки раз быстрее.

---

## Команды воспроизведения

> ⚠️ Историческая справка: скрипты ниже удалены из репозитория при зачистке одноразовых артефактов.
> Современный эквивалент: `POST /seed/examples` (admin) + curl-примеры из README (раздел «Выпускные варианты 2+5»).

```bash
# полный прогон (LLM-вызовы: ~10–20 мин каждый, суммарно ~1.5–2 часа)
cd filesdocs
python test_demo_flow.py auth
python test_demo_flow.py upload
python test_demo_flow.py review_one   # повторять до «all reviews already done»
python test_demo_flow.py batch
python test_demo_flow.py kb
python test_demo_flow.py lessons
python test_demo_flow.py econ
python arch_step.py standards && python arch_step.py urs && python arch_step.py srs \
  && python arch_step.py adr && python arch_step.py diagrams \
  && python arch_step.py coverage && python arch_step.py exports
python test_demo_flow.py report
```