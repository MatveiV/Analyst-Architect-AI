import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ADRRecord(Base):
    __tablename__ = "adr_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False)
    adr_json: Mapped[str] = mapped_column(Text, nullable=False)

    standard_profile: Mapped[str | None] = mapped_column(String(30), nullable=True)

    document = relationship("Document", back_populates="adr_records")
