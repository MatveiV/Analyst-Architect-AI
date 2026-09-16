# Реализация Фаз 1, 2 и 3 — что сделано и как проверено

Код внесён прямо в клон `MatveiV/Analyst-Architect-AI` (папка `analyst-architect-ai/`), два
коммита в `main` (`git log`: `b85db9e` — Фазы 1+2, `ecde73b` — Фаза 3). В архиве — весь проект
целиком; `.bundle` содержит полную историю обоих коммитов и накатывается одной командой;
`.diff` — плоский патч от исходного состояния репозитория, если удобнее смотреть точечно.

**Текущий статус: 146/146 бэкенд-тестов проходят, frontend — 0 ошибок TypeScript, production
build собирается чисто.** Дополнительно выполнен полный **функциональный E2E-прогон** на
демо-документах (3 темы × 6 файлов из `filesdocs/demo-documents/`) с локальной моделью
`qwen2.5` через Ollama — рецензии, batch, KB/RAG, экономика, ArchStudio (URS/SRS/ADR/диаграммы),
экспорты, аудит. Отчёт: [docs/functional-test-report.md](docs/functional-test-report.md).

## Функциональный E2E-прогон (20.08.2026) — что нашлось и починилось

Прогон не только подтвердил работоспособность всех фаз, но и вскрыл **2 бага**, которые
в 146 pytest не ловились (тесты не делают реальных HTTP-экспортов с кириллицей и не
генерируют URS/SRS через живую модель):

### Баг 1: 500 на всех экспортах документов с кириллицей в названии
- `GET /documents/{id}/export/{markdown,docx,full-package/docx}` → 500,
  `UnicodeEncodeError 'latin-1'` в заголовке `Content-Disposition: attachment; filename={title}`.
- Фикс: `documents.py` — `filename*=UTF-8''{quote(doc.title)}` (RFC 5987), затронуты 3 эндпоинта.

### Баг 2: URS/SRS-генерация падала в safe-fallback на локальной модели
- Симптом: `generate-urs`/`generate-srs` возвращали `needs_review=true` с 0 элементами за
  ~30 минут «работы» — дефолтный таймаут openai SDK 600с, а qwen2.5 локально генерирует
  URS/SRS 19–20 минут.
- Фикс: новая настройка `LLM_TIMEOUT` (`config.py` + `.env` + `llm_client.py`,
  `client_kwargs["timeout"]=settings.LLM_TIMEOUT`), в `.env` установлено `2400`.
- После фикса: URS 20 требований, SRS 20 требований, оба `needs_review=false`.

### Ключевые результаты прогона

- **Рецензии**: 6/6 — все 3 «сырых» ТЗ честно помечены `needs_review=true`, confidence=low;
  полное CRM-ТЗ — `needs_review=false`.
- **Batch**: 6/6 обработано, 0 ошибок.
- **KB/RAG**: 2 вопроса, оба с источниками, confidence=high; автоиндексация артефактов — 10 статей.
- **Экономика**: декомпозиция 411.6 ч (high), CAPEX 967000 ₽, OPEX 25000 ₽/мес, ROI12м −131%,
  `llm_cost_source=actual_usage` (34 622 in / 13 465 out токенов из audit_runs).
- **ArchStudio**: URS/SRS по ГОСТ 34.602 (20+20 требований), ADR-001, 8 диаграмм
  (`external_fallback` — Kroki не поднят, ожидаемо), coverage `is_fully_covered=true`.
- **Аудит**: 22 LLM-запуска, provider=ollama, 0 ошибок; дифф рецензий и экспорты (markdown/docx/
  full-package/CSV/JSON) — 200.

Известные ограничения локального окружения (не баги): один воркер uvicorn (LLM-вызов 2–30 мин
блокирует остальные запросы — для параллельности нужен `--workers N` или очередь задач);
без Kroki диаграммы сохраняются кодом без картинки; на слабом железе LLM-вызовы медленные
(рецензия 2–8 мин, URS/SRS ~20 мин).

Команды воспроизведения и полные таблицы результатов — в [docs/functional-test-report.md](docs/functional-test-report.md).

## Фаза 3 — что реализовано (2 из 2 запрошенных пунктов)

### 1. Авто-индексация артефактов в KB
Механизм: сгенерированные URS/SRS/ADR/наборы диаграмм, а также уроки проектов (`ProjectLesson`
— и ручные через `POST /lessons`, и автоматически извлечённые из рецензии в
`review_to_catalog.py`) конвертируются в текст и индексируются как `kb_article` Document —
тот же путь, что и обычные KB-статьи, поэтому они сразу видны в `GET /kb/documents` и
участвуют в гибридном поиске `/kb/ask` без каких-либо доработок самого поиска.

Два осознанных ограничения, которые стоит знать:
- **Индексируются только уверенные результаты** (`needs_review=false`). Если генерация URS/SRS/
  диаграмм скатилась в safe-fallback (нет LLM-ключа, невалидный JSON и т.п.) — в KB ничего не
  попадает, иначе следующий цикл рецензии опирался бы на пустышку, выданную за прошлый опыт.
- **Модель `Decision` осталась неподключённой** — в коде это класс без единого эндпоинта
  создания (его функцию де-факто выполняет `ADRRecord`, который как раз и подключён к
  автоиндексации). Дописывать CRUD для мёртвой модели ради галочки не стал — это было бы
  имитацией работы, а не связыванием существующего функционала с RAG-поиском.

Технически: новый сервис `kb_autoindex.py` (текстовые сборщики `urs_to_text`/`srs_to_text`/
`adr_to_text`/`diagrams_to_text`/`lesson_to_text` + сама индексация через уже существующий
`rag_engine.index_document()`), провенанс — новые поля `documents.source_type`/`source_id`
(миграция `0006`), видны в `DocumentOut` и бейджем в UI KB.

### 2. Замыкание Economics ↔ реальные метрики
`llm_client.py` теперь захватывает `usage` из ответов Anthropic (`input_tokens`/`output_tokens`)
и OpenAI-совместимых провайдеров (`prompt_tokens`/`completion_tokens`, работает и для
OpenAI/ProxyAPI/OpenRouter, и для Ollama — для неё стоимость всегда $0, это факт, не оценка).
Стоимость считается по приближённому прайс-листу (`llm_pricing.py`, честно помечен как
ориентировочный) и пишется в `audit_runs.estimated_cost_usd` при каждом вызове.

- `GET /dashboard/actual-usage?days=30` — агрегация: сколько вызовов, токенов, $ и проекция
  на календарный месяц, в разбивке по `action` (generate_urs, generate_diagrams, ...).
- `POST /build-projects/{id}/economic-estimate?use_actual_llm_cost=true` — подменяет
  `llm_cost_monthly` из тела запроса на реальную проекцию, и это видно в ответе как
  `llm_cost_source: "actual_usage"` (иначе `"manual"`) — честно, не молча.
- Если реальных вызовов ещё не было (`total_calls == 0`), флаг `use_actual_llm_cost=true`
  **не обнуляет** введённое пользователем значение — остаётся `"manual"`, чтобы отсутствие
  данных не выдавалось за экономию.
- Frontend (`Economics.tsx`): карточка «Реальное использование LLM (30 дней)» с чекбоксом
  «использовать вместо ползунка», бейдж источника стоимости после сохранения оценки.

## Как применить

```bash
cd analyst-architect-ai-ваш-клон
git apply All_Phases_full.diff
# или: git fetch /path/to/phase3.bundle main:incoming && git merge incoming
# или просто распакуйте Analyst-Architect-AI_AllPhases.zip поверх своей копии

cd backend
pip install -r requirements.txt --break-system-packages   # faiss-cpu уже в списке
python -m alembic upgrade head    # применит 0002...0006
python -m pytest tests/ -v        # 146 тестов, ~50 секунд

cd ../frontend
npm install --legacy-peer-deps    # конфликт typescript@5 vs react-scripts — пред-существующий
npx tsc --noEmit                  # 0 ошибок
npm run build                     # production build проходит чисто
```

---

# Фазы 1 и 2 — детали (как в предыдущем проходе)

## Что было закрыто из списка «не сделано» (прошлый проход)

| Было | Стало |
|---|---|
| Редактор диаграмм — обычный `<textarea>` | Заменён на CodeMirror (`@uiw/react-codemirror`) — номера строк, парные скобки, тёмная тема; честно отмечено, что грамматики PlantUML/Mermaid для подсветки синтаксиса нет (её и не существует как готового пакета) |
| Тестов не было (A6/B7/C7) | 39 тестов на Эпики A/B/C — `test_epic_a_diagrams.py`, `test_epic_b_standards.py`, `test_epic_c_ollama.py` |
| Живой рендер через Kroki не проверялся | Проверен мок-тестами (успех/неудача); реальный контейнер поднять по-прежнему нельзя — в песочнице нет сети до Docker Hub, это ограничение среды, а не кода |
| E2E-тестов фронтенда не было | Осталось не сделано — см. ниже, честно, не стал изображать покрытие, которого нет |

Заодно нашёл и починил **критичный баг, не связанный с моей задачей**: `create_tables()`
мигрировал не тот SQLite-файл, что использовало приложение при кастомном `DATABASE_URL` — из-за
этого **весь тестовый набор был сломан ещё до Фазы 1** («no such table: users»). Без этого фикса
писать тесты было буквально некуда.

## Фаза 2 — что реализовано (3 из 3 пунктов исходного плана)

### 1. Пакетная рецензия (Batch Review) — флагманский пункт плана
- **Backend**: `BatchReview`/`BatchReviewItem` (миграция `0005`), `batch_review_service.py`
  (переиспользует существующий `ai_reviewer.run_ai_review()` — батч не вводит новую логику
  рецензирования, только оркестрирует её по списку из до 50 документов), роутер
  `batch_reviews.py` (`POST/GET /batch-reviews`, `GET .../{id}?needs_review=`, CSV-экспорт).
  Падение одного документа в пакете не блокирует остальные (`try/except` на уровне item).
- **Frontend**: `BatchReview.tsx` — форма добавления N ТЗ, список прошлых пакетов, сводка
  (всего/обработано/на проверку/ошибок), фильтр «только требует проверки», ссылки на
  документ/рецензию каждого пункта, экспорт CSV.
- **Тесты**: `test_phase2_batch_review.py`, 8 тестов — независимая обработка при ошибке,
  фильтрация, переиспользование `Document`/`Review` (не параллельное хранилище), CSV-экспорт.

### 2. Упрощённая трассируемость (Coverage)
Важная честная оговорка (она же в докстринге эндпоинта и в схеме ответа): это **счётчики
покрытия** документа требованиями/диаграммами/критериями приёмки, а **не** пооперационная
привязка «требование → конкретный элемент диаграммы» — такая точная трассируемость требует
отдельного LLM-этапа сопоставления, которого в этом объёме нет. То, что есть — быстрый обзор
пробелов («не хватает диаграмм», «нет критериев приёмки»).
- **Backend**: `GET /documents/{id}/coverage` — берёт последний URS (или SRS, если URS нет),
  считает требования/диаграммы/критерии приёмки/риски, возвращает флаги `has_*` и
  `is_fully_covered`.
- **Frontend**: вкладка «✅ Покрытие» в ArchStudio — три карточки-счётчика с ✅/⚠️, список
  недостающего.
- **Тесты**: `test_phase2_coverage.py`, 7 тестов — пустой документ, приоритет URS над SRS,
  fallback на SRS, 404, применение дефолтных стандартов документа в ответе.

### 3. Диффы версий рецензии
Тоже осознанно ограниченный, но честный скоуп: сравниваются **две рецензии одного документа**
(типичный сценарий — заказчик прислал обновлённое ТЗ, аналитик перезапустил рецензию и хочет
увидеть разницу), а не произвольные версии самого текста ТЗ построчно.
- **Backend**: `diff_service.py` (`difflib.unified_diff` для резюме + added/removed по
  множествам для рисков/критериев приёмки/пробелов), `GET /reviews/diff?from_id=&to_id=`.
- **Frontend**: режим «🔀 Сравнить рецензии» на странице Reviews — чекбоксы на карточках,
  автоматическая сортировка старая→новая по `created_at` (не по порядку клика), панель диффа
  с цветным unified-diff резюме и списками added/removed.
- **Тесты**: `test_phase2_review_diff.py`, 5 тестов, включая unit-тест самой функции диффа
  без похода в БД (проверяет confidence/needs_review/added/removed по чистым данным).

## Что осталось не сделано (честно)

- **E2E-тесты фронтенда** (Playwright/Cypress) — по-прежнему нет, только typecheck + build +
  backend-интеграционные тесты через `httpx.AsyncClient`.
- **Batch Review — синхронная обработка**: `POST /batch-reviews` обрабатывает все документы
  пакета внутри одного HTTP-запроса (до 50 штук), без очереди/background task. Для полноценного
  прод-масштабирования стоит вынести в Celery/APScheduler — в этом объёме сознательно не делал,
  чтобы не вводить лишнюю инфраструктуру ради курсового/портфолио-проекта.
- **Coverage — не пооперационная трассируемость**: см. оговорку выше, это счётчики, не точная
  привязка.
- **Diff — только между рецензиями, не между сырыми версиями текста ТЗ**: если понадобится
  «что изменилось в самом тексте ТЗ, который прислал заказчик» (а не в рецензии на него) —
  это отдельная фича (нужно хранить версии `Document.text`, сейчас `Document` не версионируется).
- **Живой рендер через реальный Kroki**: как и в Фазе 1, ограничение среды (нет сети до Docker
  Hub в песочнице), не кода.

## Как применить

```bash
cd analyst-architect-ai-ваш-клон
git apply Phase1_Phase2_full.diff
# или распакуйте Analyst-Architect-AI_Phase1_Phase2.zip поверх своей копии

cd backend
pip install -r requirements.txt --break-system-packages   # добавился faiss-cpu
python -m alembic upgrade head    # применит 0002...0005
python -m pytest tests/ -v        # 122 теста, ~45 секунд

cd ../frontend
npm install --legacy-peer-deps    # конфликт typescript@5 vs react-scripts — пред-существующий
npx tsc --noEmit                  # 0 ошибок
npm run build                     # production build проходит чисто
```

---

# Фаза 1 (Эпики A, B, C) — детали

(Установка та же, что указана выше — единый патч/архив покрывает Фазы 1 и 2 вместе;
цифры "102 теста" ниже относятся к состоянию на конец Фазы 1, после Фазы 2 их 122 — см. начало файла.)

При обычном запуске (`start.py` / `docker-compose up`) миграции применяются автоматически —
`create_tables()` в `app/database.py` сам вызывает `alembic upgrade head`.

## Что реально реализовано и проверено

### Backend — сквозные проверки живым сервером (curl) + 39 новых тестов

| Тикет | Как проверено |
|---|---|
| A1/A2 | `render_diagram()` — мок-тесты успешного/неудачного Kroki-ответа; живой прогон честно даёт `external_fallback`/`blocked_external` при недоступности |
| A2 | Миграция 0002 применяется на чистой БД (`render_svg/render_png/render_status/render_error`) |
| A3 | Интеграционный тест: `PUT /diagrams/{id}` → версия сохранена → `GET .../versions` → `POST .../rollback/{n}` возвращает оригинал и НЕ теряет историю (v3 после rollback, не перезапись v1) |
| A4 | `export_document_docx()` с диаграммами: успешный рендер → картинка встроена (проверено реальным валидным PNG); неудачный рендер → код диаграммы + честная причина в тексте DOCX (проверено через `python-docx` парсинг результата) |
| A5 | FAISS-индекс для `Snippet` (отдельный от индекса `memory_service`) поднимается при старте, `rebuild_snippet_faiss_index()` |
| B1/B2 | `GET /standards`, `GET /standards?family=` — тесты на состав сида (9 стандартов) |
| B3 | Unit-тесты `_sections_for()`/`_urs_system_for_standard()` — структура промпта реально меняется по ГОСТ 34 vs ISO 29148; fallback-путь сохраняет `standard_profile` |
| B5 | `PATCH /documents/{id}/standards` round-trip; `generate-urs` без явного `?standard=` берёт дефолт документа; явный `?standard=` имеет приоритет над дефолтом (оба варианта — отдельные тесты) |
| B2 | `RequirementsDocument` персистентность: `GET .../requirements-documents` (история) и `GET /requirements-documents/{id}` (плоский путь) — оба протестированы, включая 404 |
| C1/C3 | Мок-тесты: `_cfg_from_env()` для ollama даёt `is_local=True`, `api_key="ollama"`; `call_llm()` не требует ключ для ollama, но требует для облачных; `_last_call_meta` фиксируется ДО вызова (важно для аудита даже при падении) |
| C1 | `_call_openai_compat(force_json=True)` реально передаёт `extra_body={"format": "json"}` (проверено мок-перехватом kwargs); при `force_json=False` — не передаёт |
| C1 | `_call_ollama()` retry: пустой первый ответ → ровно один повторный вызов с явной инструкцией "ТОЛЬКО валидный JSON"; если и второй пуст — отдаёт пустую строку (вызывающая сторона уходит в safe_fallback) |
| C3 | `with_audit()` пишет `provider_used`/`is_local_provider` и при успехе, и при исключении |
| C4 | `POST /settings/providers` + `POST /settings/test` + `GET /settings/providers/ollama/models` — все три дают аккуратную ошибку (не 500) при недоступном сервисе; доступны любому аутентифицированному пользователю (require_analyst) |
| C5 | Прямой мок-тест: недоступный Kroki + `ENFORCE_LOCAL_ONLY=true` → `blocked_external`; `=false` → `external_fallback` — оба пути проверены в одном тесте |
| C6 | `GET /dashboard/stats-by-provider` — агрегация по уникальным provider-маркерам (чтобы не зависеть от состояния общей тестовой БД), проверены `needs_review_rate_pct`/`is_local` |

Пре-существующий баг (не Фаза 1, но чинил, иначе тесты негде было писать): `RiskCatalog` vs
`RiskCatalogItem` в `seed.py`, и хардкод пути БД в `create_tables()` (см. выше).

### Frontend — typecheck + production build проходят чисто (0 ошибок)

- **`DiagramViewer.tsx`** — переписан:
  - предпочитает локальный SVG-рендер с бэкенда (`render_svg`, если `render_status === "ok"`),
    иначе — прежний fallback на публичные plantuml.com/mermaid.live;
  - бейдж статуса рендера (🔒 локально / 🌐 внешний сервис / ⛔ заблокировано / ⚠️ ошибка);
  - бейдж применённого стандарта диаграммы;
  - **редактор кода** (textarea) + «Применить и перерендерить» → `PUT /diagrams/{id}`;
  - **история версий** — раскрывающаяся панель, кнопка «Откатить» на каждую версию.
- **`Settings.tsx`** — добавлена карточка провайдера Ollama:
  - без поля API-ключа (вместо него — пояснение, что ключ не нужен и трафик не покидает сеть);
  - бейдж «🔒 Локальный контур» у карточки и у активного провайдера в статус-баре;
  - выпадающий список моделей подтягивается живьём через `GET /settings/providers/ollama/models`
    (а не угадывается руками), с понятными сообщениями при недоступности Ollama;
  - подсказка про `host.docker.internal` / `172.17.0.1` для случая «Ollama уже на хосте».
- **`ArchStudio.tsx`** — добавлен блок выбора стандарта:
  - два independent-селектора (стандарт требований / стандарт диаграмм), заполняются через
    `GET /standards?family=...`;
  - кнопка «Сделать дефолтом документа» → `PATCH /documents/{id}/standards`;
  - предупреждение при выборе приближённых стандартов (ГОСТ 19.701 / IEC 61082);
  - бейдж применённого стандарта на результатах URS/SRS;
  - кнопка «📦 Полный пакет» → `GET .../export/full-package/docx` (рецензия + диаграммы картинками).
- Обновлён `api/index.ts` — все новые эндпоинты (standards, diagram versioning, ollama models,
  stats-by-provider, full-package export, document standards) типизированы и подключены.

## Что НЕ сделано в этом проходе

- **Живой рендер через реальный Kroki-контейнер**: в песочнице нет сети до Docker Hub, поэтому
  ветка «успешный локальный рендер» (`render_status="ok"`) проверена мок-тестами и по коду, но не
  вживую на настоящем Kroki. Ветки failure/fallback/blocked проверены вживую.
- **B4 на реальном LLM**: параметризация диаграмм по стандарту (включая `viewpoints` для
  ISO/IEC/IEEE 42010) проверена на уровне промпта и safe-fallback пути — качество генерации на
  живом Claude/GPT стоит перепроверить отдельно.
- **CodeMirror/Monaco для редактора диаграмм**: сейчас простой `<textarea>` с моноширинным
  шрифтом — работает и покрыт функционалом (правка → рендер → версия), но без подсветки
  синтаксиса PlantUML/Mermaid. Можно добавить как отдельное улучшение UX.
- **E2E-тесты фронтенда** (Playwright/Cypress) — не писал, только typecheck + build + ручная
  сверка JSX-логики. Backend покрыт интеграционными тестами через `httpx.AsyncClient`, фронтенд —
  только статической проверкой типов.

## Структура изменений по эпикам

- **Эпик A**: `diagram_engine.py`, `diagram_artifact.py` + `diagram_version.py`, миграция `0002`,
  роутер `diagrams.py`, `export_service.py`, `main.py` (FAISS lifespan), `rag_engine.py`,
  `tests/test_epic_a_diagrams.py`, `DiagramViewer.tsx`.
- **Эпик B**: `documentation_standard.py`, `requirements_document.py`, миграция `0003` +
  `standards_seed.py`, роутер `standards.py`, `doc_generator.py`, `diagram_engine.py`,
  `documents.py`, `tests/test_epic_b_standards.py`, `ArchStudio.tsx` (селекторы стандарта).
- **Эпик C**: `config.py`, `llm_client.py`, `provider_settings.py` + `audit_run.py`, миграция
  `0004`, `audit_service.py`, `settings.py` (роутер), `dashboard.py`, `docker-compose.yml`,
  `.env.example`, `tests/test_epic_c_ollama.py`, `Settings.tsx` (карточка Ollama).

