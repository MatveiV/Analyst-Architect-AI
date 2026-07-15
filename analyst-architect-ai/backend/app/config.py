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
    LLM_MODEL_ANTHROPIC: str = "claude-sonnet-4-20250514"
    LLM_MODEL_OPENAI: str = "gpt-4o"
    LLM_MODEL_OPENROUTER: str = "openrouter/auto"


settings = Settings()
