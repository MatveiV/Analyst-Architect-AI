import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AuditRun(Base):
    __tablename__ = "audit_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    input: Mapped[str] = mapped_column(Text, default="{}")
    output: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), default="ok")  # ok | error | needs_review
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    # Эпик C: доказуемость того, что запуск не покидал контур (используется на защите/в комплаенсе)
    provider_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_local_provider: Mapped[bool] = mapped_column(Boolean, default=False)

    # Фаза 3: реальный расход токенов/оценка стоимости — питает Economics вместо ручных цифр
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
