"""
Идемпотентный сид справочника стандартов — используется как fallback, если приложение
стартовало через Base.metadata.create_all() (без Alembic). Список синхронизирован с
alembic/versions/0003_standards_profile.py — если меняете один, обновите и другой.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.documentation_standard import DocumentationStandard

SEED_STANDARDS = [
    dict(id="IEEE_830", name_ru="IEEE 830-1998 (SRS)", name_en="IEEE 830-1998 (SRS)",
         family="requirements",
         description="Классическая структура Software Requirements Specification."),
    dict(id="ISO_IEC_IEEE_29148", name_ru="ISO/IEC/IEEE 29148 (Requirements Engineering)",
         name_en="ISO/IEC/IEEE 29148 (Requirements Engineering)", family="requirements",
         description="Актуальный международный стандарт, преемник IEEE 830. Используется по умолчанию."),
    dict(id="GOST_19", name_ru="ГОСТ 19.201-78 (ТЗ на программу, ЕСПД)",
         name_en="GOST 19.201-78 (Software TOR, ESPD)", family="requirements",
         description="Российский стандарт ЕСПД для технического задания на программу."),
    dict(id="GOST_34", name_ru="ГОСТ 34.602-2020 (ТЗ на автоматизированную систему)",
         name_en="GOST 34.602-2020 (Automated system TOR)", family="requirements",
         description="Часто требуется банками и государственными заказчиками РФ."),
    dict(id="C4_MODEL", name_ru="C4-модель (Simon Brown)", name_en="C4 model (Simon Brown)",
         family="diagram",
         description="Context/Container/Component/Code — используется по умолчанию в проекте."),
    dict(id="UML_ISO_19505", name_ru="UML по ISO/IEC 19505", name_en="UML per ISO/IEC 19505",
         family="diagram",
         description="Use Case, Sequence, Class, State, Activity диаграммы."),
    dict(id="ISO_IEC_IEEE_42010", name_ru="ISO/IEC/IEEE 42010 (Architecture description)",
         name_en="ISO/IEC/IEEE 42010 (Architecture description)", family="diagram",
         description="Комплект видов архитектуры (viewpoints), привязанных к интересам стейкхолдеров."),
    dict(id="GOST_19_701", name_ru="ГОСТ 19.701-90 (Схемы алгоритмов, программ, данных)",
         name_en="GOST 19.701-90 (Program/data flowcharts)", family="diagram",
         description="Приближённая генерация: needs_review=true по умолчанию, требуется ручная сверка обозначений."),
    dict(id="IEC_61082", name_ru="IEC 61082 (Оформление технической документации)",
         name_en="IEC 61082 (Preparation of technical documents)", family="diagram",
         description="В первую очередь про электротехническую документацию; для чисто ПО-систем "
                     "применим ограниченно — актуален для проектов на стыке с АСУ ТП/встраиваемыми "
                     "системами. needs_review=true по умолчанию."),
]


async def seed_default_standards(db: AsyncSession) -> None:
    existing = (await db.execute(select(DocumentationStandard.id))).scalars().all()
    existing_ids = set(existing)
    for row in SEED_STANDARDS:
        if row["id"] not in existing_ids:
            db.add(DocumentationStandard(**row, is_active=True))
    await db.commit()
