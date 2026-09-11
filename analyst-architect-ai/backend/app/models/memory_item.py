import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Float, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class MemoryItem(Base):
    __tablename__ = "memory_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False)  # semantic|episodic|decision|risk|requirement
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    project_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
