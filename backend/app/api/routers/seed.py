"""
Seed router — быстрая загрузка демо-данных одним запросом
(перенос удобной практики из MatveiV/Analyst-Guru).
"""
import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.document import Document
from app.models.risk_catalog import RiskCatalogItem as RiskCatalog
from app.models.project_lesson import ProjectLesson
from app.models.memory_item import MemoryItem
from app.models.decision import Decision
from app.services import rag_engine

router = APIRouter(prefix="/seed", tags=["seed"])

TESTS_DATA_DIR = Path(__file__).resolve().parents[4] / "tests_data"


@router.post("/documents")
async def seed_documents(db: AsyncSession = Depends(get_db)):
    """Load the example specs from tests_data/specs/specs.jsonl."""
    specs_path = TESTS_DATA_DIR / "specs" / "specs.jsonl"
    if not specs_path.exists():
        return {"loaded": 0, "error": f"File not found: {specs_path}"}

    loaded = 0
    with open(specs_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            spec = json.loads(line)
            doc = Document(
                id=str(uuid.uuid4()),
                created_at=datetime.utcnow(),
                title=spec["title"],
                text=spec["text"],
                doc_type=spec.get("doc_type", "tz"),
            )
            db.add(doc)
            loaded += 1
    await db.commit()
    return {"loaded": loaded}


@router.post("/kb-documents")
async def seed_kb_documents(db: AsyncSession = Depends(get_db)):
    """Load the example knowledge-base articles from tests_data/kb_documents.jsonl."""
    kb_path = TESTS_DATA_DIR / "kb_documents.jsonl"
    if not kb_path.exists():
        return {"loaded": 0, "error": f"File not found: {kb_path}"}

    loaded = 0
    with open(kb_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            doc = Document(
                id=str(uuid.uuid4()),
                created_at=datetime.utcnow(),
                title=item["title"],
                text=item["text"],
                doc_type="kb_article",
            )
            db.add(doc)
            await db.flush()
            await rag_engine.index_document(db, doc.id, item["text"])
            loaded += 1
    await db.commit()
    return {"loaded": loaded}


@router.post("/examples")
async def seed_all_examples(db: AsyncSession = Depends(get_db)):
    """Seed comprehensive examples for all business processes."""
    results = {}

    # 1. Documents (if not already seeded)
    existing = (await db.execute(select(Document).limit(1))).scalar_one_or_none()
    if not existing:
        results["documents"] = await seed_documents(db)
    else:
        results["documents"] = {"loaded": 0, "skipped": "already seeded"}

    # 2. KB documents
    existing_kb = (await db.execute(
        select(Document).where(Document.doc_type == "kb_article").limit(1)
    )).scalar_one_or_none()
    if not existing_kb:
        results["kb_documents"] = await seed_kb_documents(db)
    else:
        results["kb_documents"] = {"loaded": 0, "skipped": "already seeded"}

    # 3. Risk Catalog examples
    existing_risk = (await db.execute(select(RiskCatalog).limit(1))).scalar_one_or_none()
    if not existing_risk:
        examples = [
            RiskCatalog(
                id=str(uuid.uuid4()), created_at=datetime.utcnow(),
                title="Отсутствие тестовой среды",
                description="У заказчика нет выделенной тестовой среды, что замедляет отладку",
                probability=4, impact=4, category="infrastructure", status="open",
                mitigation="Предложить развертывание тестового стенда в контейнерах", source="seed",
            ),
            RiskCatalog(
                id=str(uuid.uuid4()), created_at=datetime.utcnow(),
                title="Неопределённость в требованиях",
                description="Ключевые требования не формализованы, возможны частые изменения",
                probability=5, impact=3, category="requirements", status="open",
                mitigation="Закрепить требования в SRS через протокол согласования", source="seed",
            ),
            RiskCatalog(
                id=str(uuid.uuid4()), created_at=datetime.utcnow(),
                title="Зависимость от внешнего API",
                description="Интеграция с внешним сервисом, SLA которого < 99%",
                probability=3, impact=5, category="integration", status="mitigated",
                mitigation="Реализовать кэширование и fallback-механизм при недоступности API", source="seed",
            ),
        ]
        for r in examples:
            db.add(r)
        await db.commit()
        results["risk_catalog"] = {"loaded": len(examples)}
    else:
        results["risk_catalog"] = {"skipped": "already seeded"}

    # 4. Project Lessons examples
    existing_lesson = (await db.execute(select(ProjectLesson).limit(1))).scalar_one_or_none()
    if not existing_lesson:
        examples = [
            ProjectLesson(
                id=str(uuid.uuid4()), created_at=datetime.utcnow(),
                title="Мониторинг с первого дня",
                description="На проекте N настроили мониторинг только после второго инцидента в проде",
                category="devops", impact_type="negative",
                root_cause="Мониторинг не был заложен в бюджет на старте",
                recommendation="Закладывать настройку мониторинга в спринт 0 каждого проекта", source="seed",
            ),
            ProjectLesson(
                id=str(uuid.uuid4()), created_at=datetime.utcnow(),
                title="Документирование ADR",
                description="Команда тратила часы на обсуждение уже принятых архитектурных решений",
                category="architecture", impact_type="negative",
                root_cause="Решения принимались устно без фиксации в ADR",
                recommendation="Ввести практику ADR с первого архитектурного решения", source="seed",
            ),
            ProjectLesson(
                id=str(uuid.uuid4()), created_at=datetime.utcnow(),
                title="Автоматическое тестирование сократило баги на 60%",
                description="Внедрение автотестов на регресс сократило количество багов в проде на 60%",
                category="qa", impact_type="positive",
                root_cause="Ранее тестирование было только ручным",
                recommendation="Довести покрытие автотестами до 70%+ до перехода в продуктив", source="seed",
            ),
        ]
        for l in examples:
            db.add(l)
        await db.commit()
        results["project_lessons"] = {"loaded": len(examples)}
    else:
        results["project_lessons"] = {"skipped": "already seeded"}

    # 5. Memory items (project memory examples)
    existing_mem = (await db.execute(select(MemoryItem).limit(1))).scalar_one_or_none()
    if not existing_mem:
        examples = [
            MemoryItem(
                id=str(uuid.uuid4()), created_at=datetime.utcnow(),
                memory_type="risk",
                content="Интеграция с внешним платёжным шлюзом требует PCI-DSS сертификации",
                tags="integration,security,payment",
                project_name="CRM System",
            ),
            MemoryItem(
                id=str(uuid.uuid4()), created_at=datetime.utcnow(),
                memory_type="decision",
                content="Используем PostgreSQL 16, так как нужна поддержка JSONB для гибкой схемы данных",
                tags="database,architecture",
                project_name="CRM System",
            ),
            MemoryItem(
                id=str(uuid.uuid4()), created_at=datetime.utcnow(),
                memory_type="lesson",
                content="Выносить тяжёлые вычисления в фоновые задачи через Celery — иначе API timeout",
                tags="performance,architecture",
                project_name="Analytics Dashboard",
            ),
        ]
        for m in examples:
            db.add(m)
        await db.commit()
        results["memory_items"] = {"loaded": len(examples)}
    else:
        results["memory_items"] = {"skipped": "already seeded"}

    return results
