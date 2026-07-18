import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class BatchReview(Base):
    """
    Фаза 2, тикет «Пакетная рецензия» — загрузка N ТЗ одним запросом, обработка очередью,
    сводная таблица результатов с фильтром needs_review. Прямое развитие варианта 2
    (ИИ-рецензент ТЗ) — то же самое ядро (ai_reviewer), но по многим документам сразу.
    """

    __tablename__ = "batch_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # pending | processing | completed | completed_with_errors
    status: Mapped[str] = mapped_column(String(30), default="pending")
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    completed_count: Mapped[int] = mapped_column(Integer, default=0)
    needs_review_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    items = relationship("BatchReviewItem", back_populates="batch", cascade="all, delete-orphan",
                          order_by="BatchReviewItem.order_index")
