from __future__ import annotations
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict


# ─── Documents ───────────────────────────────────────────────────────────────

class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    text: str = Field(min_length=10, max_length=30_000)
    doc_type: str = Field(default="tz")
    project_name: Optional[str] = None


class DocumentOut(BaseModel):
    id: str
    created_at: datetime
    title: str
    text: str
    doc_type: str
    project_name: Optional[str] = None
    default_requirements_standard: Optional[str] = None
    default_diagram_standard: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ─── Review ──────────────────────────────────────────────────────────────────

class RiskItem(BaseModel):
    severity: str  # low|medium|high
    description: str


class ReviewSchema(BaseModel):
    summary: str = ""
    risks: List[RiskItem] = []
    missing_requirements: List[str] = []
    questions_to_client: List[str] = []
    acceptance_criteria: List[str] = []
    similar_projects: List[str] = []
    lessons_learned: List[str] = []
    related_decisions: List[str] = []
    architecture_risks: List[str] = []
    confidence: str = "medium"
    needs_review: bool = False


class ReviewOut(BaseModel):
    id: str
    created_at: datetime
    document_id: str
    review_json: str
    needs_review: bool
    confidence: str
    error: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ─── Knowledge Base ───────────────────────────────────────────────────────────

class KBQuestionRequest(BaseModel):
    question: str = Field(min_length=5, max_length=2_000)


class SourceItem(BaseModel):
    quote: str
    document_id: Optional[str] = None
    document_title: Optional[str] = None


class AnswerWithSourcesSchema(BaseModel):
    answer: str = ""
    sources: List[SourceItem] = []
    confidence: str = "medium"
    needs_review: bool = False


class QARunOut(BaseModel):
    id: str
    created_at: datetime
    question: str
    answer: str
    sources_json: str
    needs_review: bool
    error: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ─── Audit ───────────────────────────────────────────────────────────────────

class AuditRunOut(BaseModel):
    id: str
    created_at: datetime
    action: str
    input: str
    output: str
    status: str
    error: Optional[str] = None
    duration_ms: int
    provider_used: Optional[str] = None
    is_local_provider: bool = False
    model_config = ConfigDict(from_attributes=True)


# ─── Memory ──────────────────────────────────────────────────────────────────

class MemoryStoreRequest(BaseModel):
    memory_type: str = Field(pattern="^(semantic|episodic|decision|risk|requirement)$")
    content: str = Field(min_length=5, max_length=5_000)
    tags: List[str] = []
    project_name: Optional[str] = None


class MemorySearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1_000)
    memory_type: Optional[str] = None
    project_name: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=50)


class MemoryItemOut(BaseModel):
    id: str
    created_at: datetime
    memory_type: str
    content: str
    tags: str
    project_name: Optional[str] = None
    relevance_score: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)


# ─── Architecture Recommendation ─────────────────────────────────────────────

class AlternativePattern(BaseModel):
    pattern: str
    pros: List[str] = []
    cons: List[str] = []


class ArchitectureRecommendationSchema(BaseModel):
    recommended_pattern: str = ""
    rationale: str = ""
    alternatives: List[AlternativePattern] = []
    integration_recommendations: List[str] = []
    risks: List[RiskItem] = []
    confidence: str = "medium"
    needs_review: bool = False


class ArchitectureReviewOut(BaseModel):
    id: str
    created_at: datetime
    document_id: str
    recommendation_json: str
    needs_review: bool
    model_config = ConfigDict(from_attributes=True)


# ─── ADR ─────────────────────────────────────────────────────────────────────

class ADRAlternative(BaseModel):
    option: str
    reason_rejected: str


class ADRConsequences(BaseModel):
    positive: List[str] = []
    negative: List[str] = []


class ADRSchema(BaseModel):
    title: str = ""
    status: str = "proposed"
    context: str = ""
    problem: str = ""
    decision: str = ""
    alternatives: List[ADRAlternative] = []
    consequences: ADRConsequences = ADRConsequences()
    confidence: str = "medium"
    needs_review: bool = False


class ADRRecordOut(BaseModel):
    id: str
    created_at: datetime
    document_id: str
    adr_json: str
    model_config = ConfigDict(from_attributes=True)


# ─── API Spec ─────────────────────────────────────────────────────────────────

class APISpecOut(BaseModel):
    id: str
    created_at: datetime
    document_id: str
    openapi_json: str
    openapi_yaml: str
    model_config = ConfigDict(from_attributes=True)


# ─── Diagrams ─────────────────────────────────────────────────────────────────

class ViewpointItem(BaseModel):
    """Эпик B4: вид архитектуры по ISO/IEC/IEEE 42010, привязанный к интересу стейкхолдера."""
    name: str = ""
    stakeholder_concern: str = ""
    diagram_code: str = ""


class DiagramSetSchema(BaseModel):
    c4_context: str = ""
    c4_container: str = ""
    c4_component: str = ""
    use_case: str = ""
    sequence: str = ""
    class_diagram: str = ""
    erd: str = ""
    mermaid_flowchart: str = ""
    confidence: str = "medium"
    needs_review: bool = False
    standard_profile: str = "C4_MODEL"
    viewpoints: List[ViewpointItem] = []


class DiagramArtifactOut(BaseModel):
    id: str
    created_at: datetime
    document_id: str
    diagram_type: str
    notation: str
    source_code: str
    render_svg: str | None = None
    rendered_at: datetime | None = None
    render_status: str = "pending"
    render_error: str | None = None
    standard_profile: str | None = None
    model_config = ConfigDict(from_attributes=True)


class DiagramUpdateIn(BaseModel):
    source_code: str = Field(min_length=1, max_length=50_000)
    change_note: str = Field(default="", max_length=300)


class DiagramVersionOut(BaseModel):
    id: str
    diagram_artifact_id: str
    version_number: int
    source_code: str
    notation: str
    created_at: datetime
    created_by: str | None = None
    change_note: str | None = None
    model_config = ConfigDict(from_attributes=True)


class DocumentationStandardOut(BaseModel):
    id: str
    name_ru: str
    name_en: str
    family: str
    description: str | None = None
    is_active: bool = True
    model_config = ConfigDict(from_attributes=True)


class RequirementsDocumentOut(BaseModel):
    id: str
    document_id: str
    doc_kind: str
    standard_profile: str
    content_json: str
    confidence: str
    needs_review: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DocumentStandardsIn(BaseModel):
    default_requirements_standard: str | None = None
    default_diagram_standard: str | None = None


# ─── Batch Review (Фаза 2) ─────────────────────────────────────────────────────

class BatchReviewInputItem(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=10, max_length=30_000)


class BatchReviewCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=300)
    items: List[BatchReviewInputItem] = Field(min_length=1, max_length=50)
    reasoning_mode: str = Field(default="direct", pattern="^(direct|cot|react)$")


class BatchReviewItemOut(BaseModel):
    id: str
    order_index: int
    title: str
    document_id: Optional[str] = None
    review_id: Optional[str] = None
    status: str
    needs_review: bool
    confidence: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BatchReviewOut(BaseModel):
    id: str
    created_at: datetime
    title: Optional[str] = None
    status: str
    total_count: int
    completed_count: int
    needs_review_count: int
    error_count: int
    model_config = ConfigDict(from_attributes=True)


class BatchReviewDetailOut(BatchReviewOut):
    items: List[BatchReviewItemOut] = []


# ─── Coverage / упрощённая трассируемость (Фаза 2) ────────────────────────────
# Честная оговорка: это агрегированные счётчики покрытия (сколько требований/диаграмм/
# критериев приёмки есть у документа), а НЕ пооперационная привязка "требование → элемент
# диаграммы" — такая точная трассируемость потребовала бы отдельного LLM-этапа сопоставления
# и не реализована в этом объёме.

class CoverageRequirementItem(BaseModel):
    id: str = ""
    description: str = ""


class CoverageOut(BaseModel):
    document_id: str
    requirements_standard: Optional[str] = None
    diagram_standard: Optional[str] = None
    requirements: List[CoverageRequirementItem] = []
    requirements_source: Optional[str] = None  # "urs" | "srs" | None
    diagrams_count: int = 0
    diagrams_rendered_count: int = 0
    diagrams_by_type: List[str] = []
    acceptance_criteria: List[str] = []
    risks_count: int = 0
    risks_high_count: int = 0
    has_requirements: bool = False
    has_diagrams: bool = False
    has_acceptance_criteria: bool = False
    is_fully_covered: bool = False


# ─── Review diff (Фаза 2) ──────────────────────────────────────────────────────
# Сравнение двух рецензий одного документа (например, до/после обновлённого ТЗ от заказчика).

class ReviewDiffOut(BaseModel):
    from_review_id: str
    to_review_id: str
    from_created_at: datetime
    to_created_at: datetime
    confidence_changed: bool = False
    confidence_from: str = ""
    confidence_to: str = ""
    needs_review_changed: bool = False
    needs_review_from: bool = False
    needs_review_to: bool = False
    summary_diff_lines: List[str] = []  # unified diff строк резюме
    risks_added: List[str] = []
    risks_removed: List[str] = []
    acceptance_criteria_added: List[str] = []
    acceptance_criteria_removed: List[str] = []
    missing_requirements_added: List[str] = []
    missing_requirements_removed: List[str] = []


# ─── URS / SRS ────────────────────────────────────────────────────────────────

class URSSchema(BaseModel):
    title: str = ""
    objective: str = ""
    stakeholders: List[str] = []
    user_requirements: List[dict] = []
    non_functional_requirements: List[dict] = []
    constraints: List[str] = []
    missing_requirements: List[str] = []
    confidence: str = "medium"
    needs_review: bool = False
    standard_profile: str = "ISO_IEC_IEEE_29148"


class SRSSchema(BaseModel):
    title: str = ""
    introduction: str = ""
    overall_description: str = ""
    functional_requirements: List[dict] = []
    non_functional_requirements: List[dict] = []
    external_interfaces: List[str] = []
    missing_requirements: List[str] = []
    confidence: str = "medium"
    needs_review: bool = False
    standard_profile: str = "ISO_IEC_IEEE_29148"


# ─── Direct AI call ──────────────────────────────────────────────────────────

class DirectReviewRequest(BaseModel):
    text: str = Field(min_length=1, max_length=30_000)
    reasoning_mode: str = Field(default="direct", pattern="^(direct|cot|react)$")


class DirectAnswerRequest(BaseModel):
    question: str = Field(min_length=5, max_length=2_000)
    context: str = Field(default="", max_length=50_000)


# ─── Provider Settings ────────────────────────────────────────────────────────

class ProviderSettingsIn(BaseModel):
    provider: str = Field(pattern="^(anthropic|openai|proxyapi|openrouter|ollama)$")
    api_key: str = Field(default="", max_length=500)
    model: str = Field(default="", max_length=100)
    base_url: str = Field(default="", max_length=500)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=256, le=32768)
    route: str = Field(default="openrouter/free", max_length=50)
    is_active: bool = False


class ProviderSettingsOut(BaseModel):
    id: str
    updated_at: datetime
    provider: str
    api_key_masked: str   # show only last 4 chars
    model: str
    base_url: str
    temperature: float
    max_tokens: int
    route: str
    is_active: bool
    is_local: bool = False

    model_config = ConfigDict(from_attributes=True)


class ActiveProviderOut(BaseModel):
    provider: str
    model: str
    base_url: str
    temperature: float
    max_tokens: int
    route: str
    is_local: bool = False


class OllamaModelOut(BaseModel):
    name: str
    size_bytes: int | None = None
    modified_at: str | None = None


class ProviderStatsOut(BaseModel):
    provider: str
    is_local: bool
    total_runs: int
    error_rate_pct: float
    needs_review_rate_pct: float
    avg_duration_ms: float


# ─── Economic Module: Build Projects, Task Estimates, ROI ────────────────────

class BuildProjectCreate(BaseModel):
    document_id: str
    name: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=5000)


class BuildProjectOut(BaseModel):
    id: str
    created_at: datetime
    document_id: str
    name: str
    description: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class TaskItem(BaseModel):
    name: str
    role: str  # backend|frontend|qa|devops|analyst
    story_points: int = 1
    estimated_hours: float = 0.0
    risk_multiplier: float = 1.0


class TaskDecompositionSchema(BaseModel):
    tasks: List[TaskItem] = []
    total_hours_by_role: dict = {}
    confidence: str = "medium"
    needs_review: bool = False


class TaskEstimateOut(BaseModel):
    id: str
    created_at: datetime
    project_id: str
    tasks_json: str
    total_hours: float
    confidence: str
    needs_review: bool

    model_config = ConfigDict(from_attributes=True)


class EconomicEstimateIn(BaseModel):
    rate_backend: float = Field(default=2500.0, ge=0)
    rate_frontend: float = Field(default=2200.0, ge=0)
    rate_qa: float = Field(default=1800.0, ge=0)
    rate_devops: float = Field(default=2800.0, ge=0)
    rate_analyst: float = Field(default=2500.0, ge=0)
    hosting_cost_monthly: float = Field(default=5000.0, ge=0)
    llm_cost_monthly: float = Field(default=3000.0, ge=0)
    support_hours_monthly: float = Field(default=8.0, ge=0)
    time_saved_hours_monthly: float = Field(default=0.0, ge=0)
    avg_employee_rate: float = Field(default=2500.0, ge=0)
    # Optional manual override of hours-by-role (if no task estimate yet)
    manual_hours_by_role: Optional[dict] = None


class EconomicEstimateOut(BaseModel):
    id: str
    created_at: datetime
    project_id: str
    rate_backend: float
    rate_frontend: float
    rate_qa: float
    rate_devops: float
    rate_analyst: float
    hosting_cost_monthly: float
    llm_cost_monthly: float
    support_hours_monthly: float
    time_saved_hours_monthly: float
    avg_employee_rate: float
    capex: float
    opex_monthly: float
    benefit_monthly: float
    payback_months: float
    roi_12m_pct: float

    model_config = ConfigDict(from_attributes=True)


class EconomicActualIn(BaseModel):
    actual_capex: float = Field(default=0.0, ge=0)
    actual_opex_monthly: float = Field(default=0.0, ge=0)
    actual_benefit_monthly: float = Field(default=0.0, ge=0)
    actual_time_saved_hours_monthly: float = Field(default=0.0, ge=0)
    notes: str = Field(default="", max_length=2000)


class EconomicActualOut(BaseModel):
    id: str
    created_at: datetime
    project_id: str
    actual_capex: float
    actual_opex_monthly: float
    actual_benefit_monthly: float
    actual_time_saved_hours_monthly: float
    notes: str

    model_config = ConfigDict(from_attributes=True)


class BuildProjectReportOut(BaseModel):
    project: BuildProjectOut
    latest_task_estimate: Optional[TaskEstimateOut] = None
    latest_economic_estimate: Optional[EconomicEstimateOut] = None
    latest_actual: Optional[EconomicActualOut] = None
    variance: dict = {}   # plan-vs-fact deltas, computed at read time


# ─── Risk Catalog ─────────────────────────────────────────────────────────────

def compute_severity(probability: int, impact: int) -> str:
    product = probability * impact
    if product >= 13:
        return "critical"
    if product >= 9:
        return "high"
    if product >= 5:
        return "medium"
    return "low"


class RiskCatalogItemIn(BaseModel):
    project_name: Optional[str] = None
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=5000)
    probability: int = Field(default=1, ge=1, le=5)
    impact: int = Field(default=1, ge=1, le=5)
    category: str = Field(default="tech", pattern="^(tech|process|business|security)$")
    status: str = Field(default="open", pattern="^(open|mitigated|closed|accepted|reopened)$")
    owner: Optional[str] = None
    mitigation: Optional[str] = None
    document_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RiskCatalogItemOut(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    project_name: Optional[str] = None
    title: str
    description: str
    probability: int
    impact: int
    severity: str = ""
    category: str
    status: str
    owner: Optional[str] = None
    mitigation: Optional[str] = None
    document_id: Optional[str] = None
    source: str

    model_config = ConfigDict(from_attributes=True)


class RiskStatsOut(BaseModel):
    total: int
    by_severity: dict[str, int]
    by_category: dict[str, int]
    by_status: dict[str, int]
    by_project: dict[str, int]


# ─── Project Lessons ──────────────────────────────────────────────────────────

class ProjectLessonIn(BaseModel):
    project_name: Optional[str] = None
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=5000)
    category: str = Field(default="technology", pattern="^(technology|process|communication|estimation)$")
    impact_type: str = Field(default="negative", pattern="^(positive|negative)$")
    root_cause: Optional[str] = None
    recommendation: Optional[str] = None
    document_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectLessonOut(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    project_name: Optional[str] = None
    title: str
    description: str
    category: str
    impact_type: str
    root_cause: Optional[str] = None
    recommendation: Optional[str] = None
    document_id: Optional[str] = None
    source: str

    model_config = ConfigDict(from_attributes=True)
