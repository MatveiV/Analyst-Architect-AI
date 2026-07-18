import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class DiagramVersion(Base):
    """История версий source_code диаграммы — тикет A3 (версионирование + rollback)."""

    __tablename__ = "diagram_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    diagram_artifact_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("diagram_artifacts.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    notation: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    change_note: Mapped[str | None] = mapped_column(String(300), nullable=True)

    diagram_artifact = relationship("DiagramArtifact", back_populates="versions")
