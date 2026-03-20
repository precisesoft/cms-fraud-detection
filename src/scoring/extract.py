"""Signal extraction — maps a case row to fired signals with points and reasons."""

from __future__ import annotations

from dataclasses import dataclass

from src.scoring.taxonomy import (
    CHARGE_RATIO_OUTLIER,
    CONCENTRATION_OUTLIER,
    ENROLLED_CURRENT,
    LARGE_PATIENT_PANEL,
    MEDICARE_PARTICIPATING,
    MIN_PEER_COUNT,
    NO_REVOCATION,
    NOT_IN_ENROLLMENT,
    PAYMENT_OUTLIER,
    PEER_ALIGNED_INTENSITY,
    PEER_ALIGNED_PRICING,
    PEER_ALIGNED_VOLUME,
    REVOKED_PROVIDER,
    SERVICE_INTENSITY_OUTLIER,
    SERVICE_VOLUME_OUTLIER,
    SignalDef,
    points_for_z,
    z_fires_reason,
)


@dataclass(frozen=True)
class FiredSignal:
    """A signal that fired for a specific case, carrying points and context."""

    signal: SignalDef
    points: int
    value: float | None = None
    peer_baseline: float | None = None
    reason: str | None = None


# ---------------------------------------------------------------------------
# Column-to-signal mapping for z-score risk signals
# ---------------------------------------------------------------------------

_Z_RISK_MAP: tuple[tuple[SignalDef, str, str | None], ...] = (
    (SERVICE_VOLUME_OUTLIER, "service_volume_peer_z", "peer_avg_tot_srvcs"),
    (SERVICE_INTENSITY_OUTLIER, "services_per_bene_peer_z", None),
    (CHARGE_RATIO_OUTLIER, "submitted_to_allowed_peer_z", None),
    (PAYMENT_OUTLIER, "payment_peer_z", None),
)

_Z_LEGITIMACY_MAP: tuple[tuple[SignalDef, str], ...] = (
    (PEER_ALIGNED_VOLUME, "service_volume_peer_z"),
    (PEER_ALIGNED_INTENSITY, "services_per_bene_peer_z"),
    (PEER_ALIGNED_PRICING, "submitted_to_allowed_peer_z"),
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_signals(case: dict) -> list[FiredSignal]:
    """Extract all applicable signals from a provider_service_cases row."""
    signals: list[FiredSignal] = []

    _extract_enrollment(case, signals)
    _extract_peer_risk(case, signals)
    _extract_peer_legitimacy(case, signals)
    _extract_large_panel(case, signals)
    _extract_concentration(case, signals)

    return signals


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _extract_enrollment(case: dict, out: list[FiredSignal]) -> None:
    enrolled = bool(case.get("present_in_2025_enrollment_file"))
    revoked = bool(case.get("present_in_2026_revocation_file"))
    participating = case.get("medicare_participating_ind") == "Y"

    # Risk
    if revoked:
        out.append(
            FiredSignal(
                signal=REVOKED_PROVIDER,
                points=REVOKED_PROVIDER.points,  # type: ignore[arg-type]
                reason=REVOKED_PROVIDER.description,
            )
        )
    if not enrolled:
        out.append(
            FiredSignal(
                signal=NOT_IN_ENROLLMENT,
                points=NOT_IN_ENROLLMENT.points,  # type: ignore[arg-type]
                reason=NOT_IN_ENROLLMENT.description,
            )
        )

    # Legitimacy
    if enrolled:
        out.append(
            FiredSignal(
                signal=ENROLLED_CURRENT,
                points=ENROLLED_CURRENT.points,  # type: ignore[arg-type]
                reason=ENROLLED_CURRENT.description,
            )
        )
    if not revoked:
        out.append(
            FiredSignal(
                signal=NO_REVOCATION,
                points=NO_REVOCATION.points,  # type: ignore[arg-type]
                reason=NO_REVOCATION.description,
            )
        )
    if participating:
        out.append(
            FiredSignal(
                signal=MEDICARE_PARTICIPATING,
                points=MEDICARE_PARTICIPATING.points,  # type: ignore[arg-type]
                reason=MEDICARE_PARTICIPATING.description,
            )
        )


def _has_peers(case: dict) -> bool:
    return (case.get("peer_case_count") or 0) >= MIN_PEER_COUNT


def _extract_peer_risk(case: dict, out: list[FiredSignal]) -> None:
    if not _has_peers(case):
        return
    for signal_def, z_col, baseline_col in _Z_RISK_MAP:
        z = case.get(z_col)
        if z is None:
            continue
        pts = points_for_z(signal_def, z)
        if pts > 0:
            reason = signal_def.description if z_fires_reason(signal_def, z) else None
            baseline = case.get(baseline_col) if baseline_col else None
            out.append(
                FiredSignal(
                    signal=signal_def,
                    points=pts,
                    value=z,
                    peer_baseline=baseline,
                    reason=reason,
                )
            )


def _extract_peer_legitimacy(case: dict, out: list[FiredSignal]) -> None:
    if not _has_peers(case):
        return
    for signal_def, z_col in _Z_LEGITIMACY_MAP:
        z = case.get(z_col)
        if z is None:
            continue
        if abs(z) < signal_def.threshold:  # type: ignore[operator]
            out.append(
                FiredSignal(
                    signal=signal_def,
                    points=signal_def.points,  # type: ignore[arg-type]
                    value=z,
                    reason=signal_def.description,
                )
            )


def _extract_large_panel(case: dict, out: list[FiredSignal]) -> None:
    benes = case.get("provider_total_benes") or 0
    if benes >= LARGE_PATIENT_PANEL.threshold:  # type: ignore[operator]
        out.append(
            FiredSignal(
                signal=LARGE_PATIENT_PANEL,
                points=LARGE_PATIENT_PANEL.points,  # type: ignore[arg-type]
                value=float(benes),
                reason=LARGE_PATIENT_PANEL.description,
            )
        )


def _extract_concentration(case: dict, out: list[FiredSignal]) -> None:
    top_share = case.get("top_code_share")
    hhi = case.get("service_hhi")

    # Tiered: top_code_share >= 0.90 → 12pts, >= 0.80 → 8pts, hhi >= 0.50 → 6pts
    if top_share is not None and top_share >= 0.90:
        out.append(
            FiredSignal(
                signal=CONCENTRATION_OUTLIER,
                points=12,
                value=round(float(top_share), 3),
                reason=f"Provider derives {top_share * 100:.0f}% of billing from one code",
            )
        )
    elif top_share is not None and top_share >= 0.80:
        out.append(
            FiredSignal(
                signal=CONCENTRATION_OUTLIER,
                points=8,
                value=round(float(top_share), 3),
                reason=f"Provider derives {top_share * 100:.0f}% of billing from one code",
            )
        )
    elif hhi is not None and hhi >= 0.50:
        out.append(
            FiredSignal(
                signal=CONCENTRATION_OUTLIER,
                points=6,
                value=round(float(hhi), 3),
                reason=f"Billing concentration index (HHI={hhi:.2f}) indicates narrow service mix",
            )
        )
