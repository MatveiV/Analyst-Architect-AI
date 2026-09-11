import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class RiskCatalogItem(Base):
    __tablename__ = "risk_catalog"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    project_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    probability: Mapped[int] = mapped_column(Integer, default=1)
    impact: Mapped[int] = mapped_column(Integer, default=1)
    category: Mapped[str] = mapped_column(String(50), default="tech")
    status: Mapped[str] = mapped_column(String(20), default="open")
    owner: Mapped[str | None] = mapped_column(String(200), nullable=True)
    mitigation: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="manual")
