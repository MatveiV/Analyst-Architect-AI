"""
Usage Economics — агрегация ФАКТИЧЕСКОГО расхода токенов/времени из audit_runs за период,
чтобы OPEX в экономическом модуле считался по реальным данным использования, а не по
вручную введённым цифрам (llm_cost_monthly по умолчанию = 3000 ₽/мес "на глаз").

Честная оговорка (см. также llm_pricing.py): estimated_cost_usd — оценка по приближённому
прайс-листу, не выгрузка из биллинга провайдера. Для Ollama (is_local_provider=true)
стоимость всегда 0 — это уже не оценка, а факт.
"""
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.audit_run import AuditRun
from app.schemas import UsageEconomicsOut, UsageByAction


async def get_actual_usage(db: AsyncSession, days: int = 30) -> UsageEconomicsOut:
    since = datetime.utcnow() - timedelta(days=days)

    totals_row = (await db.execute(
        select(
            func.count(AuditRun.id),
            func.coalesce(func.sum(AuditRun.input_tokens), 0),
            func.coalesce(func.sum(AuditRun.output_tokens), 0),
            func.coalesce(func.sum(AuditRun.estimated_cost_usd), 0.0),
            func.coalesce(func.avg(AuditRun.duration_ms), 0.0),
        ).where(AuditRun.created_at >= since)
    )).one()
    total_calls, total_in, total_out, total_cost_usd, avg_duration = totals_row

    by_action_rows = (await db.execute(
        select(
            AuditRun.action,
            func.count(AuditRun.id),
            func.coalesce(func.sum(AuditRun.input_tokens), 0),
            func.coalesce(func.sum(AuditRun.output_tokens), 0),
            func.coalesce(func.sum(AuditRun.estimated_cost_usd), 0.0),
            func.coalesce(func.avg(AuditRun.duration_ms), 0.0),
        )
        .where(AuditRun.created_at >= since)
        .group_by(AuditRun.action)
        .order_by(func.sum(AuditRun.estimated_cost_usd).desc())
    )).all()

    by_action = [
        UsageByAction(
            action=action, calls=calls,
            total_input_tokens=int(in_tok), total_output_tokens=int(out_tok),
            total_cost_usd=round(float(cost), 4), avg_duration_ms=round(float(dur), 1),
        )
        for action, calls, in_tok, out_tok, cost, dur in by_action_rows
    ]

    fx = settings.LLM_COST_USD_TO_RUB
    # Проекция на календарный месяц (30 дней) от фактического расхода за period_days
    scale = 30.0 / days if days > 0 else 0.0
    projected_usd = round(float(total_cost_usd) * scale, 4)

    return UsageEconomicsOut(
        period_days=days,
        total_calls=int(total_calls),
        total_input_tokens=int(total_in),
        total_output_tokens=int(total_out),
        total_cost_usd=round(float(total_cost_usd), 4),
        total_cost_rub=round(float(total_cost_usd) * fx, 2),
        projected_monthly_cost_usd=projected_usd,
        projected_monthly_cost_rub=round(projected_usd * fx, 2),
        avg_duration_ms=round(float(avg_duration), 1),
        by_action=by_action,
        fx_rate_used=fx,
    )
