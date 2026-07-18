from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class DocumentationStandard(Base):
    """Справочник стандартов оформления требований/документации и диаграмм — тикет B1.

    family: "requirements" (структура ТЗ/URS/SRS) | "diagram" (нотация диаграмм/архитектуры)
    """

    __tablename__ = "documentation_standards"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)  # напр. "GOST_34", "C4_MODEL"
    name_ru: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    family: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
