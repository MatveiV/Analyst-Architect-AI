"""
Economics Service — прозрачный расчёт CAPEX/OPEX/ROI/payback.

Никакого "чёрного ящика": формулы — обычная арифметика над ставками
и часами. AI участвует только на этапе оценки часов (task_estimator),
все финансовые расчёты выполняются детерминированно в Python.
"""
from app.schemas import EconomicEstimateIn

RATE_FIELD_BY_ROLE = {
    "backend": "rate_backend",
    "frontend": "rate_frontend",
    "qa": "rate_qa",
    "devops": "rate_devops",
    "analyst": "rate_analyst",
}


def compute_capex(hours_by_role: dict, rates: EconomicEstimateIn) -> float:
    """CAPEX = Σ(hours_by_role × hourly_rate_by_role)."""
    total = 0.0
    for role, hours in hours_by_role.items():
        rate_field = RATE_FIELD_BY_ROLE.get(role)
        rate = getattr(rates, rate_field, None) if rate_field else None
        # Unknown role → fall back to analyst rate (conservative estimate)
        rate = rate if rate is not None else rates.rate_analyst
        total += hours * rate
    return round(total, 2)


def compute_opex_monthly(rates: EconomicEstimateIn) -> float:
    """OPEX = hosting + LLM costs + support hours × rate."""
    support_cost = rates.support_hours_monthly * rates.rate_backend
    return round(rates.hosting_cost_monthly + rates.llm_cost_monthly + support_cost, 2)


def compute_benefit_monthly(rates: EconomicEstimateIn) -> float:
    """Benefit = time saved (hours/month) × average employee rate."""
    return round(rates.time_saved_hours_monthly * rates.avg_employee_rate, 2)


def compute_payback_months(capex: float, benefit_monthly: float, opex_monthly: float) -> float:
    """Payback period in months. Returns -1 if the project never pays back (net monthly gain <= 0)."""
    net_monthly = benefit_monthly - opex_monthly
    if net_monthly <= 0:
        return -1.0
    return round(capex / net_monthly, 1)


def compute_roi_12m_pct(capex: float, benefit_monthly: float, opex_monthly: float) -> float:
    """ROI over a 12-month horizon, as a percentage of CAPEX."""
    if capex <= 0:
        return 0.0
    net_monthly = benefit_monthly - opex_monthly
    roi = ((net_monthly * 12) - capex) / capex * 100
    return round(roi, 1)


def full_economic_calculation(hours_by_role: dict, rates: EconomicEstimateIn) -> dict:
    """Run the complete pipeline and return all outputs as a dict."""
    capex = compute_capex(hours_by_role, rates)
    opex_monthly = compute_opex_monthly(rates)
    benefit_monthly = compute_benefit_monthly(rates)
    payback_months = compute_payback_months(capex, benefit_monthly, opex_monthly)
    roi_12m_pct = compute_roi_12m_pct(capex, benefit_monthly, opex_monthly)

    return {
        "capex": capex,
        "opex_monthly": opex_monthly,
        "benefit_monthly": benefit_monthly,
        "payback_months": payback_months,
        "roi_12m_pct": roi_12m_pct,
    }


def compute_variance(estimate: dict, actual: dict) -> dict:
    """Compare plan (estimate) vs fact (actual) and return absolute + percentage deltas."""
    variance = {}
    pairs = [
        ("capex", "actual_capex"),
        ("opex_monthly", "actual_opex_monthly"),
        ("benefit_monthly", "actual_benefit_monthly"),
    ]
    for plan_key, actual_key in pairs:
        plan_val = estimate.get(plan_key, 0.0) or 0.0
        actual_val = actual.get(actual_key, 0.0) or 0.0
        delta = round(actual_val - plan_val, 2)
        pct = round((delta / plan_val * 100), 1) if plan_val else 0.0
        variance[plan_key] = {"plan": plan_val, "actual": actual_val, "delta": delta, "delta_pct": pct}
    return variance
