"""Tests for API schema helpers — especially risk_band_from_score boundaries."""

from __future__ import annotations

import pytest

from src.api.schemas import RiskBand, risk_band_from_score
from src.scoring.taxonomy import HIGH_RISK_SCORE_THRESHOLD, STABLE_RISK_CEILING


class TestRiskBandFromScore:
    def test_none_returns_none(self):
        assert risk_band_from_score(None) is None

    def test_zero_is_stable(self):
        assert risk_band_from_score(0) == RiskBand.stable

    def test_stable_ceiling_inclusive(self):
        # score == STABLE_RISK_CEILING → stable
        assert risk_band_from_score(STABLE_RISK_CEILING) == RiskBand.stable

    def test_just_above_stable_ceiling_is_review(self):
        # score == STABLE_RISK_CEILING + 1 → review
        assert risk_band_from_score(STABLE_RISK_CEILING + 1) == RiskBand.review

    def test_high_risk_threshold_minus_one_is_review(self):
        # score == HIGH_RISK_SCORE_THRESHOLD - 1 → review
        assert risk_band_from_score(HIGH_RISK_SCORE_THRESHOLD - 1) == RiskBand.review

    def test_just_above_high_risk_threshold(self):
        # score == HIGH_RISK_SCORE_THRESHOLD → high_risk
        assert risk_band_from_score(HIGH_RISK_SCORE_THRESHOLD) == RiskBand.high_risk

    def test_max_score_is_high_risk(self):
        assert risk_band_from_score(100) == RiskBand.high_risk

    def test_mid_review_range(self):
        # score between STABLE_RISK_CEILING+1 and HIGH_RISK_SCORE_THRESHOLD-1 → review
        mid = (STABLE_RISK_CEILING + HIGH_RISK_SCORE_THRESHOLD) // 2
        assert risk_band_from_score(mid) == RiskBand.review

    @pytest.mark.parametrize("score", [0, 5, STABLE_RISK_CEILING])
    def test_stable_range(self, score: int):
        assert risk_band_from_score(score) == RiskBand.stable

    @pytest.mark.parametrize(
        "score",
        [STABLE_RISK_CEILING + 1, 38, HIGH_RISK_SCORE_THRESHOLD - 1],
    )
    def test_review_range(self, score: int):
        assert risk_band_from_score(score) == RiskBand.review

    @pytest.mark.parametrize("score", [HIGH_RISK_SCORE_THRESHOLD, 75, 100])
    def test_high_risk_range(self, score: int):
        assert risk_band_from_score(score) == RiskBand.high_risk
