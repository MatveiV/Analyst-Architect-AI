import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class KBSnippet(Base):
    """Фрагмент KB-документа, индексируется RAG-движком (раньше назывался Snippet).

    После физического разделения `documents` → `spec_documents`/`kb_documents`
    снипеты остались только для KB (для спецификаций они не нужны — там
    целиком рецензируется `spec_documents.text`).
    """
    __tablename__ = "kb_snippets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("kb_documents.id"), nullable=False)
    snippet_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    document = relationship("KBDocument", back_populates="snippets")
