import json
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Awaitable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from app.models.audit_run import AuditRun
from app.services.llm_client import get_last_call_meta


async def save_audit(
    db: AsyncSession,
    action: str,
    input_data: Any,
    output: Any,
    status: str = "ok",
    error: str | None = None,
    duration_ms: int = 0,
    provider_used: str | None = None,
    is_local_provider: bool = False,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    estimated_cost_usd: float | None = None,
) -> AuditRun:
    run = AuditRun(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        action=action,
        input=json.dumps(input_data, ensure_ascii=False, default=str)[:50_000],
        output=json.dumps(output, ensure_ascii=False, default=str)[:50_000],
        status=status,
        error=error,
        duration_ms=duration_ms,
        provider_used=provider_used,
        is_local_provider=is_local_provider,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=estimated_cost_usd,
    )
    db.add(run)
    await db.commit()
    return run


async def with_audit(
    db: AsyncSession,
    action: str,
    input_data: dict,
    func: Callable[[], Awaitable[Any]],
) -> Any:
    start = time.time()
    try:
        result = await func()
        duration = int((time.time() - start) * 1000)
        status = "needs_review" if getattr(result, "needs_review", False) else "ok"
        # Option2/Option5: причина ручной проверки должна быть видна в audit_runs.error.
        audit_error = None
        if status == "needs_review":
            audit_error = (
                getattr(result, "needs_review_reason", None)
                or getattr(result, "reason", None)
                or "NEEDS_REVIEW"
            )
        result_dict = result.model_dump() if hasattr(result, "model_dump") else result
        # Эпик C3: кто фактически обрабатывал запрос — записываем в аудит для доказуемости,
        # что документ не покидал локальный контур (провайдер ollama).
        # Фаза 3: реальный расход токенов/оценка стоимости — питает Economics вместо ручных цифр.
        meta = get_last_call_meta()
        await save_audit(
            db, action, input_data, result_dict, status=status, error=audit_error, duration_ms=duration,
            provider_used=meta.get("provider"), is_local_provider=bool(meta.get("is_local")),
            input_tokens=meta.get("input_tokens"), output_tokens=meta.get("output_tokens"),
            estimated_cost_usd=meta.get("estimated_cost_usd"),
        )
        return result
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        meta = get_last_call_meta()
        await save_audit(
            db, action, input_data, None, status="error", error=str(e), duration_ms=duration,
            provider_used=meta.get("provider"), is_local_provider=bool(meta.get("is_local")),
            input_tokens=meta.get("input_tokens"), output_tokens=meta.get("output_tokens"),
            estimated_cost_usd=meta.get("estimated_cost_usd"),
        )
        raise


async def get_audit_runs(
    db: AsyncSession,
    action: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    q = select(AuditRun).order_by(desc(AuditRun.created_at))
    filters = []
    if action:
        filters.append(AuditRun.action == action)
    if status:
        filters.append(AuditRun.status == status)
    if filters:
        q = q.where(and_(*filters))
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()
