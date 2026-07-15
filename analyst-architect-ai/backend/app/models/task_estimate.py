import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class TaskEstimate(Base):
    """
    Stores the full AI task-decomposition result for a build project
    (one row per estimation run — history is preserved).
    """
    __tablename__ = "task_estimates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("build_projects.id"), nullable=False)
    tasks_json: Mapped[str] = mapped_column(Text, nullable=False)   # full AI JSON: tasks[], total_hours_by_role
    total_hours: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[str] = mapped_column(String(20), default="medium")
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)

    project = relationship("BuildProject", back_populates="task_estimates")
