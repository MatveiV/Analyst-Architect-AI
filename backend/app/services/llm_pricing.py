"""
LLM Pricing — приближённые цены за 1M токенов (USD), для оценки реальной стоимости
LLM-вызовов на основе фактического расхода токенов из audit_runs.

Честная оговорка: цифры ниже — ориентировочные (публичные прайсы на момент написания),
не гарантированно актуальные и не учитывают скидки/тарифы конкретного аккаунта (особенно
для ProxyAPI/OpenRouter, где действует своя наценка). Для реальной защиты/production —
свериться с актуальным прайсом провайдера. Локальные модели (Ollama) — $0, это не
приближение, а факт: инференс идёт на своём железе.
"""

# (model_substring, input_usd_per_1m, output_usd_per_1m) — matched by substring, first match wins
PRICING_TABLE: list[tuple[str, float, float]] = [
    ("claude-opus-4-8", 15.0, 75.0),
    ("claude-opus", 15.0, 75.0),
    ("claude-sonnet", 3.0, 15.0),
    ("claude-haiku", 0.8, 4.0),
    ("gpt-4o-mini", 0.15, 0.6),
    ("gpt-4o", 2.5, 10.0),
    ("gpt-4-turbo", 10.0, 30.0),
    ("gpt-3.5", 0.5, 1.5),
]

# Провайдеры, для которых стоимость всегда $0 (инференс на своём железе)
FREE_PROVIDERS = {"ollama"}

# Если модель не нашлась в таблице (например, кастомный роут OpenRouter) — консервативная
# оценка "средней" облачной модели, чтобы не показывать в отчёте ложный ноль.
DEFAULT_INPUT_USD_PER_1M = 3.0
DEFAULT_OUTPUT_USD_PER_1M = 15.0


def estimate_cost_usd(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    if provider in FREE_PROVIDERS:
        return 0.0
    model_l = (model or "").lower()
    in_rate, out_rate = DEFAULT_INPUT_USD_PER_1M, DEFAULT_OUTPUT_USD_PER_1M
    for substr, in_price, out_price in PRICING_TABLE:
        if substr in model_l:
            in_rate, out_rate = in_price, out_price
            break
    cost = (input_tokens / 1_000_000) * in_rate + (output_tokens / 1_000_000) * out_rate
    return round(cost, 6)
