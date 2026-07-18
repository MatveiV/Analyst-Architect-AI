"""
Unified LLM client — Anthropic Claude, OpenAI GPT, ProxyAPI, OpenRouter, Ollama (Эпик C).

Priority for runtime config:
  1. DB-stored ProviderSettings (if api_key present, or provider == "ollama")
  2. app.config.settings (from .env)
"""
import json
from app.config import settings

# ── Эпик C3: метаданные последнего вызова, для audit_service (доказуемость локальности) ──
_last_call_meta: dict = {"provider": None, "is_local": False}


def get_last_call_meta() -> dict:
    """Возвращает провайдера последнего вызова call_llm() — используется audit_service,
    чтобы записать в audit_runs, был ли конкретный запуск локальным (провайдер ollama)."""
    return dict(_last_call_meta)


async def _load_active_config() -> dict:
    """
    Try to load active provider config from DB.
    Returns dict with: provider, api_key, model, base_url, temperature, max_tokens.
    Falls back to env-based settings if DB is empty / not reachable.
    """
    try:
        from app.database import AsyncSessionLocal
        from app.models.provider_settings import ProviderSettings
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            # 1) Try active provider with key (Ollama не требует ключа — Эпик C1)
            res = await db.execute(
                select(ProviderSettings).where(ProviderSettings.is_active == "true")
            )
            row = res.scalar_one_or_none()
            if row and (row.api_key or row.provider == "ollama"):
                return _cfg_from_row(row)

            # 2) Try any provider with a key if none is active
            res = await db.execute(
                select(ProviderSettings).where(
                    ProviderSettings.api_key != "",
                    ProviderSettings.api_key.isnot(None),
                )
            )
            any_with_key = res.scalars().all()
            if any_with_key:
                return _cfg_from_row(any_with_key[0])
    except Exception:
        pass  # DB not ready or no active row — fall through to env

    # Fallback to env
    return _cfg_from_env()

def _cfg_from_row(row) -> dict:
    return {
        "provider": row.provider,
        "api_key": row.api_key or ("ollama" if row.provider == "ollama" else ""),
        "model": row.model,
        "base_url": row.base_url or (settings.OLLAMA_BASE_URL if row.provider == "ollama" else ""),
        "temperature": float(row.temperature or "0.2"),
        "max_tokens": int(row.max_tokens or "4096"),
        "route": row.route or "",
        "is_local": bool(getattr(row, "is_local", False)) or row.provider == "ollama",
    }

def _cfg_from_env() -> dict:
    provider = settings.LLM_PROVIDER.lower()
    model_map = {
        "anthropic": settings.LLM_MODEL_ANTHROPIC,
        "openai": settings.LLM_MODEL_OPENAI,
        "openrouter": settings.LLM_MODEL_OPENROUTER,
        "ollama": settings.OLLAMA_MODEL,
    }
    api_key_map = {
        "anthropic": settings.ANTHROPIC_API_KEY,
        "openai": settings.OPENAI_API_KEY,
        "proxyapi": settings.PROXYAPI_KEY,
        "openrouter": settings.OPENROUTER_API_KEY,
        # Ollama не проверяет ключ, но OpenAI-совместимому клиенту нужна непустая строка.
        "ollama": "ollama",
    }
    base_url_map = {
        "openrouter": settings.OPENROUTER_BASE_URL,
        "proxyapi": settings.PROXYAPI_BASE_URL,
        "ollama": settings.OLLAMA_BASE_URL,
    }
    route_map = {"openrouter": settings.OPENROUTER_ROUTE}
    return {
        "provider": provider,
        "api_key": api_key_map.get(provider, ""),
        "model": model_map.get(provider, settings.LLM_MODEL_OPENAI),
        "base_url": base_url_map.get(provider, ""),
        "temperature": settings.LLM_TEMPERATURE,
        "max_tokens": settings.LLM_MAX_TOKENS,
        "route": route_map.get(provider, ""),
        "is_local": provider == "ollama",
    }


async def call_llm(prompt: str, system: str = "") -> str:
    """
    Call the active LLM provider and return raw string response.
    Raises RuntimeError on failure.
    """
    global _last_call_meta
    cfg = await _load_active_config()
    provider = cfg["provider"]
    api_key = cfg.get("api_key", "")

    # Эпик C3: фиксируем провайдера ДО вызова, чтобы audit_service мог записать
    # provider_used/is_local_provider даже если сам вызов упадёт с ошибкой.
    _last_call_meta = {"provider": provider, "is_local": bool(cfg.get("is_local", False))}

    if not api_key and provider != "ollama":
        raise RuntimeError(
            f"API-ключ для {provider} не настроен. "
            f"Укажите ключ в Настройках → {provider.upper()} или в файле .env"
        )

    if provider == "anthropic":
        return await _call_anthropic(prompt, system, cfg)
    elif provider in ("openai", "proxyapi", "openrouter"):
        return await _call_openai_compat(prompt, system, cfg)
    elif provider == "ollama":
        return await _call_ollama(prompt, system, cfg)
    else:
        raise RuntimeError(f"Unknown LLM provider: {provider}")


async def _call_ollama(prompt: str, system: str, cfg: dict) -> str:
    """
    Эпик C1: Ollama отдаёт OpenAI-совместимый /v1/chat/completions — переиспользуем
    _call_openai_compat(), но принудительно включаем JSON-режим (constrained decoding),
    т.к. локальные модели заметно хуже держат формат, чем облачные.

    Если первый ответ пустой/невалидный — один explicit retry с более прямой инструкцией,
    прежде чем сервис-вызывающая сторона откатится на safe_fallback_*.
    """
    text = await _call_openai_compat(prompt, system, cfg, force_json=True)
    if text and text.strip():
        return text

    retry_system = (
        (system or "") + "\n\nВАЖНО: верни ТОЛЬКО валидный JSON, без единого слова до или после, "
        "без markdown-разметки и пояснений."
    )
    return await _call_openai_compat(prompt, retry_system, cfg, force_json=True)


async def _call_anthropic(prompt: str, system: str, cfg: dict) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=cfg["api_key"])
    response = client.messages.create(
        model=cfg["model"] or settings.LLM_MODEL_ANTHROPIC,
        max_tokens=cfg["max_tokens"],
        temperature=cfg["temperature"],
        system=system or "You are a helpful assistant. Always respond in the requested JSON format.",
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text
    return text or ""


async def _call_openai_compat(prompt: str, system: str, cfg: dict, force_json: bool = False) -> str:
    """
    OpenAI-compatible call — works for OpenAI, ProxyAPI, OpenRouter, and Ollama.
    ProxyAPI is an OpenAI-compatible proxy that supports Claude models.
    OpenRouter uses X-Route header to select routing mode.
    force_json=True (Ollama, Эпик C1) — включает constrained JSON decoding на стороне модели,
    что заметно повышает надёжность строгого JSON-контракта у более слабых локальных моделей.
    """
    from openai import OpenAI

    client_kwargs: dict = {"api_key": cfg["api_key"]}
    if cfg.get("base_url"):
        client_kwargs["base_url"] = cfg["base_url"]

    default_headers: dict = {}
    if cfg.get("provider") == "openrouter" and cfg.get("route"):
        default_headers["X-Route"] = cfg["route"]
    if default_headers:
        client_kwargs["default_headers"] = default_headers

    client = OpenAI(**client_kwargs)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    model = cfg["model"] or (settings.LLM_MODEL_OPENROUTER if cfg.get("provider") == "openrouter" else settings.LLM_MODEL_OPENAI)
    extra_kwargs: dict = {}
    if force_json:
        # Ollama принимает OpenAI-совместимый response_format={"type": "json_object"}
        extra_kwargs["extra_body"] = {"format": "json"}
    response = client.chat.completions.create(
        model=model,
        max_tokens=cfg["max_tokens"],
        temperature=cfg["temperature"],
        messages=messages,
        **extra_kwargs,
    )
    content = response.choices[0].message.content
    return content or ""


def extract_json(raw: str) -> str:
    """Strip markdown code fences if present and return clean JSON string."""
    raw = raw.strip()
    if not raw:
        return ""
    # Find ``` markers anywhere in the response
    import re
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", raw, re.DOTALL)
    if m:
        raw = m.group(1).strip()
    # If still wrapped in ``` but no closing fence, strip opening
    elif raw.startswith("```"):
        lines = raw.split("\n")
        start = 1
        end = len(lines) - 1
        if lines[-1].strip() == "```":
            end = len(lines) - 1
        raw = "\n".join(lines[start:end]).strip()
    # Strip leading/trailing non-JSON noise (anything before { or [)
    first_brace = raw.find("{")
    first_bracket = raw.find("[")
    if first_brace >= 0 or first_bracket >= 0:
        start = first_brace if first_brace >= 0 else first_bracket
        if first_bracket >= 0 and (first_brace < 0 or first_bracket < first_brace):
            start = first_bracket
        raw = raw[start:]
    # Strip trailing non-JSON after matching braces
    depth = 0
    end_pos = 0
    for i, ch in enumerate(raw):
        if ch in ("{", "["):
            depth += 1
        elif ch in ("}", "]"):
            depth -= 1
        if depth == 0:
            end_pos = i + 1
            break
    if end_pos > 0:
        raw = raw[:end_pos]

    # Convert single-quoted keys/values to double-quoted JSON (common LLM mistake)
    raw = _fix_single_quotes(raw)

    return raw.strip()


def _fix_single_quotes(text: str) -> str:
    """Replace Python-style single-quoted strings with JSON double-quotes."""
    import re
    # Fix single-quoted property names: {'key': -> {"key":
    text = re.sub(r"(?<=[{,])\s*'([^']*?)'\s*:", r'"\1":', text)
    # Fix single-quoted string values: : 'value' -> : "value"
    text = re.sub(r":\s*'([^']*?)'\s*([,}\]])", r':"\1"\2', text)
    return text
