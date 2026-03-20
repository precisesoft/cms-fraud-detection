"""Tests for network risk endpoint — schema and SQL validation."""

from __future__ import annotations

from src.api.schemas import NetworkNeighbor, NetworkRiskResponse


class TestNetworkSchemas:
    def test_neighbor_minimal(self):
        n = NetworkNeighbor(npi="1234567890")
        assert n.npi == "1234567890"
        assert n.revoked is False

    def test_neighbor_full(self):
        n = NetworkNeighbor(
            npi="1234567890",
            provider_name="Test Clinic",
            provider_type="Internal Medicine",
            state="FL",
            risk_score=75,
            revoked=True,
        )
        assert n.risk_score == 75
        assert n.revoked is True

    def test_response_empty(self):
        r = NetworkRiskResponse(npi="1234567890")
        assert r.same_zip_flagged == []
        assert r.same_org_flagged == []
        assert r.zip_risk_summary is None

    def test_response_with_neighbors(self):
        r = NetworkRiskResponse(
            npi="1234567890",
            zip5="33101",
            same_zip_flagged=[
                NetworkNeighbor(npi="9999999999", risk_score=80, revoked=True),
                NetworkNeighbor(npi="8888888888", risk_score=55),
            ],
            same_org_flagged=[],
            zip_risk_summary={
                "total_in_zip": 15,
                "high_risk_in_zip": 4,
                "revoked_in_zip": 2,
                "avg_risk_in_zip": 42.3,
            },
        )
        assert len(r.same_zip_flagged) == 2
        assert r.zip_risk_summary["high_risk_in_zip"] == 4
