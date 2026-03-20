"""Tests for retrospective validation logic."""

from __future__ import annotations

from src.validation.retrospective import blind_score_row, original_score_row


def _revoked_case(**overrides: object) -> dict:
    """A revoked provider with outlier billing patterns."""
    row: dict = {
        "npi": "1234567890",
        "present_in_2025_enrollment_file": 1,
        "present_in_2026_revocation_file": 1,
        "medicare_participating_ind": "Y",
        "peer_case_count": 30,
        "service_volume_peer_z": 4.0,
        "services_per_bene_peer_z": 3.5,
        "submitted_to_allowed_peer_z": 0.5,
        "payment_peer_z": 0.5,
        "peer_avg_tot_srvcs": 150.0,
        "provider_total_benes": 200.0,
    }
    row.update(overrides)
    return row


class TestBlindScoring:
    def test_blind_removes_revocation_risk(self):
        row = _revoked_case()
        original = original_score_row(row)
        blind = blind_score_row(row)
        # Blind score should have LESS risk (no +25 revocation)
        assert blind["blind_risk"] < original["original_risk"]

    def test_blind_adds_no_revocation_legitimacy(self):
        row = _revoked_case()
        original = original_score_row(row)
        blind = blind_score_row(row)
        # Blind score should have MORE legitimacy (gains +15 no_revocation)
        assert blind["blind_legitimacy"] > original["original_legitimacy"]

    def test_outlier_still_detected_blind(self):
        """Provider with extreme z-scores should still be flagged even blind."""
        row = _revoked_case(
            service_volume_peer_z=6.0,
            services_per_bene_peer_z=6.0,
            submitted_to_allowed_peer_z=6.0,
            payment_peer_z=6.0,
            provider_total_benes=30.0,
            medicare_participating_ind="N",
            present_in_2025_enrollment_file=0,
        )
        blind = blind_score_row(row)
        # Extreme outlier should still flag as high_risk or review
        assert blind["blind_label"] in ("high_risk", "review")

    def test_normal_revoked_becomes_stable_blind(self):
        """Provider with normal billing but revoked should become stable blind."""
        row = _revoked_case(
            service_volume_peer_z=0.3,
            services_per_bene_peer_z=0.2,
            submitted_to_allowed_peer_z=0.1,
            payment_peer_z=0.1,
        )
        blind = blind_score_row(row)
        # Normal billing patterns → stable when revocation removed
        assert blind["blind_label"] == "stable"
