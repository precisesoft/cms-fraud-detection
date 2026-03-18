"""Score computation — sums fired signals into risk/legitimacy scores and a case label."""

from __future__ import annotations

from dataclasses import dataclass

from src.scoring.extract import FiredSignal, extract_signals
from src.scoring.taxonomy import (
    SCORE_CAP,
    CaseLabel,
    SignalDirection,
    label_case,
)


@dataclass(frozen=True)
class ScoreCard:
    """Result of scoring a single case."""

    risk_score: int
    legitimacy_score: int
    case_label: CaseLabel
    signals: tuple[FiredSignal, ...]


def score_case(case: dict) -> ScoreCard:
    """Score a provider_service_cases row end-to-end.

    Extracts signals, sums points by direction, caps at SCORE_CAP,
    and assigns a case label.
    """
    fired = extract_signals(case)
    risk, legitimacy = _sum_scores(fired)
    return ScoreCard(
        risk_score=risk,
        legitimacy_score=legitimacy,
        case_label=label_case(risk, legitimacy),
        signals=tuple(fired),
    )


def _sum_scores(signals: list[FiredSignal]) -> tuple[int, int]:
    """Sum points by direction and cap at SCORE_CAP."""
    risk = 0
    legitimacy = 0
    for s in signals:
        if s.signal.direction == SignalDirection.risk:
            risk += s.points
        else:
            legitimacy += s.points
    return min(risk, SCORE_CAP), min(legitimacy, SCORE_CAP)
