"""
Unified LLM client — Anthropic Claude, OpenAI GPT, ProxyAPI.

Priority for runtime config:
  1. DB-stored ProviderSettings (if api_key present)
  2. app.config.settings (from .env)
"""
import json
from app.config import settings


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
            # 1) Try active provider with key
            res = await db.execute(
                select(ProviderSettings).where(ProviderSettings.is_active == "true")
            )
            row = res.scalar_one_or_none()
            if row and row.api_key:
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
        "api_key": row.api_key,
        "model": row.model,
        "base_url": row.base_url or "",
        "temperature": float(row.temperature or "0.2"),
        "max_tokens": int(row.max_tokens or "4096"),
        "route": row.route or "",
    }

def _cfg_from_env() -> dict:
    provider = settings.LLM_PROVIDER.lower()
    model_map = {"anthropic": settings.LLM_MODEL_ANTHROPIC, "openai": settings.LLM_MODEL_OPENAI, "openrouter": settings.LLM_MODEL_OPENROUTER}
    api_key_map = {"anthropic": settings.ANTHROPIC_API_KEY, "openai": settings.OPENAI_API_KEY, "proxyapi": settings.PROXYAPI_KEY, "openrouter": settings.OPENROUTER_API_KEY}
    base_url_map = {"openrouter": settings.OPENROUTER_BASE_URL, "proxyapi": settings.PROXYAPI_BASE_URL}
    route_map = {"openrouter": settings.OPENROUTER_ROUTE}
    return {
        "provider": provider,
        "api_key": api_key_map.get(provider, ""),
        "model": model_map.get(provider, settings.LLM_MODEL_OPENAI),
        "base_url": base_url_map.get(provider, ""),
        "temperature": settings.LLM_TEMPERATURE,
        "max_tokens": settings.LLM_MAX_TOKENS,
        "route": route_map.get(provider, ""),
    }


async def call_llm(prompt: str, system: str = "") -> str:
    """
    Call the active LLM provider and return raw string response.
    Raises RuntimeError on failure.
    """
    cfg = await _load_active_config()
    provider = cfg["provider"]
    api_key = cfg.get("api_key", "")

    if not api_key:
        raise RuntimeError(
            f"API-ключ для {provider} не настроен. "
            f"Укажите ключ в Настройках → {provider.upper()} или в файле .env"
        )

    if provider == "anthropic":
        return await _call_anthropic(prompt, system, cfg)
    elif provider in ("openai", "proxyapi", "openrouter"):
        return await _call_openai_compat(prompt, system, cfg)
    else:
        raise RuntimeError(f"Unknown LLM provider: {provider}")


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


async def _call_openai_compat(prompt: str, system: str, cfg: dict) -> str:
    """
    OpenAI-compatible call — works for OpenAI, ProxyAPI, and OpenRouter.
    ProxyAPI is an OpenAI-compatible proxy that supports Claude models.
    OpenRouter uses X-Route header to select routing mode.
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
    response = client.chat.completions.create(
        model=model,
        max_tokens=cfg["max_tokens"],
        temperature=cfg["temperature"],
        messages=messages,
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
