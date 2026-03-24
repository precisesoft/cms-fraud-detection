"""Validation endpoint — retrospective detection rate statistics."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter

from src.api.schemas import DetectionByReason, ProviderLevelBreakdown, ValidationReport

router = APIRouter(prefix="/validation", tags=["validation"])

_DATA_FILE = Path(__file__).parents[3] / "data" / "validation" / "retrospective_results.json"

_METHODOLOGY = (
    "Retrospective blind validation: revocation labels were withheld from the scoring "
    "engine. Providers were scored on behavioral signals only (volume, charge, peer "
    "z-scores, concentration). A provider is 'detected' if its blind risk score places "
    "it in the review or high_risk band (score >= 31). Results cover 335 revoked "
    "providers and 10,282 total providers in the 2024 Medicare Part B dataset."
)


@lru_cache(maxsize=1)
def _load_report() -> ValidationReport:
    """Load and parse retrospective_results.json once at first request."""
    with _DATA_FILE.open() as f:
        data = json.load(f)

    summary = data["summary"]
    non_revoked = data["non_revoked_baseline"]
    by_reason_raw = data["by_revocation_reason"]

    # baseline flagging rate: (high_risk + review) / total non-revoked
    non_revoked_total = sum(non_revoked.values())
    non_revoked_flagged = non_revoked.get("high_risk", 0) + non_revoked.get("review", 0)
    baseline_rate = non_revoked_flagged / non_revoked_total if non_revoked_total > 0 else 0.0

    detection_by_reason = [
        DetectionByReason(
            reason=reason,
            count=stats["total"],
            detected=stats["total"] - stats.get("stable", 0),
            rate=round(stats["detection_rate"], 4),
        )
        for reason, stats in by_reason_raw.items()
    ]
    # Sort descending by count so the most-impactful reasons appear first
    detection_by_reason.sort(key=lambda r: r.count, reverse=True)

    # Provider-level blind label breakdown
    prov = data.get("provider_level", {}).get("blind_labels", {})
    provider_level = ProviderLevelBreakdown(
        high_risk=prov.get("high_risk", 0),
        review=prov.get("review", 0),
        stable=prov.get("stable", 0),
    )

    # Detection lift: revoked flagging rate / non-revoked flagging rate
    detection_lift = (
        round(summary["npi_detection_rate"] / baseline_rate, 1) if baseline_rate > 0 else 0.0
    )

    return ValidationReport(
        overall_detection_rate=round(summary["npi_detection_rate"], 4),
        total_revoked_providers=summary["total_revoked_npis"],
        total_revoked_cases=summary["total_revoked_cases"],
        detection_by_reason=detection_by_reason,
        baseline_flagging_rate=round(baseline_rate, 4),
        avg_blind_risk_revoked=summary.get("avg_blind_risk_score_revoked", 0.0),
        avg_risk_non_revoked=summary.get("avg_risk_score_non_revoked", 0.0),
        detection_lift=detection_lift,
        provider_level=provider_level,
        methodology=_METHODOLOGY,
    )


@router.get("", response_model=ValidationReport)
async def get_validation() -> ValidationReport:
    """Return retrospective detection rate statistics.

    Scores were computed without revocation labels to prove the system
    detects fraud patterns from billing behavior alone.
    """
    return _load_report()
