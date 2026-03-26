from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

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


@pytest.mark.asyncio
async def test_emit_loop_loads_a_batch_on_demand() -> None:
    mgr = QueueManager(tps=20.0, running=True)
    subscriber = mgr.subscribe()

    async def load_next_batch() -> bool:
        mgr.queue = [
            QueueManager._event_from_seed_row(
                {
                    "npi": "1111111111",
                    "provider_name": "TEST PROVIDER",
                    "state": "TX",
                    "city": "Houston",
                    "hcpcs_cd": "99213",
                    "hcpcs_desc": "Office visit",
                    "avg_submitted_charge": 180.0,
                    "provider_type": "Internal Medicine",
                    "seed_risk_score": 61,
                    "seed_legitimacy_score": 39,
                    "seed_case_label": "high_risk",
                    "seed_risk_reasons": "payment_outlier|revoked_provider",
                }
            )
        ]
        mgr.position = 0
        mgr.queue_actual_counts = {
            "high_risk": 1,
            "review": 0,
            "stable": 0,
            "total": 1,
        }
        mgr.ready = True
        return True

    with patch.object(
        mgr,
        "_load_next_batch",
        AsyncMock(side_effect=load_next_batch),
    ) as load_mock:
        task = asyncio.create_task(mgr._emit_loop())
        try:
            message = await asyncio.wait_for(subscriber.get(), timeout=1.0)
        finally:
            mgr.running = False
            await asyncio.wait_for(task, timeout=1.0)

    payload = json.loads(message.removeprefix("data: ").strip())
    assert payload["npi"] == "1111111111"
    assert payload["case_label"] == "high_risk"
    assert load_mock.await_count == 1
    assert mgr.total_emitted == 1


def test_unsubscribe_last_subscriber_marks_batch_idle() -> None:
    mgr = QueueManager()
    mgr.queue = [
        QueueManager._event_from_seed_row(
            {
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
                "seed_risk_reasons": "revoked_provider|payment_outlier",
            }
        )
    ]
    mgr.position = 1
    mgr.queue_actual_counts = {"high_risk": 1, "review": 0, "stable": 0, "total": 1}

    subscriber = mgr.subscribe()
    mgr.unsubscribe(subscriber)

    assert len(mgr.queue) == 1
    assert mgr.position == 1
    assert mgr.ready is False
    assert mgr.queue_actual_counts == {"high_risk": 1, "review": 0, "stable": 0, "total": 1}
