import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    PROXYAPI_KEY: str = os.getenv("PROXYAPI_KEY", "")
    PROXYAPI_BASE_URL: str = os.getenv("PROXYAPI_BASE_URL", "https://api.proxyapi.ru/anthropic")
    PROXYAPI_MODEL: str = os.getenv("PROXYAPI_MODEL", "claude-sonnet-4-20250514")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_ROUTE: str = os.getenv("OPENROUTER_ROUTE", "openrouter/free")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "anthropic")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/analyst_guru.db")
    APP_SECRET_KEY: str = os.getenv("APP_SECRET_KEY", "dev_secret")
    MAX_DOCUMENT_LENGTH: int = int(os.getenv("MAX_DOCUMENT_LENGTH", "30000"))
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))
    # Таймаут одного LLM-вызова, секунды. Локальные модели на CPU (Ollama + qwen2.5:7b)
    # генерируют ответ 2–20 минут, поэтому дефолтный таймаут SDK (600 с в новых версиях
    # openai, 120 с — в этом коде) недостаточен: вызов падает в safe-fallback с
    # needs_review=true. Для локальных моделей поднимайте значение до 2400+ (см. .env).
    LLM_TIMEOUT: float = float(os.getenv("LLM_TIMEOUT", "600"))
    LLM_MODEL_ANTHROPIC: str = "claude-sonnet-4-20250514"
    LLM_MODEL_OPENAI: str = "gpt-4o"
    LLM_MODEL_OPENROUTER: str = "openrouter/auto"

    # ── Эпик A: локальный рендер диаграмм (Kroki) ─────────────────────────────
    DIAGRAM_RENDERER_URL: str = os.getenv("DIAGRAM_RENDERER_URL", "http://kroki:8000")
    DIAGRAM_RENDERER_TIMEOUT: float = float(os.getenv("DIAGRAM_RENDERER_TIMEOUT", "10"))

    # ── Эпик C: локальные LLM через Ollama ────────────────────────────────────
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434/v1")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:14b-instruct")
    # Если true — система не делает НИ ОДНОГО внешнего сетевого вызова (ни LLM, ни рендер диаграмм).
    # Отсутствие локального сервиса приводит к явной ошибке, а не к тихому уходу во внешний сервис.
    ENFORCE_LOCAL_ONLY: bool = os.getenv("ENFORCE_LOCAL_ONLY", "false").lower() == "true"

    # ── Фаза 3: реальные метрики использования → Economics ────────────────────────
    # Курс для перевода оценочной стоимости LLM (USD) в рубли в отчёте по экономике.
    # Не подтягивается автоматически из ЦБ — намеренно, чтобы не вводить внешнюю сетевую
    # зависимость в расчёт; значение можно переопределить в .env под текущий курс.
    LLM_COST_USD_TO_RUB: float = float(os.getenv("LLM_COST_USD_TO_RUB", "90.0"))


settings = Settings()
