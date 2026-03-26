from src.api.live_queue import QueueManager


def test_event_from_seed_row_uses_precomputed_seed_fields() -> None:
    row = {
        "npi": "1234567890",
        "provider_name": "SMITH, JOHN",
        "state": "TX",
        "city": "Houston",
        "hcpcs_cd": "99213",
        "hcpcs_desc": "Office visit",
        "avg_submitted_charge": 125.5,
        "provider_type": "Internal Medicine",
        "seed_risk_score": 72,
        "seed_legitimacy_score": 24,
        "seed_case_label": "high_risk",
        "seed_risk_reasons": "revoked_provider|payment_outlier|service_volume_outlier",
    }

    event = QueueManager._event_from_seed_row(row)

    assert event.npi == "1234567890"
    assert event.provider_name == "SMITH, JOHN"
    assert event.risk_score == 72
    assert event.legitimacy_score == 24
    assert event.case_label == "high_risk"
    assert event.signals == [
        "revoked_provider",
        "payment_outlier",
        "service_volume_outlier",
    ]
    assert event.anomaly_score is None
    assert event.scoring_latency_ms == 0.0


def test_parse_seed_reasons_handles_empty_values() -> None:
    assert QueueManager._parse_seed_reasons(None) == []
    assert QueueManager._parse_seed_reasons("") == []
    assert QueueManager._parse_seed_reasons("a|b|| c ") == ["a", "b", "c"]
