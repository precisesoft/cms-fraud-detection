"""Tests for the signal taxonomy — the single source of truth for scoring."""

from __future__ import annotations

from src.scoring.taxonomy import (
    ALL_SIGNALS,
    CHARGE_RATIO_OUTLIER,
    LARGE_PATIENT_PANEL,
    LEGITIMACY_SIGNALS,
    RISK_SIGNALS,
    SCORE_CAP,
    SERVICE_VOLUME_OUTLIER,
    CaseLabel,
    SignalDirection,
    label_case,
    max_possible_legitimacy,
    max_possible_risk,
    points_for_z,
    z_fires_reason,
)


class TestSignalDefinitions:
    def test_risk_signal_count(self):
        assert len(RISK_SIGNALS) == 7

    def test_legitimacy_signal_count(self):
        assert len(LEGITIMACY_SIGNALS) == 7

    def test_all_signals_is_union(self):
        assert len(ALL_SIGNALS) == len(RISK_SIGNALS) + len(LEGITIMACY_SIGNALS)

    def test_risk_signals_are_risk(self):
        for s in RISK_SIGNALS:
            assert s.direction == SignalDirection.risk, f"{s.name} should be risk"

    def test_legitimacy_signals_are_legitimacy(self):
        for s in LEGITIMACY_SIGNALS:
            assert s.direction == SignalDirection.legitimacy, f"{s.name} should be legitimacy"

    def test_unique_names(self):
        names = [s.name for s in ALL_SIGNALS]
        assert len(names) == len(set(names)), "Duplicate signal names"

    def test_all_signals_have_descriptions(self):
        for s in ALL_SIGNALS:
            assert s.description, f"{s.name} missing description"

    def test_z_tiers_ordered_descending(self):
        """Z-tiers must be highest first so the scoring loop works."""
        for s in ALL_SIGNALS:
            if s.z_tiers:
                thresholds = [t.z_min for t in s.z_tiers]
                assert thresholds == sorted(thresholds, reverse=True), (
                    f"{s.name} tiers not descending"
                )


class TestPointsForZ:
    def test_highest_tier(self):
        assert points_for_z(SERVICE_VOLUME_OUTLIER, 6.0) == 20

    def test_middle_tier(self):
        assert points_for_z(SERVICE_VOLUME_OUTLIER, 3.5) == 14

    def test_lowest_tier(self):
        assert points_for_z(SERVICE_VOLUME_OUTLIER, 2.5) == 8

    def test_below_all_tiers(self):
        assert points_for_z(SERVICE_VOLUME_OUTLIER, 1.5) == 0

    def test_exact_boundary(self):
        assert points_for_z(SERVICE_VOLUME_OUTLIER, 3.0) == 14

    def test_charge_outlier_tiers(self):
        assert points_for_z(CHARGE_RATIO_OUTLIER, 5.0) == 18
        assert points_for_z(CHARGE_RATIO_OUTLIER, 4.0) == 12
        assert points_for_z(CHARGE_RATIO_OUTLIER, 2.0) == 7
        assert points_for_z(CHARGE_RATIO_OUTLIER, 1.0) == 0


class TestZFiresReason:
    def test_fires_above_threshold(self):
        assert z_fires_reason(SERVICE_VOLUME_OUTLIER, 3.5) is True

    def test_does_not_fire_below(self):
        assert z_fires_reason(SERVICE_VOLUME_OUTLIER, 2.5) is False

    def test_fires_at_exact_threshold(self):
        assert z_fires_reason(SERVICE_VOLUME_OUTLIER, 3.0) is True

    def test_no_threshold_returns_false(self):
        assert z_fires_reason(LARGE_PATIENT_PANEL, 5.0) is False


class TestLabelCase:
    def test_high_risk(self):
        assert label_case(risk_score=60, legitimacy_score=40) == CaseLabel.high_risk

    def test_high_risk_requires_gap(self):
        # risk >= 30 but gap < 5 → review, not high_risk
        assert label_case(risk_score=32, legitimacy_score=30) == CaseLabel.review

    def test_stable(self):
        assert label_case(risk_score=5, legitimacy_score=80) == CaseLabel.stable

    def test_stable_requires_low_risk(self):
        # legitimacy >= 70 but risk >= STABLE_RISK_CEILING (25) → review
        assert label_case(risk_score=30, legitimacy_score=75) == CaseLabel.review

    def test_review_is_default(self):
        assert label_case(risk_score=20, legitimacy_score=20) == CaseLabel.review

    def test_edge_high_risk_boundary(self):
        # risk=55, gap=31 → high_risk (threshold is >= 51)
        assert label_case(risk_score=55, legitimacy_score=24) == CaseLabel.high_risk

    def test_edge_below_high_risk_boundary(self):
        # risk=29 is below threshold → review
        assert label_case(risk_score=29, legitimacy_score=20) == CaseLabel.review

    def test_edge_stable_boundary(self):
        # legitimacy=70, risk=9 → stable (risk < STABLE_RISK_CEILING=10)
        assert label_case(risk_score=9, legitimacy_score=70) == CaseLabel.stable


class TestMaxScores:
    def test_max_risk_does_not_exceed_cap(self):
        assert max_possible_risk() <= SCORE_CAP

    def test_max_legitimacy_does_not_exceed_cap(self):
        assert max_possible_legitimacy() <= SCORE_CAP

    def test_max_risk_is_positive(self):
        assert max_possible_risk() > 0

    def test_max_legitimacy_is_positive(self):
        assert max_possible_legitimacy() > 0
