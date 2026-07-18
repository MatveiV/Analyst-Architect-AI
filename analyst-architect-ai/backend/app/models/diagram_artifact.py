import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, LargeBinary
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

    # ── Эпик A2: локальный рендер ────────────────────────────────────────────
    render_svg: Mapped[str | None] = mapped_column(Text, nullable=True)
    render_png: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    rendered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # pending | ok | failed | external_fallback | blocked_external
    render_status: Mapped[str] = mapped_column(String(20), default="pending")
    render_error: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # ── Эпик B: мультистандартность ──────────────────────────────────────────
    standard_profile: Mapped[str | None] = mapped_column(String(30), nullable=True)

    document = relationship("Document", back_populates="diagram_artifacts")
    versions = relationship("DiagramVersion", back_populates="diagram_artifact",
                             cascade="all, delete-orphan", order_by="DiagramVersion.version_number")
