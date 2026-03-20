"""Signal taxonomy and weights — single source of truth for all scoring logic.

Every risk and legitimacy signal is defined here with its category, thresholds,
point allocations, and human-readable description. The scoring engine, API, and
explainability layer all import from this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCORE_CAP = 100
MIN_PEER_COUNT = 25

# Case-label thresholds
HIGH_RISK_SCORE_THRESHOLD = 50
HIGH_RISK_GAP = 5  # risk must exceed legitimacy by this much
STABLE_LEGITIMACY_THRESHOLD = 70
STABLE_RISK_CEILING = 30


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SignalDirection(StrEnum):
    risk = "risk"
    legitimacy = "legitimacy"


class SignalCategory(StrEnum):
    enrollment = "enrollment"
    volume = "volume"
    charge = "charge"
    peer = "peer"


class CaseLabel(StrEnum):
    high_risk = "high_risk"
    review = "review"
    stable = "stable"


# ---------------------------------------------------------------------------
# Z-score tier
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ZTier:
    """A z-score threshold and the points awarded when crossed."""

    z_min: float
    points: int


# ---------------------------------------------------------------------------
# Signal definition
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SignalDef:
    """Immutable signal definition."""

    name: str
    category: SignalCategory
    direction: SignalDirection
    description: str
    # For boolean signals (enrollment checks)
    points: int | None = None
    # For z-score signals (peer comparison) — ordered highest tier first
    z_tiers: tuple[ZTier, ...] = ()
    # Z-score threshold for the reason string to fire
    z_reason_threshold: float | None = None
    # For threshold-based signals (e.g., large patient panel)
    threshold: float | None = None
    # Whether this signal requires a peer group
    requires_peers: bool = False


# ---------------------------------------------------------------------------
# Risk signals
# ---------------------------------------------------------------------------

REVOKED_PROVIDER = SignalDef(
    name="revoked_provider",
    category=SignalCategory.enrollment,
    direction=SignalDirection.risk,
    description="Provider appears in 2026 revocation file",
    points=25,
)

NOT_IN_ENROLLMENT = SignalDef(
    name="not_in_current_enrollment_file",
    category=SignalCategory.enrollment,
    direction=SignalDirection.risk,
    description="Provider not found in current (2025) enrollment file",
    points=8,
)

SERVICE_VOLUME_OUTLIER = SignalDef(
    name="service_volume_outlier",
    category=SignalCategory.peer,
    direction=SignalDirection.risk,
    description="Total services significantly above peer average",
    z_tiers=(ZTier(5.0, 20), ZTier(3.0, 14), ZTier(2.0, 8)),
    z_reason_threshold=3.0,
    requires_peers=True,
)

SERVICE_INTENSITY_OUTLIER = SignalDef(
    name="service_intensity_outlier",
    category=SignalCategory.peer,
    direction=SignalDirection.risk,
    description="Services per beneficiary significantly above peer average",
    z_tiers=(ZTier(5.0, 18), ZTier(3.0, 12), ZTier(2.0, 7)),
    z_reason_threshold=3.0,
    requires_peers=True,
)

CHARGE_RATIO_OUTLIER = SignalDef(
    name="charge_ratio_outlier",
    category=SignalCategory.peer,
    direction=SignalDirection.risk,
    description="Submitted-to-allowed charge ratio significantly above peer average",
    z_tiers=(ZTier(5.0, 18), ZTier(3.0, 12), ZTier(2.0, 7)),
    z_reason_threshold=3.0,
    requires_peers=True,
)

PAYMENT_OUTLIER = SignalDef(
    name="payment_outlier",
    category=SignalCategory.peer,
    direction=SignalDirection.risk,
    description="Average payment significantly above peer average",
    z_tiers=(ZTier(5.0, 12), ZTier(3.0, 8), ZTier(2.0, 5)),
    z_reason_threshold=3.0,
    requires_peers=True,
)

RISK_SIGNALS: tuple[SignalDef, ...] = (
    REVOKED_PROVIDER,
    NOT_IN_ENROLLMENT,
    SERVICE_VOLUME_OUTLIER,
    SERVICE_INTENSITY_OUTLIER,
    CHARGE_RATIO_OUTLIER,
    PAYMENT_OUTLIER,
)

# ---------------------------------------------------------------------------
# Legitimacy signals
# ---------------------------------------------------------------------------

ENROLLED_CURRENT = SignalDef(
    name="present_in_current_enrollment_file",
    category=SignalCategory.enrollment,
    direction=SignalDirection.legitimacy,
    description="Provider found in current (2025) enrollment file",
    points=20,
)

NO_REVOCATION = SignalDef(
    name="no_revocation_match",
    category=SignalCategory.enrollment,
    direction=SignalDirection.legitimacy,
    description="Provider has no revocation on record",
    points=15,
)

MEDICARE_PARTICIPATING = SignalDef(
    name="medicare_participating",
    category=SignalCategory.enrollment,
    direction=SignalDirection.legitimacy,
    description="Provider accepts Medicare assignment",
    points=10,
)

PEER_ALIGNED_VOLUME = SignalDef(
    name="peer_aligned_volume",
    category=SignalCategory.peer,
    direction=SignalDirection.legitimacy,
    description="Service volume within one standard deviation of peers",
    threshold=1.0,  # |z| < 1.0
    points=12,
    requires_peers=True,
)

PEER_ALIGNED_INTENSITY = SignalDef(
    name="peer_aligned_intensity",
    category=SignalCategory.peer,
    direction=SignalDirection.legitimacy,
    description="Services per beneficiary within one standard deviation of peers",
    threshold=1.0,
    points=12,
    requires_peers=True,
)

PEER_ALIGNED_PRICING = SignalDef(
    name="peer_aligned_pricing",
    category=SignalCategory.peer,
    direction=SignalDirection.legitimacy,
    description="Charge ratio within one standard deviation of peers",
    threshold=1.0,
    points=12,
    requires_peers=True,
)

LARGE_PATIENT_PANEL = SignalDef(
    name="large_patient_panel",
    category=SignalCategory.volume,
    direction=SignalDirection.legitimacy,
    description="Provider serves 100+ Medicare beneficiaries",
    threshold=100.0,
    points=8,
)

LEGITIMACY_SIGNALS: tuple[SignalDef, ...] = (
    ENROLLED_CURRENT,
    NO_REVOCATION,
    MEDICARE_PARTICIPATING,
    PEER_ALIGNED_VOLUME,
    PEER_ALIGNED_INTENSITY,
    PEER_ALIGNED_PRICING,
    LARGE_PATIENT_PANEL,
)

# ---------------------------------------------------------------------------
# All signals
# ---------------------------------------------------------------------------

ALL_SIGNALS: tuple[SignalDef, ...] = RISK_SIGNALS + LEGITIMACY_SIGNALS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def points_for_z(signal: SignalDef, z: float) -> int:
    """Return points awarded for a z-score signal given the observed z value."""
    for tier in signal.z_tiers:
        if z >= tier.z_min:
            return tier.points
    return 0


def z_fires_reason(signal: SignalDef, z: float) -> bool:
    """Return True if the z-score crosses the threshold to emit a reason string."""
    if signal.z_reason_threshold is None:
        return False
    return z >= signal.z_reason_threshold


def label_case(risk_score: int, legitimacy_score: int) -> CaseLabel:
    """Apply case-label rules to a scored case."""
    if risk_score >= HIGH_RISK_SCORE_THRESHOLD and risk_score >= legitimacy_score + HIGH_RISK_GAP:
        return CaseLabel.high_risk
    if legitimacy_score >= STABLE_LEGITIMACY_THRESHOLD and risk_score < STABLE_RISK_CEILING:
        return CaseLabel.stable
    return CaseLabel.review


def max_possible_risk() -> int:
    """Theoretical max risk score (before cap)."""
    total = 0
    for s in RISK_SIGNALS:
        if s.points is not None:
            total += s.points
        elif s.z_tiers:
            total += s.z_tiers[0].points  # highest tier
    return min(total, SCORE_CAP)


def max_possible_legitimacy() -> int:
    """Theoretical max legitimacy score (before cap)."""
    total = sum(s.points for s in LEGITIMACY_SIGNALS if s.points is not None)
    return min(total, SCORE_CAP)
