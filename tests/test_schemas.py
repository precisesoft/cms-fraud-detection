"""Tests for API schema helpers — especially risk_band_from_score boundaries."""

from __future__ import annotations

import pytest

from src.api.schemas import RiskBand, risk_band_from_score


class TestRiskBandFromScore:
    def test_none_returns_none(self):
        assert risk_band_from_score(None) is None

    def test_zero_is_stable(self):
        assert risk_band_from_score(0) == RiskBand.stable

    def test_stable_ceiling_inclusive(self):
        # score == STABLE_RISK_CEILING (30) → stable
        assert risk_band_from_score(30) == RiskBand.stable

    def test_just_above_stable_ceiling_is_review(self):
        # score == 31 → review
        assert risk_band_from_score(31) == RiskBand.review

    def test_high_risk_threshold_is_review(self):
        # score == HIGH_RISK_SCORE_THRESHOLD (50) → review (band is 31-50)
        assert risk_band_from_score(50) == RiskBand.review

    def test_just_above_high_risk_threshold(self):
        # score == 51 → high_risk (band is 51+)
        assert risk_band_from_score(51) == RiskBand.high_risk

    def test_max_score_is_high_risk(self):
        assert risk_band_from_score(100) == RiskBand.high_risk

    def test_mid_review_range(self):
        # score between 31 and 50 → review
        assert risk_band_from_score(40) == RiskBand.review

    @pytest.mark.parametrize("score", [0, 15, 30])
    def test_stable_range(self, score: int):
        assert risk_band_from_score(score) == RiskBand.stable

    @pytest.mark.parametrize("score", [31, 40, 49, 50])
    def test_review_range(self, score: int):
        assert risk_band_from_score(score) == RiskBand.review

    @pytest.mark.parametrize("score", [51, 75, 100])
    def test_high_risk_range(self, score: int):
        assert risk_band_from_score(score) == RiskBand.high_risk
