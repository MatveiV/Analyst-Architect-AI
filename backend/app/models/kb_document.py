import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class KBDocument(Base):
    """Документ базы знаний команды (Вариант 5).

    Только для RAG-поиска: `snippets` ссылается на эту таблицу. Физически
    отделён от `spec_documents` (Вариант 2). `source_type`/`source_id`
    сохраняют provenance (urs/srs/adr/diagrams/lesson) для KB-автоиндексации
    сгенерированных артефактов.
    """
    __tablename__ = "kb_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    project_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    snippets = relationship("KBSnippet", back_populates="document", cascade="all, delete-orphan")

    @property
    def doc_type(self) -> str:
        """Обратная совместимость со старым контрактом единой таблицы `documents`.

        В KBDocument тип не хранится (он всегда KB-статья); свойство нужно для кода
        и тестов, которые раньше читали `Document.doc_type == "kb_article"`."""
        return "kb_article"
