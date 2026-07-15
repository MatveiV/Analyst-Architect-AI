import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class EconomicEstimate(Base):
    """
    Economic evaluation (business case) for a build project.
    Formula is transparent — no black-box AI numbers, only AI-assisted
    inputs (hours) combined with user-editable rates.
    """
    __tablename__ = "economic_estimates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("build_projects.id"), nullable=False)

    # Inputs (editable rates, RUB by default)
    rate_backend: Mapped[float] = mapped_column(Float, default=2500.0)
    rate_frontend: Mapped[float] = mapped_column(Float, default=2200.0)
    rate_qa: Mapped[float] = mapped_column(Float, default=1800.0)
    rate_devops: Mapped[float] = mapped_column(Float, default=2800.0)
    rate_analyst: Mapped[float] = mapped_column(Float, default=2500.0)
    hosting_cost_monthly: Mapped[float] = mapped_column(Float, default=5000.0)
    llm_cost_monthly: Mapped[float] = mapped_column(Float, default=3000.0)
    support_hours_monthly: Mapped[float] = mapped_column(Float, default=8.0)
    time_saved_hours_monthly: Mapped[float] = mapped_column(Float, default=0.0)
    avg_employee_rate: Mapped[float] = mapped_column(Float, default=2500.0)

    # Outputs (computed, stored for history/audit)
    capex: Mapped[float] = mapped_column(Float, default=0.0)
    opex_monthly: Mapped[float] = mapped_column(Float, default=0.0)
    benefit_monthly: Mapped[float] = mapped_column(Float, default=0.0)
    payback_months: Mapped[float] = mapped_column(Float, default=0.0)
    roi_12m_pct: Mapped[float] = mapped_column(Float, default=0.0)

    project = relationship("BuildProject", back_populates="economic_estimates")
