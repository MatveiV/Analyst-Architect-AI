"""
Settings router — управление настройками LLM-провайдеров.

GET  /settings/providers          — список всех сохранённых провайдеров (ключи маскируются)
POST /settings/providers          — сохранить / обновить настройки провайдера
POST /settings/providers/activate — переключить активного провайдера
GET  /settings/active             — вернуть активный провайдер для UI
POST /settings/test               — тест подключения по конфигурации из формы (с fallback на DB/env)
POST /settings/detect             — определить провайдера по API-ключу / Base URL

Доступ: любой аутентифицированный пользователь (admin | analyst | architect).
"""
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import httpx
from app.config import settings as app_settings_module
from app.database import get_db
from app.models.provider_settings import ProviderSettings
from app.schemas import (
    ProviderSettingsIn, ProviderSettingsOut, ActiveProviderOut,
    OllamaModelOut, ProviderTestIn, ProviderDetectIn, ProviderDetectOut,
)

router = APIRouter(prefix="/settings", tags=["settings"])

# Default models per provider
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
    "proxyapi": "claude-sonnet-4-20250514",
    "openrouter": "openrouter/auto",
    "ollama": "qwen2.5:14b-instruct",
}

ALL_PROVIDERS = ("anthropic", "openai", "proxyapi", "openrouter", "ollama")
# Провайдеры, работающие полностью локально — данные не покидают контур (Эпик C).
LOCAL_PROVIDERS = ("ollama",)

DEFAULT_BASE_URLS = {
    "anthropic": "",
    "openai": "",
    "proxyapi": "https://api.proxyapi.ru/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": app_settings_module.OLLAMA_BASE_URL,
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
        elif row.provider == "ollama":
            app_settings.OLLAMA_MODEL = row.model
    if row.base_url and row.provider == "ollama":
        app_settings.OLLAMA_BASE_URL = row.base_url
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
        is_local=bool(row.is_local) or row.provider in LOCAL_PROVIDERS,
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
    for p in ALL_PROVIDERS:
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
    row.is_local = body.provider in LOCAL_PROVIDERS
    row.updated_at = datetime.utcnow()

    # If this provider just got a key (или это ollama, которому ключ не нужен) и нет активного —
    # автоактивируем.
    has_credentials = bool(body.api_key) or body.provider in LOCAL_PROVIDERS
    was_auto_activated = False
    if has_credentials:
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
    if provider not in ALL_PROVIDERS:
        raise HTTPException(400, f"Unknown provider: {provider}")

    # Ensure all rows exist
    for p in ALL_PROVIDERS:
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
        model_map = {
            "anthropic": s.LLM_MODEL_ANTHROPIC, "openai": s.LLM_MODEL_OPENAI,
            "openrouter": s.LLM_MODEL_OPENROUTER, "ollama": s.OLLAMA_MODEL,
        }
        return ActiveProviderOut(
            provider=provider,
            model=model_map.get(provider, s.LLM_MODEL_OPENAI),
            base_url=s.OLLAMA_BASE_URL if provider == "ollama" else "",
            temperature=s.LLM_TEMPERATURE,
            max_tokens=s.LLM_MAX_TOKENS,
            route=s.OPENROUTER_ROUTE if provider == "openrouter" else "",
            is_local=(provider in LOCAL_PROVIDERS),
        )
    return ActiveProviderOut(
        provider=row.provider,
        model=row.model or DEFAULT_MODELS.get(row.provider, ""),
        base_url=row.base_url or "",
        temperature=float(row.temperature or "0.2"),
        max_tokens=int(row.max_tokens or "4096"),
        route=row.route or DEFAULT_ROUTES.get(row.provider, ""),
        is_local=bool(row.is_local) or row.provider in LOCAL_PROVIDERS,
    )


@router.get("/providers/ollama/models", response_model=List[OllamaModelOut])
async def list_ollama_models(db: AsyncSession = Depends(get_db)):
    """
    Эпик C4: список реально скачанных на локальной машине моделей (GET {base_url}/api/tags),
    а не текстовое поле, в которое пользователь должен угадать имя модели.
    """
    res = await db.execute(select(ProviderSettings).where(ProviderSettings.provider == "ollama"))
    row = res.scalar_one_or_none()
    base_url = (row.base_url if row and row.base_url else DEFAULT_BASE_URLS["ollama"]).rstrip("/")
    # base_url хранится как OpenAI-совместимый (.../v1) — тэги отдаёт нативный API без /v1
    tags_url = base_url[:-3] + "/api/tags" if base_url.endswith("/v1") else base_url + "/api/tags"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(tags_url)
        if resp.status_code != 200:
            raise HTTPException(502, f"Ollama вернул {resp.status_code} на {tags_url}")
        data = resp.json()
        return [
            OllamaModelOut(
                name=m.get("name", ""),
                size_bytes=m.get("size"),
                modified_at=m.get("modified_at"),
            )
            for m in data.get("models", [])
        ]
    except httpx.RequestError as e:
        raise HTTPException(502, f"Ollama не отвечает на {tags_url}: {e}. Проверьте, что сервис запущен.")


@router.post("/test")
async def test_provider(body: ProviderTestIn, db: AsyncSession = Depends(get_db)):
    """
    Тест соединения по конфигурации, которую пользователь ввёл в форму.
    api_key / model / base_url берутся из тела запроса первыми; если поле пустое —
    добираются из сохранённой настройки (DB) и дефолтов. Это позволяет проверить
    ещё НЕ сохранённый ключ сразу после ввода. Возвращает также итоговую
    использованную конфигурацию (provider/model/base_url).
    """
    provider = body.provider

    res = await db.execute(
        select(ProviderSettings).where(ProviderSettings.provider == provider)
    )
    row = res.scalar_one_or_none()

    db_key = (row.api_key or "") if row else ""
    api_key = (body.api_key or db_key).strip()
    model = body.model or (row.model if row else "") or DEFAULT_MODELS.get(provider, "")
    base_url = body.base_url or (row.base_url if row else "") or DEFAULT_BASE_URLS.get(provider, "")

    config = {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "is_local": provider in LOCAL_PROVIDERS,
    }

    if provider not in LOCAL_PROVIDERS and not api_key:
        raise HTTPException(
            400,
            "API key is not set. Enter it in the form or save the provider first.",
        )

    try:
        if provider == "anthropic":
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=api_key, base_url=base_url or None)
            resp = await client.messages.create(
                model=model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            )
            text = (resp.content[0].text or "")[:50]
            return {"status": "ok", "response": text, "config": config}

        elif provider in ("openai", "proxyapi", "openrouter"):
            from openai import AsyncOpenAI

            client_kwargs: dict = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
            if provider == "openrouter":
                route = body.route or (row.route if row else "") or "openrouter/auto"
                client_kwargs["default_headers"] = {"X-Route": route}
            client = AsyncOpenAI(**client_kwargs)
            resp = await client.chat.completions.create(
                model=model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            )
            text = (resp.choices[0].message.content or "")[:50]
            return {"status": "ok", "response": text, "config": config}

        elif provider == "ollama":
            # Эпик C4: тест — просто пинг /api/tags, ключ не требуется.
            tags_url = base_url[:-3] + "/api/tags" if base_url.endswith("/v1") else base_url + "/api/tags"
            async with httpx.AsyncClient(timeout=5) as hc:
                try:
                    resp = await hc.get(tags_url)
                except httpx.RequestError as e:
                    return {"status": "error",
                            "error": f"Ollama не отвечает на {base_url}: {e}. "
                                     f"Проверьте, что сервис запущен (docker compose --profile local-llm up).",
                            "config": config}
            if resp.status_code != 200:
                return {"status": "error", "error": f"HTTP {resp.status_code} на {tags_url}", "config": config}
            models = [m.get("name") for m in resp.json().get("models", [])]
            return {"status": "ok",
                    "response": f"Локальный контур доступен. Модели: {', '.join(models) or 'нет скачанных'}",
                    "config": config}

    except Exception as e:
        return {"status": "error", "error": str(e)[:300], "config": config}


def _detect_provider(api_key: str, base_url: str) -> dict:
    """Определить провайдера по префиксу API-ключа и/или Base URL (оффлайн-эвристики)."""
    key = (api_key or "").strip()
    base = (base_url or "").strip().lower()

    if not key and not base:
        return {"provider": None, "confidence": "low",
                "reason": "Введите API-ключ (или Base URL для локального сервиса), чтобы определить провайдера.",
                "candidates": []}

    # Локальный контур (Ollama) — ключ не нужен, судим по адресу
    if not key or ("ollama" in base or "127.0.0.1" in base or "localhost" in base or "host.docker.internal" in base):
        return {"provider": "ollama", "confidence": "high",
                "reason": "Ключ отсутствует или указан локальный адрес — это локальный Ollama, API-ключ не требуется.",
                "candidates": ["ollama"]}

    if key.startswith("sk-ant-") or "anthropic.com" in base:
        return {"provider": "anthropic", "confidence": "high",
                "reason": "Ключ начинается с sk-ant- — это API-ключ Anthropic Claude.",
                "candidates": ["anthropic"]}

    if key.startswith("sk-or-") or "openrouter.ai" in base:
        return {"provider": "openrouter", "confidence": "high",
                "reason": "Ключ начинается с sk-or- (или указан OpenRouter) — это ключ OpenRouter.",
                "candidates": ["openrouter"]}

    if "proxyapi.ru" in base:
        return {"provider": "proxyapi", "confidence": "high",
                "reason": "Base URL указывает на ProxyAPI — это ключ ProxyAPI.",
                "candidates": ["proxyapi"]}

    if "openai.com" in base:
        return {"provider": "openai", "confidence": "high",
                "reason": "Base URL указывает на OpenAI — это ключ OpenAI.",
                "candidates": ["openai"]}

    if key.startswith("sk-"):
        return {"provider": None, "confidence": "medium",
                "reason": "Ключ вида sk-* подходит нескольким провайдерам (OpenAI / ProxyAPI / OpenRouter). "
                          "Укажите Base URL или выберите провайдера вручную.",
                "candidates": ["openai", "proxyapi", "openrouter"]}

    return {"provider": None, "confidence": "low",
            "reason": "Не удалось определить провайдера по префиксу ключа. Выберите его вручную или укажите Base URL.",
            "candidates": list(ALL_PROVIDERS)}


@router.post("/detect", response_model=ProviderDetectOut)
async def detect_provider(body: ProviderDetectIn):
    """Определить провайдера по API-ключу / Base URL, чтобы подсказать пользователю настройку."""
    result = _detect_provider(body.api_key, body.base_url)
    provider = result["provider"]
    return ProviderDetectOut(
        status="ok",
        provider=provider,
        confidence=result["confidence"],
        reason=result["reason"],
        candidates=result["candidates"],
        default_model=DEFAULT_MODELS.get(provider, "") if provider else "",
        base_url=DEFAULT_BASE_URLS.get(provider, "") if provider else "",
        is_local=provider in LOCAL_PROVIDERS if provider else False,
    )
