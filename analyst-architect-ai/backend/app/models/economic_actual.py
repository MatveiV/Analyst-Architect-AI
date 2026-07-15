import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class EconomicActual(Base):
    """
    Actual (post-launch) economic figures for a build project, used to
    compare against the original EconomicEstimate (plan vs fact).
    """
    __tablename__ = "economic_actuals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("build_projects.id"), nullable=False)

    actual_capex: Mapped[float] = mapped_column(Float, default=0.0)
    actual_opex_monthly: Mapped[float] = mapped_column(Float, default=0.0)
    actual_benefit_monthly: Mapped[float] = mapped_column(Float, default=0.0)
    actual_time_saved_hours_monthly: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(Text, default="")

    project = relationship("BuildProject", back_populates="economic_actuals")
