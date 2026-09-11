import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class RequirementsDocument(Base):
    """Персистентное хранилище сгенерированных URS/SRS — тикет B2.

    Раньше URS/SRS возвращались напрямую из doc_generator.py и были видны только
    через audit_runs.output. Теперь у них есть собственная история и привязка
    к применённому стандарту (standard_profile), что позволяет сравнивать, например,
    URS по ГОСТ 34 и URS по ISO/IEC/IEEE 29148 для одного и того же документа.
    """

    __tablename__ = "requirements_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False)
    doc_kind: Mapped[str] = mapped_column(String(10), nullable=False)  # "urs" | "srs"
    standard_profile: Mapped[str] = mapped_column(String(30), nullable=False)
    content_json: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), default="medium")
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="requirements_documents")
