import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class BatchReviewItem(Base):
    __tablename__ = "batch_review_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id: Mapped[str] = mapped_column(String(36), ForeignKey("batch_reviews.id"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True)
    review_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("reviews.id"), nullable=True)
    # pending | ok | error
    status: Mapped[str] = mapped_column(String(20), default="pending")
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    batch = relationship("BatchReview", back_populates="items")
