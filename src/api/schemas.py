"""Pydantic schemas for the CMS Fraud Detection API.

Covers providers, claims, scoring, dashboard, and fairness endpoints.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.scoring.taxonomy import HIGH_RISK_SCORE_THRESHOLD, STABLE_RISK_CEILING

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RiskBand(StrEnum):
    high_risk = "high_risk"
    review = "review"
    stable = "stable"


class Recommendation(StrEnum):
    approve = "approve"
    review = "review"
    deny = "deny"


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int


# ---------------------------------------------------------------------------
# Provider schemas
# ---------------------------------------------------------------------------


class ProviderSummary(BaseModel):
    """Lightweight provider for list views and search results."""

    npi: str
    provider_name: str | None = None
    provider_type: str | None = None
    state: str | None = None
    city: str | None = None
    entity_code: str | None = None
    max_seed_risk_score: int | None = None
    risk_band: RiskBand | None = None
    service_line_count: int | None = None
    total_estimated_payment: float | None = None
    revoked_2026: int | None = None


class ProviderDetail(BaseModel):
    """Full provider profile with all features."""

    # Identity
    npi: str
    provider_name: str | None = None
    entity_code: str | None = None
    city: str | None = None
    state: str | None = None
    zip5: str | None = None
    provider_type: str | None = None
    medicare_participating: str | None = None

    # Enrollment
    enrolled_2025: int | None = None
    enrollment_record_count: int | None = None
    revoked_2026: int | None = None
    revocation_reason: str | None = None

    # Aggregate totals
    provider_total_hcpcs_codes: float | None = None
    provider_total_benes: float | None = None
    provider_total_services: float | None = None
    provider_total_payment_amt: float | None = None

    # Volume features
    unique_hcpcs_codes: int | None = None
    unique_place_of_service: int | None = None
    service_line_count: int | None = None
    total_benes: float | None = None
    total_services: float | None = None
    total_bene_day_services: float | None = None
    avg_benes_per_line: float | None = None
    avg_services_per_line: float | None = None
    avg_services_per_bene: float | None = None
    max_services_per_bene: float | None = None
    std_services_per_bene: float | None = None

    # Charge features
    mean_submitted_charge: float | None = None
    max_submitted_charge: float | None = None
    std_submitted_charge: float | None = None
    mean_allowed_amt: float | None = None
    max_allowed_amt: float | None = None
    mean_payment_amt: float | None = None
    max_payment_amt: float | None = None
    std_payment_amt: float | None = None
    total_estimated_payment: float | None = None
    mean_charge_ratio: float | None = None
    max_charge_ratio: float | None = None
    std_charge_ratio: float | None = None
    mean_payment_ratio: float | None = None

    # Concentration
    service_hhi: float | None = None
    top_code_share: float | None = None
    top3_code_share: float | None = None

    # Peer z-scores
    mean_volume_z: float | None = None
    max_volume_z: float | None = None
    mean_intensity_z: float | None = None
    max_intensity_z: float | None = None
    mean_charge_z: float | None = None
    max_charge_z: float | None = None
    mean_payment_z: float | None = None
    max_payment_z: float | None = None
    n_volume_outlier_lines: int | None = None
    n_intensity_outlier_lines: int | None = None
    n_charge_outlier_lines: int | None = None

    # Risk scores
    max_seed_risk_score: int | None = None
    avg_seed_risk_score: float | None = None
    min_seed_legitimacy_score: int | None = None
    avg_seed_legitimacy_score: float | None = None
    n_high_risk_lines: int | None = None
    n_state_peer_lines: int | None = None
    risk_legitimacy_gap: int | None = None
    frac_volume_outlier_lines: float | None = None
    charge_cv: float | None = None

    # Computed
    risk_band: RiskBand | None = None


class ProviderListResponse(BaseModel):
    data: list[ProviderSummary]
    meta: PaginationMeta


class ProviderScoreDetails(BaseModel):
    """Hybrid score summary for a provider detail view."""

    npi: str
    explainable_risk_score: int | None = Field(default=None, ge=0, le=100)
    explainable_risk_band: RiskBand | None = None
    anomaly_score: float | None = Field(default=None, ge=0, le=100)
    ml_suspicion_max: float | None = Field(default=None, ge=0, le=100)
    ml_suspicion_avg: float | None = Field(default=None, ge=0, le=100)
    hybrid_composite_max: float | None = Field(default=None, ge=0, le=100)
    hybrid_composite_avg: float | None = Field(default=None, ge=0, le=100)
    hybrid_risk_label: Literal["low", "medium", "high", "critical"] | None = None
    service_line_scored_count: int = 0
    model_name: str | None = None
    model_version: str | None = None


# ---------------------------------------------------------------------------
# Claim / service case schemas
# ---------------------------------------------------------------------------


class Claim(BaseModel):
    """Single provider-service case row."""

    case_id: str
    npi: str
    provider_last_org_name: str | None = None
    provider_first_name: str | None = None
    provider_credentials: str | None = None
    provider_entity_code: str | None = None
    provider_city: str | None = None
    provider_state: str | None = None
    provider_zip5: str | None = None
    provider_type: str | None = None
    medicare_participating_ind: str | None = None
    hcpcs_cd: str
    hcpcs_desc: str | None = None
    place_of_service: str | None = None

    # Volume
    tot_benes: float | None = None
    tot_srvcs: float | None = None
    tot_bene_day_srvcs: float | None = None

    # Charges
    avg_submitted_charge: float | None = None
    avg_medicare_allowed_amt: float | None = None
    avg_medicare_payment_amt: float | None = None
    estimated_case_payment_amt: float | None = None

    # Ratios
    services_per_bene: float | None = None
    submitted_to_allowed_ratio: float | None = None
    payment_to_allowed_ratio: float | None = None

    # Peer comparison
    peer_scope: str | None = None
    peer_case_count: int | None = None
    peer_avg_tot_srvcs: float | None = None
    service_volume_peer_z: float | None = None
    services_per_bene_peer_z: float | None = None
    submitted_to_allowed_peer_z: float | None = None
    payment_peer_z: float | None = None

    # Seed scores
    seed_risk_score: int | None = None
    seed_legitimacy_score: int | None = None
    seed_case_label: str | None = None
    seed_risk_reasons: str | None = None
    seed_legitimacy_reasons: str | None = None


class ClaimListResponse(BaseModel):
    data: list[Claim]
    meta: PaginationMeta


class ClaimScoreDetails(BaseModel):
    """Hybrid score summary for a claim or investigation detail view."""

    case_id: str
    npi: str
    explainable_risk_score: int | None = Field(default=None, ge=0, le=100)
    explainable_risk_band: RiskBand | None = None
    anomaly_score: float | None = Field(default=None, ge=0, le=100)
    ml_predicted_probability: float | None = Field(default=None, ge=0, le=100)
    hybrid_composite_score: float | None = Field(default=None, ge=0, le=100)
    hybrid_risk_label: Literal["low", "medium", "high", "critical"] | None = None
    model_name: str | None = None
    model_version: str | None = None


# ---------------------------------------------------------------------------
# Scoring schemas
# ---------------------------------------------------------------------------


class Signal(BaseModel):
    """Individual risk or legitimacy signal."""

    name: str
    category: str = Field(description="e.g. volume, charge, peer, enrollment")
    direction: str = Field(description="risk or legitimacy")
    value: float | None = None
    threshold: float | None = None
    description: str


class RadarDimension(BaseModel):
    """Single axis on the provider risk radar chart."""

    dimension: str
    provider: float = Field(ge=0, le=100, description="Provider value (0-100 scale)")
    peer: float = Field(default=50, ge=0, le=100, description="Peer baseline (always 50)")


class RadarResponse(BaseModel):
    """Radar chart data for a provider's risk profile."""

    npi: str
    dimensions: list[RadarDimension]


class ScoreRequest(BaseModel):
    """Input for on-the-fly scoring."""

    npi: str
    hcpcs_cd: str | None = None
    tot_srvcs: float | None = None
    avg_submitted_charge: float | None = None


class ScoreResult(BaseModel):
    """Scoring engine output."""

    npi: str
    risk_score: int = Field(ge=0, le=100)
    legitimacy_score: int = Field(ge=0, le=100)
    risk_band: RiskBand
    signals: list[Signal] = []
    narrative: str | None = None
    anomaly_score: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Isolation forest anomaly score (0-100, higher = more anomalous)",
    )


class ScoreV2Result(ScoreResult):
    """V2 scoring output with weak-supervised and composite scoring."""

    ml_predicted_probability: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Weakly supervised fraud probability (0-100, higher = more suspicious)",
    )
    composite_score: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Composite hybrid risk score combining rules, anomaly, context, and ML output.",
    )
    composite_risk_label: Literal["low", "medium", "high", "critical"] | None = Field(
        default=None,
        description="Composite risk band derived from the hybrid score.",
    )


# ---------------------------------------------------------------------------
# Claim Simulation schemas
# ---------------------------------------------------------------------------


class ClaimSimulationRequest(BaseModel):
    """Input for real-time single-claim scoring."""

    npi: str = Field(description="Provider NPI")
    hcpcs_cd: str = Field(description="HCPCS procedure code")
    submitted_charge: float = Field(gt=0, description="Submitted charge amount in USD")
    num_services: int = Field(gt=0, description="Number of services on this claim")
    num_benes: int = Field(gt=0, description="Number of beneficiaries")
    place_of_service: str | None = Field(
        default=None, description="Place of service code (optional)"
    )


class PeerComparisonStats(BaseModel):
    """Provider value vs peer baseline for a single metric."""

    metric: str = Field(description="e.g. submitted_charge, services_per_bene")
    provider_value: float
    peer_mean: float
    z_score: float
    percentile: float | None = Field(
        default=None, ge=0, le=100, description="Provider percentile among peers"
    )
    peer_count: int = Field(description="Number of peers in comparison group")


class ClaimSimulationResult(BaseModel):
    """Output from real-time claim scoring."""

    npi: str
    hcpcs_cd: str
    risk_score: int = Field(ge=0, le=100)
    risk_band: RiskBand
    recommendation: Recommendation
    signals: list[Signal] = []
    peer_comparisons: list[PeerComparisonStats] = []
    provider_name: str | None = None
    provider_type: str | None = None
    state: str | None = None
    narrative: str | None = Field(default=None, description="AI-generated verdict explanation")
    anomaly_score: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Isolation forest anomaly score (0-100, higher = more anomalous)",
    )


class ClaimSimulationV2Result(ClaimSimulationResult):
    """V2 output for real-time single-claim scoring with ML probability."""

    ml_predicted_probability: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Weakly supervised fraud probability (0-100, higher = more suspicious)",
    )


# ---------------------------------------------------------------------------
# Chat schemas
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


class ChatResponse(BaseModel):
    answer: str
    sql: str | None = Field(default=None, description="Generated SQL (if text-to-SQL was used)")
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, object]] = Field(default_factory=list)
    row_count: int = 0
    duration_ms: int = 0
    chart_spec: dict[str, object] | None = Field(
        default=None,
        description="Recharts-compatible chart spec (bar/line/pie) when data is chart-worthy",
    )


# ---------------------------------------------------------------------------
# Dashboard schemas
# ---------------------------------------------------------------------------


class RiskDistribution(BaseModel):
    high_risk: int
    review: int
    stable: int


class DashboardStats(BaseModel):
    total_providers: int
    total_cases: int
    risk_distribution: RiskDistribution
    top_providers: list[ProviderSummary]


class HeatmapEntry(BaseModel):
    state: str
    provider_count: int
    avg_risk_score: float
    flagged_count: int


class HeatmapResponse(BaseModel):
    data: list[HeatmapEntry]


# ---------------------------------------------------------------------------
# Fairness schemas
# ---------------------------------------------------------------------------


class CohortFairness(BaseModel):
    """Flagging rate and parity metrics for a single cohort."""

    cohort: str
    provider_count: int
    flagged_count: int
    flagging_rate: float
    is_outlier: bool = Field(description="True if > 2 sigma above mean flagging rate")


class RevocationImpact(BaseModel):
    """Impact of the revocation signal on fairness metrics."""

    overall_flagging_rate_with: float = Field(description="Flagging rate with revocation signal")
    overall_flagging_rate_without: float = Field(
        description="Flagging rate without revocation signal"
    )
    flagging_rate_delta: float = Field(
        description="without - with: negative means revocation signal increases flagging"
    )
    disparate_impact_with: float | None = None
    disparate_impact_without: float | None = None


class FairnessReport(BaseModel):
    by_state: list[CohortFairness]
    by_specialty: list[CohortFairness]
    overall_flagging_rate: float
    statistical_parity_diff: float | None = None
    disparate_impact_ratio: float | None = None
    revocation_impact: RevocationImpact | None = Field(
        default=None,
        description="Impact analysis of revocation signal on fairness (included when blind=true)",
    )


# ---------------------------------------------------------------------------
# Network Risk
# ---------------------------------------------------------------------------


class NetworkNeighbor(BaseModel):
    """A provider co-located or co-org with the target."""

    npi: str
    provider_name: str | None = None
    provider_type: str | None = None
    state: str | None = None
    risk_score: int | None = None
    revoked: bool = False


class NetworkRiskResponse(BaseModel):
    """Network risk context for a provider."""

    npi: str
    zip5: str | None = None
    same_zip_flagged: list[NetworkNeighbor] = Field(
        default_factory=list,
        description="Flagged providers in the same zip code",
    )
    same_org_flagged: list[NetworkNeighbor] = Field(
        default_factory=list,
        description="Flagged providers with the same organization name",
    )
    zip_risk_summary: dict[str, Any] | None = Field(
        default=None,
        description="Aggregate risk stats for the provider's zip code",
    )


# ---------------------------------------------------------------------------
# Evidence Graph
# ---------------------------------------------------------------------------


class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphResponse(BaseModel):
    npi: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# ---------------------------------------------------------------------------
# Case Actions (Investigation Workflow)
# ---------------------------------------------------------------------------


class CaseAction(StrEnum):
    approved = "APPROVED"
    flagged = "FLAGGED"
    denied = "DENIED"
    escalated = "ESCALATED"


class CaseActionRequest(BaseModel):
    action: CaseAction
    notes: str | None = Field(default=None, max_length=1000)


class CaseActionRecord(BaseModel):
    id: int
    case_id: str
    npi: str
    action: CaseAction
    notes: str | None = None
    analyst_id: str
    created_at: str


class CaseActionResponse(BaseModel):
    case_id: str
    action: CaseAction
    message: str


class CaseActionsListResponse(BaseModel):
    case_id: str
    actions: list[CaseActionRecord]
    current_status: CaseAction | None = None


# ---------------------------------------------------------------------------
# Validation Report
# ---------------------------------------------------------------------------


class DetectionByReason(BaseModel):
    """Detection stats for a single revocation reason code."""

    reason: str
    count: int
    detected: int
    rate: float


class ValidationReport(BaseModel):
    """Retrospective validation results: detection rate on revoked providers."""

    overall_detection_rate: float = Field(
        description="Fraction of revoked providers flagged by behavioral signals alone"
    )
    total_revoked_providers: int
    total_revoked_cases: int
    detection_by_reason: list[DetectionByReason]
    baseline_flagging_rate: float = Field(
        description="Fraction of non-revoked providers that were also flagged"
    )
    methodology: str


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    full_name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ---------------------------------------------------------------------------
# Explainability
# ---------------------------------------------------------------------------


class FeatureContribution(BaseModel):
    name: str
    contribution: float
    actual_value: float
    direction: str  # "risk" | "protective" | "neutral"


class ExplainResponse(BaseModel):
    npi: str
    anomaly_score: float | None = None
    top_features: list[FeatureContribution] = []


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    database: str
    graph: str = "unavailable"
    version: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def risk_band_from_score(score: int | None) -> RiskBand | None:
    if score is None:
        return None
    if score >= HIGH_RISK_SCORE_THRESHOLD:
        return RiskBand.high_risk
    if score > STABLE_RISK_CEILING:
        return RiskBand.review
    return RiskBand.stable
