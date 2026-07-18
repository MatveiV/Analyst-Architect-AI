import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), default="tz")
    project_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # ── Эпик B: дефолтные стандарты документа (можно переопределять на уровне запроса) ──
    default_requirements_standard: Mapped[str | None] = mapped_column(String(30), nullable=True)
    default_diagram_standard: Mapped[str | None] = mapped_column(String(30), nullable=True)

    snippets = relationship("Snippet", back_populates="document", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="document", cascade="all, delete-orphan")
    architecture_reviews = relationship("ArchitectureReview", back_populates="document", cascade="all, delete-orphan")
    api_specs = relationship("APISpec", back_populates="document", cascade="all, delete-orphan")
    adr_records = relationship("ADRRecord", back_populates="document", cascade="all, delete-orphan")
    diagram_artifacts = relationship("DiagramArtifact", back_populates="document", cascade="all, delete-orphan")
    requirements_documents = relationship("RequirementsDocument", back_populates="document", cascade="all, delete-orphan")
