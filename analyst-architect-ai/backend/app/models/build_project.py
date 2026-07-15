import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class BuildProject(Base):
    """
    Represents an application being designed/built with the help of
    Analyst-Architect-AI. Links a source document (TZ/BRD/URS/SRS)
    to task estimates and economic evaluation.
    """
    __tablename__ = "build_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="draft")  # draft|estimated|approved|in_progress|delivered

    task_estimates = relationship("TaskEstimate", back_populates="project", cascade="all, delete-orphan")
    economic_estimates = relationship("EconomicEstimate", back_populates="project", cascade="all, delete-orphan")
    economic_actuals = relationship("EconomicActual", back_populates="project", cascade="all, delete-orphan")
