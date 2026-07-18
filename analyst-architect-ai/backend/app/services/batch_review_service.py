"""
Batch Review service — Фаза 2: пакетная рецензия N технических заданий за один запрос.
Переиспользует существующее ядро ai_reviewer.run_ai_review() и модель Review — батч
не вводит новую логику рецензирования, только оркестрирует существующую по списку документов.
"""
import json
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.review import Review
from app.models.batch_review import BatchReview
from app.models.batch_review_item import BatchReviewItem
from app.schemas import BatchReviewCreate
from app.services import ai_reviewer
from app.services.audit_service import with_audit


async def create_and_process_batch(db: AsyncSession, body: BatchReviewCreate) -> BatchReview:
    batch = BatchReview(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        title=body.title,
        status="processing",
        total_count=len(body.items),
    )
    db.add(batch)
    await db.flush()  # получить batch.id для FK у items

    needs_review_count = 0
    error_count = 0

    for idx, item in enumerate(body.items):
        doc = Document(
            id=str(uuid.uuid4()),
            created_at=datetime.utcnow(),
            title=item.title,
            text=item.text,
            doc_type="tz",
        )
        db.add(doc)
        await db.flush()

        batch_item = BatchReviewItem(
            id=str(uuid.uuid4()),
            batch_id=batch.id,
            order_index=idx,
            title=item.title,
            document_id=doc.id,
            status="pending",
            created_at=datetime.utcnow(),
        )
        db.add(batch_item)

        try:
            async def _run(doc_text=doc.text, mode=body.reasoning_mode):
                return await ai_reviewer.run_ai_review(doc_text, reasoning_mode=mode)

            schema = await with_audit(
                db, "batch_review_item",
                {"batch_id": batch.id, "document_id": doc.id, "title": item.title},
                _run,
            )

            review = Review(
                id=str(uuid.uuid4()),
                created_at=datetime.utcnow(),
                document_id=doc.id,
                review_json=json.dumps(schema.model_dump(), ensure_ascii=False),
                needs_review=schema.needs_review,
                confidence=schema.confidence,
                error=None,
            )
            db.add(review)
            await db.flush()

            batch_item.review_id = review.id
            batch_item.status = "ok"
            batch_item.needs_review = schema.needs_review
            batch_item.confidence = schema.confidence
            if schema.needs_review:
                needs_review_count += 1
        except Exception as e:
            # Эпик "честная ручная проверка": сбой одного документа не должен ронять весь батч —
            # остальные ТЗ в пакете обрабатываются независимо.
            batch_item.status = "error"
            batch_item.error = str(e)[:2000]
            batch_item.needs_review = True
            error_count += 1

        batch.completed_count += 1

    batch.needs_review_count = needs_review_count
    batch.error_count = error_count
    batch.status = "completed_with_errors" if error_count else "completed"

    await db.commit()
    await db.refresh(batch)
    return batch
