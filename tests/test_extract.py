"""Tests for signal extraction — maps case rows to fired signals."""

from __future__ import annotations

from src.scoring.extract import FiredSignal, extract_signals
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
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_case(**overrides: object) -> dict:
    """Minimal case row with sane defaults (enrolled, no revocation, has peers)."""
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


def _signal_names(signals: list[FiredSignal]) -> set[str]:
    return {s.signal.name for s in signals}


def _find(signals: list[FiredSignal], name: str) -> FiredSignal | None:
    return next((s for s in signals if s.signal.name == name), None)


# ---------------------------------------------------------------------------
# Enrollment signals
# ---------------------------------------------------------------------------


class TestEnrollmentSignals:
    def test_enrolled_fires_legitimacy(self):
        signals = extract_signals(_base_case())
        assert ENROLLED_CURRENT.name in _signal_names(signals)

    def test_not_enrolled_fires_risk(self):
        signals = extract_signals(_base_case(present_in_2025_enrollment_file=0))
        names = _signal_names(signals)
        assert NOT_IN_ENROLLMENT.name in names
        assert ENROLLED_CURRENT.name not in names

    def test_revoked_fires_risk(self):
        signals = extract_signals(_base_case(present_in_2026_revocation_file=1))
        names = _signal_names(signals)
        assert REVOKED_PROVIDER.name in names
        assert NO_REVOCATION.name not in names

    def test_no_revocation_fires_legitimacy(self):
        signals = extract_signals(_base_case())
        assert NO_REVOCATION.name in _signal_names(signals)

    def test_medicare_participating_fires(self):
        signals = extract_signals(_base_case())
        assert MEDICARE_PARTICIPATING.name in _signal_names(signals)

    def test_medicare_not_participating_skips(self):
        signals = extract_signals(_base_case(medicare_participating_ind="N"))
        assert MEDICARE_PARTICIPATING.name not in _signal_names(signals)

    def test_revoked_points(self):
        signals = extract_signals(_base_case(present_in_2026_revocation_file=1))
        s = _find(signals, REVOKED_PROVIDER.name)
        assert s is not None
        assert s.points == 25

    def test_enrollment_reasons_populated(self):
        signals = extract_signals(_base_case())
        enrolled = _find(signals, ENROLLED_CURRENT.name)
        assert enrolled is not None
        assert enrolled.reason is not None


# ---------------------------------------------------------------------------
# Peer risk signals (z-score based)
# ---------------------------------------------------------------------------


class TestPeerRiskSignals:
    def test_high_volume_z_fires(self):
        signals = extract_signals(_base_case(service_volume_peer_z=5.5))
        s = _find(signals, SERVICE_VOLUME_OUTLIER.name)
        assert s is not None
        assert s.points == 20
        assert s.value == 5.5

    def test_mid_volume_z_fires(self):
        signals = extract_signals(_base_case(service_volume_peer_z=3.5))
        s = _find(signals, SERVICE_VOLUME_OUTLIER.name)
        assert s is not None
        assert s.points == 14

    def test_low_volume_z_fires(self):
        signals = extract_signals(_base_case(service_volume_peer_z=2.5))
        s = _find(signals, SERVICE_VOLUME_OUTLIER.name)
        assert s is not None
        assert s.points == 8

    def test_below_threshold_no_risk(self):
        signals = extract_signals(_base_case(service_volume_peer_z=1.5))
        assert SERVICE_VOLUME_OUTLIER.name not in _signal_names(signals)

    def test_intensity_outlier_fires(self):
        signals = extract_signals(_base_case(services_per_bene_peer_z=4.0))
        s = _find(signals, SERVICE_INTENSITY_OUTLIER.name)
        assert s is not None
        assert s.points == 12

    def test_charge_outlier_fires(self):
        signals = extract_signals(_base_case(submitted_to_allowed_peer_z=6.0))
        s = _find(signals, CHARGE_RATIO_OUTLIER.name)
        assert s is not None
        assert s.points == 18

    def test_payment_outlier_fires(self):
        signals = extract_signals(_base_case(payment_peer_z=3.5))
        s = _find(signals, PAYMENT_OUTLIER.name)
        assert s is not None
        assert s.points == 8

    def test_volume_baseline_captured(self):
        signals = extract_signals(
            _base_case(
                service_volume_peer_z=5.0,
                peer_avg_tot_srvcs=150.0,
            )
        )
        s = _find(signals, SERVICE_VOLUME_OUTLIER.name)
        assert s is not None
        assert s.peer_baseline == 150.0

    def test_reason_fires_above_threshold(self):
        signals = extract_signals(_base_case(service_volume_peer_z=3.5))
        s = _find(signals, SERVICE_VOLUME_OUTLIER.name)
        assert s is not None
        assert s.reason is not None

    def test_reason_none_below_reason_threshold(self):
        """z=2.5 awards points (tier 2.0) but is below z_reason_threshold (3.0)."""
        signals = extract_signals(_base_case(service_volume_peer_z=2.5))
        s = _find(signals, SERVICE_VOLUME_OUTLIER.name)
        assert s is not None
        assert s.reason is None

    def test_none_z_skips_signal(self):
        signals = extract_signals(_base_case(service_volume_peer_z=None))
        assert SERVICE_VOLUME_OUTLIER.name not in _signal_names(signals)


# ---------------------------------------------------------------------------
# Peer count gate
# ---------------------------------------------------------------------------


class TestPeerCountGate:
    def test_no_peers_skips_risk_z_signals(self):
        signals = extract_signals(
            _base_case(
                peer_case_count=10,
                service_volume_peer_z=6.0,
            )
        )
        assert SERVICE_VOLUME_OUTLIER.name not in _signal_names(signals)

    def test_no_peers_skips_legitimacy_z_signals(self):
        signals = extract_signals(_base_case(peer_case_count=10))
        names = _signal_names(signals)
        assert PEER_ALIGNED_VOLUME.name not in names
        assert PEER_ALIGNED_INTENSITY.name not in names
        assert PEER_ALIGNED_PRICING.name not in names

    def test_exact_min_peers_passes(self):
        signals = extract_signals(
            _base_case(
                peer_case_count=MIN_PEER_COUNT,
                service_volume_peer_z=5.0,
            )
        )
        assert SERVICE_VOLUME_OUTLIER.name in _signal_names(signals)

    def test_null_peer_count_skips(self):
        signals = extract_signals(
            _base_case(
                peer_case_count=None,
                service_volume_peer_z=5.0,
            )
        )
        assert SERVICE_VOLUME_OUTLIER.name not in _signal_names(signals)


# ---------------------------------------------------------------------------
# Peer-aligned legitimacy signals
# ---------------------------------------------------------------------------


class TestPeerAlignedSignals:
    def test_aligned_volume_fires(self):
        signals = extract_signals(_base_case(service_volume_peer_z=0.5))
        assert PEER_ALIGNED_VOLUME.name in _signal_names(signals)

    def test_aligned_intensity_fires(self):
        signals = extract_signals(_base_case(services_per_bene_peer_z=0.3))
        assert PEER_ALIGNED_INTENSITY.name in _signal_names(signals)

    def test_aligned_pricing_fires(self):
        signals = extract_signals(_base_case(submitted_to_allowed_peer_z=-0.5))
        assert PEER_ALIGNED_PRICING.name in _signal_names(signals)

    def test_high_z_not_aligned(self):
        """z >= 1.0 means not within one SD — should NOT fire."""
        signals = extract_signals(_base_case(service_volume_peer_z=1.5))
        assert PEER_ALIGNED_VOLUME.name not in _signal_names(signals)

    def test_negative_high_z_not_aligned(self):
        """z <= -1.0 means not within one SD — should NOT fire."""
        signals = extract_signals(_base_case(services_per_bene_peer_z=-1.5))
        assert PEER_ALIGNED_INTENSITY.name not in _signal_names(signals)

    def test_exact_boundary_not_aligned(self):
        """|z| == 1.0 is NOT < 1.0, so should not fire."""
        signals = extract_signals(_base_case(service_volume_peer_z=1.0))
        assert PEER_ALIGNED_VOLUME.name not in _signal_names(signals)

    def test_aligned_points_correct(self):
        signals = extract_signals(_base_case(service_volume_peer_z=0.5))
        s = _find(signals, PEER_ALIGNED_VOLUME.name)
        assert s is not None
        assert s.points == 12


# ---------------------------------------------------------------------------
# Large patient panel
# ---------------------------------------------------------------------------


class TestLargePatientPanel:
    def test_fires_above_threshold(self):
        signals = extract_signals(_base_case(provider_total_benes=150.0))
        assert LARGE_PATIENT_PANEL.name in _signal_names(signals)

    def test_fires_at_exact_threshold(self):
        signals = extract_signals(_base_case(provider_total_benes=100.0))
        assert LARGE_PATIENT_PANEL.name in _signal_names(signals)

    def test_does_not_fire_below(self):
        signals = extract_signals(_base_case(provider_total_benes=50.0))
        assert LARGE_PATIENT_PANEL.name not in _signal_names(signals)

    def test_null_benes_skips(self):
        signals = extract_signals(_base_case(provider_total_benes=None))
        assert LARGE_PATIENT_PANEL.name not in _signal_names(signals)

    def test_zero_benes_skips(self):
        signals = extract_signals(_base_case(provider_total_benes=0))
        assert LARGE_PATIENT_PANEL.name not in _signal_names(signals)

    def test_panel_value_captured(self):
        signals = extract_signals(_base_case(provider_total_benes=250.0))
        s = _find(signals, LARGE_PATIENT_PANEL.name)
        assert s is not None
        assert s.value == 250.0


# ---------------------------------------------------------------------------
# Concentration outlier
# ---------------------------------------------------------------------------


class TestConcentrationOutlier:
    def test_extreme_top_code_share(self):
        signals = extract_signals(_base_case(top_code_share=0.95))
        s = _find(signals, CONCENTRATION_OUTLIER.name)
        assert s is not None
        assert s.points == 12

    def test_high_top_code_share(self):
        signals = extract_signals(_base_case(top_code_share=0.85))
        s = _find(signals, CONCENTRATION_OUTLIER.name)
        assert s is not None
        assert s.points == 8

    def test_hhi_fires_when_top_code_below_threshold(self):
        signals = extract_signals(_base_case(top_code_share=0.5, service_hhi=0.55))
        s = _find(signals, CONCENTRATION_OUTLIER.name)
        assert s is not None
        assert s.points == 6

    def test_top_code_takes_priority_over_hhi(self):
        signals = extract_signals(_base_case(top_code_share=0.92, service_hhi=0.6))
        s = _find(signals, CONCENTRATION_OUTLIER.name)
        assert s is not None
        assert s.points == 12  # top_code tier, not HHI

    def test_does_not_fire_below_thresholds(self):
        signals = extract_signals(_base_case(top_code_share=0.5, service_hhi=0.3))
        assert CONCENTRATION_OUTLIER.name not in _signal_names(signals)

    def test_does_not_fire_when_missing(self):
        signals = extract_signals(_base_case())
        assert CONCENTRATION_OUTLIER.name not in _signal_names(signals)

    def test_reason_includes_percentage(self):
        signals = extract_signals(_base_case(top_code_share=0.91))
        s = _find(signals, CONCENTRATION_OUTLIER.name)
        assert s is not None
        assert "91%" in s.reason


# ---------------------------------------------------------------------------
# Integration: full case
# ---------------------------------------------------------------------------


class TestFullCaseExtraction:
    def test_healthy_provider_all_legitimacy(self):
        """Enrolled, not revoked, participating, aligned, large panel."""
        signals = extract_signals(_base_case())
        names = _signal_names(signals)
        # All legitimacy signals should fire
        assert ENROLLED_CURRENT.name in names
        assert NO_REVOCATION.name in names
        assert MEDICARE_PARTICIPATING.name in names
        assert PEER_ALIGNED_VOLUME.name in names
        assert PEER_ALIGNED_INTENSITY.name in names
        assert PEER_ALIGNED_PRICING.name in names
        assert LARGE_PATIENT_PANEL.name in names
        # No risk signals
        assert REVOKED_PROVIDER.name not in names
        assert NOT_IN_ENROLLMENT.name not in names
        assert SERVICE_VOLUME_OUTLIER.name not in names

    def test_risky_provider_mix(self):
        """Revoked, high z-scores, small panel."""
        case = _base_case(
            present_in_2025_enrollment_file=0,
            present_in_2026_revocation_file=1,
            medicare_participating_ind="N",
            service_volume_peer_z=5.5,
            services_per_bene_peer_z=4.0,
            submitted_to_allowed_peer_z=3.5,
            payment_peer_z=2.5,
            provider_total_benes=30.0,
        )
        signals = extract_signals(case)
        names = _signal_names(signals)
        # Risk signals
        assert REVOKED_PROVIDER.name in names
        assert NOT_IN_ENROLLMENT.name in names
        assert SERVICE_VOLUME_OUTLIER.name in names
        assert SERVICE_INTENSITY_OUTLIER.name in names
        assert CHARGE_RATIO_OUTLIER.name in names
        assert PAYMENT_OUTLIER.name in names
        # No legitimacy signals (except maybe none)
        assert ENROLLED_CURRENT.name not in names
        assert NO_REVOCATION.name not in names
        assert MEDICARE_PARTICIPATING.name not in names
        assert LARGE_PATIENT_PANEL.name not in names

    def test_fired_signal_is_frozen(self):
        signals = extract_signals(_base_case())
        s = signals[0]
        try:
            s.points = 999  # type: ignore[misc]
            raise AssertionError("FiredSignal should be frozen")
        except AttributeError:
            pass
