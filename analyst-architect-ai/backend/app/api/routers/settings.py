"""
Settings router — управление настройками LLM-провайдеров.

GET  /settings/providers          — список всех сохранённых провайдеров (ключи маскируются)
POST /settings/providers          — сохранить / обновить настройки провайдера
POST /settings/providers/activate — переключить активного провайдера
GET  /settings/active             — вернуть активный провайдер для UI
POST /settings/test               — быстрый тест подключения (ping LLM)
"""
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.provider_settings import ProviderSettings
from app.schemas import ProviderSettingsIn, ProviderSettingsOut, ActiveProviderOut

router = APIRouter(prefix="/settings", tags=["settings"])

# Default models per provider
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
    "proxyapi": "claude-sonnet-4-20250514",
    "openrouter": "openrouter/auto",
}

DEFAULT_BASE_URLS = {
    "anthropic": "",
    "openai": "",
    "proxyapi": "https://api.proxyapi.ru/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}

DEFAULT_ROUTES = {
    "openrouter": "openrouter/free",
}

# ── helpers ───────────────────────────────────────────────────────────────────

def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return "*" * (len(key) - 4) + key[-4:]


def _apply_to_runtime(row: ProviderSettings) -> None:
    """Copy DB provider settings into in-memory app.config.settings."""
    from app.config import settings as app_settings
    app_settings.LLM_PROVIDER = row.provider
    if row.api_key:
        key_attr = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "proxyapi": "PROXYAPI_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }.get(row.provider)
        if key_attr:
            setattr(app_settings, key_attr, row.api_key)
    if row.model:
        if row.provider == "anthropic":
            app_settings.LLM_MODEL_ANTHROPIC = row.model
        elif row.provider in ("openai", "proxyapi"):
            app_settings.LLM_MODEL_OPENAI = row.model
        elif row.provider == "openrouter":
            app_settings.LLM_MODEL_OPENROUTER = row.model
    if row.temperature:
        app_settings.LLM_TEMPERATURE = float(row.temperature)
    if row.max_tokens:
        app_settings.LLM_MAX_TOKENS = int(row.max_tokens)
    if row.route and row.provider == "openrouter":
        app_settings.OPENROUTER_ROUTE = row.route

def _row_to_out(row: ProviderSettings) -> ProviderSettingsOut:
    return ProviderSettingsOut(
        id=row.id,
        updated_at=row.updated_at or datetime.utcnow(),
        provider=row.provider,
        api_key_masked=_mask_key(row.api_key or ""),
        model=row.model or DEFAULT_MODELS.get(row.provider, ""),
        base_url=row.base_url or DEFAULT_BASE_URLS.get(row.provider, ""),
        temperature=float(row.temperature or "0.2"),
        max_tokens=int(row.max_tokens or "4096"),
        route=row.route or DEFAULT_ROUTES.get(row.provider, ""),
        is_active=(row.is_active == "true"),
    )


async def _get_or_create(db: AsyncSession, provider: str) -> ProviderSettings:
    res = await db.execute(
        select(ProviderSettings).where(ProviderSettings.provider == provider)
    )
    row = res.scalar_one_or_none()
    if not row:
        row = ProviderSettings(
            id=str(uuid.uuid4()),
            provider=provider,
            model=DEFAULT_MODELS.get(provider, ""),
            base_url=DEFAULT_BASE_URLS.get(provider, ""),
            route=DEFAULT_ROUTES.get(provider, ""),
            is_active="false",
        )
        db.add(row)
        await db.flush()
    return row


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.get("/providers", response_model=List[ProviderSettingsOut])
async def list_providers(db: AsyncSession = Depends(get_db)):
    """Return all provider configs (api_key masked). Pre-create missing defaults."""
    for p in ("anthropic", "openai", "proxyapi", "openrouter"):
        await _get_or_create(db, p)
    await db.commit()

    res = await db.execute(
        select(ProviderSettings).order_by(ProviderSettings.provider)
    )
    return [_row_to_out(r) for r in res.scalars().all()]


@router.post("/providers", response_model=ProviderSettingsOut)
async def save_provider(body: ProviderSettingsIn, db: AsyncSession = Depends(get_db)):
    """Create or update a provider configuration."""
    row = await _get_or_create(db, body.provider)
    # Only update api_key if a non-empty value is sent (allows keeping existing key)
    if body.api_key:
        row.api_key = body.api_key.strip().encode("ascii", "ignore").decode("ascii")
    row.model = body.model or DEFAULT_MODELS.get(body.provider, "")
    row.base_url = body.base_url or DEFAULT_BASE_URLS.get(body.provider, "")
    row.temperature = str(body.temperature)
    row.max_tokens = str(body.max_tokens)
    row.route = body.route or DEFAULT_ROUTES.get(body.provider, "")
    row.updated_at = datetime.utcnow()

    # If this provider just got a key and no active provider exists, auto-activate
    was_auto_activated = False
    if body.api_key:
        active_res = await db.execute(
            select(ProviderSettings).where(ProviderSettings.is_active == "true")
        )
        if not active_res.scalar_one_or_none():
            res_all = await db.execute(select(ProviderSettings))
            for r in res_all.scalars().all():
                r.is_active = "true" if r.provider == body.provider else "false"
                r.updated_at = datetime.utcnow()
            was_auto_activated = True

    # Also update runtime config if this provider should be active
    if was_auto_activated or row.is_active == "true":
        _apply_to_runtime(row)

    await db.commit()
    await db.refresh(row)
    return _row_to_out(row)


@router.post("/providers/activate")
async def activate_provider(
    provider: str,
    db: AsyncSession = Depends(get_db),
):
    """Switch active provider. Deactivates all others."""
    if provider not in ("anthropic", "openai", "proxyapi", "openrouter"):
        raise HTTPException(400, f"Unknown provider: {provider}")

    # Ensure all rows exist
    for p in ("anthropic", "openai", "proxyapi", "openrouter"):
        await _get_or_create(db, p)

    # Deactivate all, then activate chosen
    res = await db.execute(select(ProviderSettings))
    for row in res.scalars().all():
        row.is_active = "true" if row.provider == provider else "false"
        row.updated_at = datetime.utcnow()

    await db.commit()

    # Apply to runtime settings
    res2 = await db.execute(
        select(ProviderSettings).where(ProviderSettings.provider == provider)
    )
    active_row = res2.scalar_one_or_none()
    if active_row:
        _apply_to_runtime(active_row)

    return {"activated": provider, "status": "ok"}


@router.get("/active", response_model=ActiveProviderOut)
async def get_active(db: AsyncSession = Depends(get_db)):
    """Return current active provider config (for UI status display)."""
    res = await db.execute(
        select(ProviderSettings).where(ProviderSettings.is_active == "true")
    )
    row = res.scalar_one_or_none()
    if not row:
        # Fallback: read from env settings
        from app.config import settings as s
        provider = s.LLM_PROVIDER
        model_map = {"anthropic": s.LLM_MODEL_ANTHROPIC, "openai": s.LLM_MODEL_OPENAI, "openrouter": s.LLM_MODEL_OPENROUTER}
        return ActiveProviderOut(
            provider=provider,
            model=model_map.get(provider, s.LLM_MODEL_OPENAI),
            base_url="",
            temperature=s.LLM_TEMPERATURE,
            max_tokens=s.LLM_MAX_TOKENS,
            route=s.OPENROUTER_ROUTE if provider == "openrouter" else "",
        )
    return ActiveProviderOut(
        provider=row.provider,
        model=row.model or DEFAULT_MODELS.get(row.provider, ""),
        base_url=row.base_url or "",
        temperature=float(row.temperature or "0.2"),
        max_tokens=int(row.max_tokens or "4096"),
        route=row.route or DEFAULT_ROUTES.get(row.provider, ""),
    )


@router.post("/test")
async def test_provider(provider: str, db: AsyncSession = Depends(get_db)):
    """Send a minimal ping to the provider to verify API key."""
    res = await db.execute(
        select(ProviderSettings).where(ProviderSettings.provider == provider)
    )
    row = res.scalar_one_or_none()
    if not row or not row.api_key:
        raise HTTPException(400, "No API key configured for this provider")

    try:
        if provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=row.api_key)
            resp = client.messages.create(
                model=row.model or DEFAULT_MODELS["anthropic"],
                max_tokens=10,
                messages=[{"role": "user", "content": "Say: OK"}],
            )
            return {"status": "ok", "response": resp.content[0].text[:50]}

        elif provider == "openai":
            from openai import OpenAI
            client = OpenAI(
                api_key=row.api_key,
                base_url=row.base_url or None,
            )
            resp = client.chat.completions.create(
                model=row.model or DEFAULT_MODELS["openai"],
                max_tokens=10,
                messages=[{"role": "user", "content": "Say: OK"}],
            )
            return {"status": "ok", "response": resp.choices[0].message.content[:50]}

        elif provider == "proxyapi":
            from openai import OpenAI
            client = OpenAI(
                api_key=row.api_key,
                base_url="https://api.proxyapi.ru/openai/v1",
            )
            resp = client.chat.completions.create(
                model=row.model or DEFAULT_MODELS["proxyapi"],
                max_tokens=10,
                messages=[{"role": "user", "content": "Say: OK"}],
            )
            return {"status": "ok", "response": resp.choices[0].message.content[:50]}

        elif provider == "openrouter":
            import httpx
            base = (row.base_url or DEFAULT_BASE_URLS["openrouter"]).rstrip("/")
            key = row.api_key.strip().encode("ascii", "ignore").decode("ascii") if row.api_key else ""
            model = row.model or "openrouter/auto"
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }
            async with httpx.AsyncClient() as hc:
                resp = await hc.post(
                    f"{base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": "OK"}],
                    },
                    timeout=15,
                )
                data = resp.json()
                if resp.status_code == 200 and "choices" in data:
                    return {"status": "ok", "response": data["choices"][0]["message"]["content"][:50]}
                err = data.get("error", {})
                if isinstance(err, dict):
                    err = err.get("message") or str(err)
                else:
                    err = str(err)
                hint = ""
                if resp.status_code == 403:
                    hint = " Проверьте ограничения ключа в дашборде OpenRouter (модели/IP/бюджет)."
                return {"status": "error", "error": f"HTTP {resp.status_code}: {err}.{hint}"}

    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
