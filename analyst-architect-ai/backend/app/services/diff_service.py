"""
Diff service — Фаза 2: сравнение двух рецензий одного документа (например, до/после
того, как заказчик прислал обновлённое ТЗ). Считает построчный diff резюме и
added/removed для списковых полей (риски, критерии приёмки, отсутствующие требования).
"""
import difflib
import json
from app.models.review import Review
from app.schemas import ReviewDiffOut


def _risk_descriptions(risks: list) -> set[str]:
    return {r.get("description", "") for r in risks if isinstance(r, dict) and r.get("description")}


def compute_review_diff(from_review: Review, to_review: Review) -> ReviewDiffOut:
    from_data = json.loads(from_review.review_json)
    to_data = json.loads(to_review.review_json)

    from_summary_lines = (from_data.get("summary") or "").splitlines()
    to_summary_lines = (to_data.get("summary") or "").splitlines()
    summary_diff = list(difflib.unified_diff(
        from_summary_lines, to_summary_lines,
        fromfile="summary (было)", tofile="summary (стало)", lineterm="",
    ))

    from_risks = _risk_descriptions(from_data.get("risks", []))
    to_risks = _risk_descriptions(to_data.get("risks", []))

    from_ac = set(from_data.get("acceptance_criteria", []))
    to_ac = set(to_data.get("acceptance_criteria", []))

    from_missing = set(from_data.get("missing_requirements", []))
    to_missing = set(to_data.get("missing_requirements", []))

    return ReviewDiffOut(
        from_review_id=from_review.id,
        to_review_id=to_review.id,
        from_created_at=from_review.created_at,
        to_created_at=to_review.created_at,
        confidence_changed=from_review.confidence != to_review.confidence,
        confidence_from=from_review.confidence or "",
        confidence_to=to_review.confidence or "",
        needs_review_changed=from_review.needs_review != to_review.needs_review,
        needs_review_from=from_review.needs_review,
        needs_review_to=to_review.needs_review,
        summary_diff_lines=summary_diff,
        risks_added=sorted(to_risks - from_risks),
        risks_removed=sorted(from_risks - to_risks),
        acceptance_criteria_added=sorted(to_ac - from_ac),
        acceptance_criteria_removed=sorted(from_ac - to_ac),
        missing_requirements_added=sorted(to_missing - from_missing),
        missing_requirements_removed=sorted(from_missing - to_missing),
    )
