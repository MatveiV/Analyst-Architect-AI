import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class DiagramArtifact(Base):
    __tablename__ = "diagram_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False)
    diagram_type: Mapped[str] = mapped_column(String(50), nullable=False)
    notation: Mapped[str] = mapped_column(String(20), nullable=False)  # plantuml | mermaid
    source_code: Mapped[str] = mapped_column(Text, nullable=False)

    document = relationship("Document", back_populates="diagram_artifacts")
