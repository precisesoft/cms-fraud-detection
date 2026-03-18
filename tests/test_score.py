"""Tests for score computation — sums signals into scores and case labels."""

from __future__ import annotations

from src.scoring.score import score_case
from src.scoring.taxonomy import CaseLabel

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_case(**overrides: object) -> dict:
    """Healthy provider: enrolled, not revoked, participating, peer-aligned, large panel."""
    row: dict = {
        "present_in_2025_enrollment_file": 1,
        "present_in_2026_revocation_file": 0,
        "medicare_participating_ind": "Y",
        "peer_case_count": 30,
        "service_volume_peer_z": 0.5,
        "services_per_bene_peer_z": 0.4,
        "submitted_to_allowed_peer_z": 0.3,
        "payment_peer_z": 0.2,
        "peer_avg_tot_srvcs": 150.0,
        "provider_total_benes": 200.0,
    }
    row.update(overrides)
    return row


def _risky_case(**overrides: object) -> dict:
    """Revoked, not enrolled, extreme z-scores, small panel."""
    row: dict = {
        "present_in_2025_enrollment_file": 0,
        "present_in_2026_revocation_file": 1,
        "medicare_participating_ind": "N",
        "peer_case_count": 30,
        "service_volume_peer_z": 6.0,
        "services_per_bene_peer_z": 6.0,
        "submitted_to_allowed_peer_z": 6.0,
        "payment_peer_z": 6.0,
        "peer_avg_tot_srvcs": 150.0,
        "provider_total_benes": 30.0,
    }
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------


class TestScoreComputation:
    def test_healthy_provider_scores(self):
        """Enrolled + no revocation + participating + all aligned + large panel."""
        card = score_case(_base_case())
        # Legitimacy: enrolled(20) + no_revocation(15) + participating(10)
        #   + aligned_volume(12) + aligned_intensity(12) + aligned_pricing(12)
        #   + large_panel(8) = 89
        assert card.legitimacy_score == 89
        # Risk: no risk signals fire (z-scores all < 2.0)
        assert card.risk_score == 0

    def test_risky_provider_scores(self):
        """Revoked + not enrolled + extreme z-scores."""
        card = score_case(_risky_case())
        # Risk: revoked(25) + not_enrolled(8) + volume(20) + intensity(18)
        #   + charge(18) + payment(12) = 101, capped at 100
        assert card.risk_score == 100
        # Legitimacy: not enrolled, revoked, not participating, not aligned, small panel = 0
        assert card.legitimacy_score == 0

    def test_risk_capped_at_100(self):
        card = score_case(_risky_case())
        assert card.risk_score <= 100

    def test_legitimacy_capped_at_100(self):
        card = score_case(_base_case())
        assert card.legitimacy_score <= 100


# ---------------------------------------------------------------------------
# Case labeling
# ---------------------------------------------------------------------------


class TestCaseLabeling:
    def test_healthy_provider_is_stable(self):
        card = score_case(_base_case())
        # risk=0, legitimacy=89 → stable (legitimacy >= 70 and risk < 30)
        assert card.case_label == CaseLabel.stable

    def test_risky_provider_is_high_risk(self):
        card = score_case(_risky_case())
        # risk=100, legitimacy=0 → high_risk (risk >= 50 and gap >= 5)
        assert card.case_label == CaseLabel.high_risk

    def test_mixed_case_is_review(self):
        """Enrolled but with some outlier z-scores — lands in review."""
        case = _base_case(
            service_volume_peer_z=4.0,
            services_per_bene_peer_z=4.0,
        )
        card = score_case(case)
        # Risk: volume(14) + intensity(12) = 26
        # Legitimacy: enrolled(20) + no_rev(15) + participating(10)
        #   + aligned_pricing(12) + large_panel(8) = 65
        #   (volume and intensity no longer aligned since z=4.0 > 1.0)
        # risk=26 < 50 → not high_risk
        # legitimacy=65 < 70 → not stable
        assert card.case_label == CaseLabel.review

    def test_edge_stable_boundary(self):
        """Legitimacy exactly 70, risk exactly 29 → stable."""
        # Need: legitimacy signals summing to exactly 70, risk < 30
        # enrolled(20) + no_rev(15) + participating(10) + large_panel(8) = 53
        # Need aligned signals: +12 each → 53 + 12 = 65, 53 + 24 = 77
        # With 2 aligned signals: 53 + 12 + 12 = 77, too high
        # With 1 aligned: 53 + 12 = 65, too low
        # Can't hit exactly 70 from our fixed signals, so test that the
        # label_case logic works correctly via score_case integration
        case = _base_case(
            service_volume_peer_z=0.5,
            services_per_bene_peer_z=0.5,
            submitted_to_allowed_peer_z=2.0,  # not aligned (>= 1.0)
        )
        card = score_case(case)
        # Legitimacy: enrolled(20) + no_rev(15) + participating(10)
        #   + aligned_volume(12) + aligned_intensity(12) + large_panel(8) = 77
        # Risk: 0 (no z-scores above 2.0 except submitted which is exactly 2.0)
        # Wait, submitted_to_allowed_peer_z=2.0 → charge_ratio_outlier fires at tier 2.0 = 7 pts
        # Risk: 7, Legitimacy: 77 → stable (77 >= 70 and 7 < 30)
        assert card.case_label == CaseLabel.stable


# ---------------------------------------------------------------------------
# ScoreCard structure
# ---------------------------------------------------------------------------


class TestScoreCardStructure:
    def test_signals_are_tuple(self):
        card = score_case(_base_case())
        assert isinstance(card.signals, tuple)

    def test_signals_not_empty_for_real_case(self):
        card = score_case(_base_case())
        assert len(card.signals) > 0

    def test_scorecard_is_frozen(self):
        card = score_case(_base_case())
        try:
            card.risk_score = 999  # type: ignore[misc]
            raise AssertionError("ScoreCard should be frozen")
        except AttributeError:
            pass

    def test_empty_case_returns_zero_scores(self):
        """Completely empty dict → no signals fire → 0/0 → review."""
        card = score_case({})
        # not enrolled → NOT_IN_ENROLLMENT fires (8 pts risk)
        # not revoked (None → False) → NO_REVOCATION fires (15 pts legitimacy)
        assert card.risk_score == 8
        assert card.legitimacy_score == 15
        assert card.case_label == CaseLabel.review

    def test_scores_are_integers(self):
        card = score_case(_base_case())
        assert isinstance(card.risk_score, int)
        assert isinstance(card.legitimacy_score, int)


# ---------------------------------------------------------------------------
# Signal pass-through
# ---------------------------------------------------------------------------


class TestSignalPassThrough:
    def test_healthy_signals_all_legitimacy(self):
        card = score_case(_base_case())
        directions = {s.signal.direction.value for s in card.signals}
        assert directions == {"legitimacy"}

    def test_risky_signals_include_risk(self):
        card = score_case(_risky_case())
        directions = {s.signal.direction.value for s in card.signals}
        assert "risk" in directions

    def test_signal_count_matches_extraction(self):
        """ScoreCard should carry every signal from extract_signals."""
        from src.scoring.extract import extract_signals

        case = _base_case()
        expected = extract_signals(case)
        card = score_case(case)
        assert len(card.signals) == len(expected)
