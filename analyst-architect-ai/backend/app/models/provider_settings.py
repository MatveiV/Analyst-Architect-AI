import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ProviderSettings(Base):
    """
    Persistent storage for LLM provider configuration.
    One row per provider (anthropic | openai | proxyapi).
    """
    __tablename__ = "provider_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    provider: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # anthropic|openai|proxyapi
    api_key: Mapped[str] = mapped_column(Text, default="")          # stored as-is (no encryption in dev)
    model: Mapped[str] = mapped_column(String(100), default="")     # e.g. claude-sonnet-4-20250514
    base_url: Mapped[str] = mapped_column(Text, default="")         # for ProxyAPI / custom endpoints
    temperature: Mapped[str] = mapped_column(String(10), default="0.2")
    max_tokens: Mapped[str] = mapped_column(String(10), default="4096")
    route: Mapped[str] = mapped_column(String(50), default="openrouter/free")  # openrouter/free | openrouter/fusion | openrouter/pareto-code
    is_active: Mapped[str] = mapped_column(String(5), default="false")  # "true"|"false" as string
