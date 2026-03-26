from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.api import deps as api_deps
from src.api.live_queue import QueueEvent, QueueManager, start_queue, stop_queue
from src.api.routes import live as live_routes

SAMPLE_EVENT = QueueEvent(
    npi="1234567890",
    provider_name="SMITH, JOHN M.D.",
    state="TX",
    city="HOUSTON",
    hcpcs_code="99213",
    hcpcs_desc="OFFICE/OUTPATIENT VISIT EST",
    submitted_charge=150.0,
    provider_type="Internal Medicine",
    risk_score=35,
    legitimacy_score=55,
    case_label="review",
    anomaly_score=None,
    signals=["service_volume_outlier"],
    scoring_latency_ms=1.2,
)


class FakeCursor:
    def __init__(self, responses: list[list[dict]]) -> None:
        self._responses = list(responses)
        self.executed: list[tuple[str, dict]] = []

    async def __aenter__(self) -> FakeCursor:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def execute(self, sql: str, params: dict) -> None:
        self.executed.append((sql, params))

    async def fetchall(self) -> list[dict]:
        if self._responses:
            return self._responses.pop(0)
        return []


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor

    def cursor(self, **kwargs) -> FakeCursor:
        return self._cursor


class FakeConnectionContext:
    def __init__(self, conn: FakeConnection) -> None:
        self._conn = conn

    async def __aenter__(self) -> FakeConnection:
        return self._conn

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class FakePool:
    def __init__(self, conn: FakeConnection) -> None:
        self._conn = conn

    def connection(self) -> FakeConnectionContext:
        return FakeConnectionContext(self._conn)


class BrokenQueue(asyncio.Queue[str]):
    def put_nowait(self, item: str) -> None:
        raise asyncio.QueueFull

    def get_nowait(self) -> str:
        raise asyncio.QueueEmpty


@pytest.fixture
def sample_row() -> dict:
    return {
        "case_id": 101,
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


@pytest.fixture
def queue_mgr() -> QueueManager:
    mgr = QueueManager()
    mgr.queue = [SAMPLE_EVENT] * 2
    mgr.ready = True
    mgr.running = True
    mgr.queue_actual_counts = {
        "high_risk": 0,
        "review": 2,
        "stable": 0,
        "total": 2,
    }
    return mgr


class TestQueueManager:
    def test_subscribe_unsubscribe_marks_last_batch_idle(self, queue_mgr: QueueManager):
        subscriber = queue_mgr.subscribe()
        assert len(queue_mgr._subscribers) == 1

        queue_mgr.unsubscribe(subscriber)

        assert len(queue_mgr._subscribers) == 0
        assert queue_mgr.ready is False
        assert len(queue_mgr.queue) == 2

    def test_unsubscribe_nonexistent_does_not_raise(self, queue_mgr: QueueManager):
        queue_mgr.unsubscribe(asyncio.Queue())
        assert queue_mgr.running is True

    @pytest.mark.asyncio
    async def test_broadcast_replaces_oldest_for_slow_subscriber(
        self, queue_mgr: QueueManager
    ):
        subscriber: asyncio.Queue[str] = asyncio.Queue(maxsize=1)
        subscriber.put_nowait("old")
        queue_mgr._subscribers = [subscriber]

        await queue_mgr._broadcast("new")

        assert await subscriber.get() == "new"

    @pytest.mark.asyncio
    async def test_broadcast_drops_broken_subscriber(self, queue_mgr: QueueManager):
        broken = BrokenQueue()
        queue_mgr._subscribers = [broken]

        await queue_mgr._broadcast("ignored")

        assert queue_mgr._subscribers == []

    def test_get_db_pool_prefers_readonly(self):
        fake_pool = object()
        with (
            patch.object(api_deps, "readonly_pool", fake_pool),
            patch.object(api_deps, "pool", object()),
        ):
            assert QueueManager._get_db_pool() is fake_pool

    def test_get_db_pool_falls_back_to_primary(self):
        fake_pool = object()
        with (
            patch.object(api_deps, "readonly_pool", None),
            patch.object(api_deps, "pool", fake_pool),
        ):
            assert QueueManager._get_db_pool() is fake_pool

    @pytest.mark.asyncio
    async def test_fetch_band_rows_updates_cursor(self, sample_row: dict):
        cursor = FakeCursor([[sample_row]])
        conn = FakeConnection(cursor)
        mgr = QueueManager()

        rows = await mgr._fetch_band_rows(conn, "high_risk", 5)

        assert rows == [sample_row]
        assert mgr._band_after_case_id["high_risk"] == 101
        assert len(cursor.executed) == 1
        assert cursor.executed[0][1]["after_case_id"] == 0

    @pytest.mark.asyncio
    async def test_fetch_band_rows_wraps_when_cursor_exhausted(self, sample_row: dict):
        cursor = FakeCursor([[], [sample_row]])
        conn = FakeConnection(cursor)
        mgr = QueueManager()
        mgr._band_after_case_id["review"] = 500

        rows = await mgr._fetch_band_rows(conn, "review", 3)

        assert rows == [sample_row]
        assert len(cursor.executed) == 2
        assert cursor.executed[0][1]["after_case_id"] == 500
        assert cursor.executed[1][1]["after_case_id"] == 0

    @pytest.mark.asyncio
    async def test_fetch_band_rows_resets_cursor_when_still_empty(self):
        cursor = FakeCursor([[], []])
        conn = FakeConnection(cursor)
        mgr = QueueManager()
        mgr._band_after_case_id["stable"] = 99

        rows = await mgr._fetch_band_rows(conn, "stable", 3)

        assert rows == []
        assert mgr._band_after_case_id["stable"] == 0

    def test_interleave_covers_primary_mix_paths(self):
        stable = [SAMPLE_EVENT] * 6
        review = [SAMPLE_EVENT] * 2
        high_risk = [SAMPLE_EVENT]

        result = QueueManager._interleave(high_risk, review, stable)

        assert len(result) == 9
        assert result[2].case_label == "review"
        assert result[6].case_label == "review" or result[6].case_label == "high_risk"

    def test_interleave_drains_review_when_only_review_present(self):
        result = QueueManager._interleave([], [SAMPLE_EVENT], [])
        assert result == [SAMPLE_EVENT]

    def test_interleave_drains_high_risk_when_only_high_risk_present(self):
        result = QueueManager._interleave([SAMPLE_EVENT], [], [])
        assert result == [SAMPLE_EVENT]

    @pytest.mark.asyncio
    async def test_load_next_batch_returns_false_without_pool(self):
        mgr = QueueManager()
        with (
            patch.object(api_deps, "readonly_pool", None),
            patch.object(api_deps, "pool", None),
        ):
            assert await mgr._load_next_batch() is False

    @pytest.mark.asyncio
    async def test_load_next_batch_populates_current_batch(self, sample_row: dict):
        mgr = QueueManager()
        conn = FakeConnection(FakeCursor([]))
        pool = FakePool(conn)
        rows = {
            "high_risk": [sample_row],
            "review": [{**sample_row, "case_id": 102, "seed_case_label": "review"}],
            "stable": [{**sample_row, "case_id": 103, "seed_case_label": "stable"}],
        }

        async def fake_fetch(conn, label: str, limit: int) -> list[dict]:
            return rows[label]

        with (
            patch.object(mgr, "_get_db_pool", return_value=pool),
            patch.object(mgr, "_fetch_band_rows", AsyncMock(side_effect=fake_fetch)),
        ):
            loaded = await mgr._load_next_batch()

        assert loaded is True
        assert mgr.ready is True
        assert mgr.position == 0
        assert mgr.queue_actual_counts["total"] == 3
        assert len(mgr.queue) == 3
        assert mgr.build_time_s >= 0.0

    @pytest.mark.asyncio
    async def test_load_next_batch_handles_empty_rows(self):
        mgr = QueueManager()
        conn = FakeConnection(FakeCursor([]))
        pool = FakePool(conn)

        async def fake_fetch(conn, label: str, limit: int) -> list[dict]:
            return []

        with (
            patch.object(mgr, "_get_db_pool", return_value=pool),
            patch.object(mgr, "_fetch_band_rows", AsyncMock(side_effect=fake_fetch)),
        ):
            loaded = await mgr._load_next_batch()

        assert loaded is False
        assert mgr.ready is False
        assert mgr.queue == []
        assert mgr.queue_actual_counts["total"] == 0

    @pytest.mark.asyncio
    async def test_emit_loop_waits_when_no_subscribers(self):
        mgr = QueueManager(running=True, ready=True, queue=[SAMPLE_EVENT], position=1)
        mgr.queue_actual_counts = {"high_risk": 0, "review": 1, "stable": 0, "total": 1}
        sleep_calls: list[float] = []

        async def fake_sleep(delay: float) -> None:
            sleep_calls.append(delay)
            mgr.running = False

        with patch("src.api.live_queue.asyncio.sleep", side_effect=fake_sleep):
            await mgr._emit_loop()

        assert sleep_calls == [0.5]
        assert mgr.queue == []
        assert mgr.position == 0
        assert mgr.ready is False
        assert mgr.queue_actual_counts == {}

    @pytest.mark.asyncio
    async def test_emit_loop_waits_when_batch_load_returns_false(self):
        mgr = QueueManager(running=True)
        mgr.subscribe()
        sleep_calls: list[float] = []

        async def fake_sleep(delay: float) -> None:
            sleep_calls.append(delay)
            mgr.running = False

        with (
            patch.object(mgr, "_load_next_batch", AsyncMock(return_value=False)),
            patch("src.api.live_queue.asyncio.sleep", side_effect=fake_sleep),
        ):
            await mgr._emit_loop()

        assert sleep_calls == [1.0]

    @pytest.mark.asyncio
    async def test_start_initializes_background_task(self):
        mgr = QueueManager()
        task = object()

        def fake_create_task(coro):
            coro.close()
            return task

        with patch(
            "src.api.live_queue.asyncio.create_task", side_effect=fake_create_task
        ) as create_task:
            await mgr.start()
            await mgr.start()

        assert mgr.running is True
        assert mgr.position == 0
        assert mgr.total_emitted == 0
        assert mgr._task is task
        assert create_task.call_count == 1

    @pytest.mark.asyncio
    async def test_stop_cancels_background_task_and_clears_state(self):
        mgr = QueueManager(running=True, ready=True, queue=[SAMPLE_EVENT], position=1)

        async def wait_forever() -> None:
            await asyncio.Future()

        mgr._task = asyncio.create_task(wait_forever())
        await asyncio.sleep(0)

        await mgr.stop()

        assert mgr.running is False
        assert mgr.ready is False
        assert mgr._task is None
        assert mgr.queue == []
        assert mgr.position == 0

    def test_status_includes_runtime_fields(self, queue_mgr: QueueManager):
        queue_mgr.tps = 5.0
        queue_mgr.total_emitted = 11
        status = queue_mgr.status()

        assert status["running"] is True
        assert status["queue_size"] == 2
        assert status["total_emitted"] == 11
        assert status["tps"] == 5.0

    @pytest.mark.asyncio
    async def test_module_level_start_and_stop_queue_delegate(self):
        with (
            patch.object(live_routes.queue_manager, "start", AsyncMock()) as start_mock,
            patch.object(live_routes.queue_manager, "stop", AsyncMock()) as stop_mock,
        ):
            await start_queue()
            await stop_queue()

        assert start_mock.await_count == 1
        assert stop_mock.await_count == 1


class TestLiveRoutes:
    @pytest.mark.asyncio
    async def test_ensure_queue_started_when_not_running(self):
        mgr = QueueManager(running=False)
        with (
            patch.object(live_routes, "queue_manager", mgr),
            patch.object(live_routes, "start_queue", AsyncMock()) as start_mock,
        ):
            await live_routes._ensure_queue_started()

        assert start_mock.await_count == 1

    @pytest.mark.asyncio
    async def test_ensure_queue_started_when_already_running(self):
        mgr = QueueManager(running=True)
        with (
            patch.object(live_routes, "queue_manager", mgr),
            patch.object(live_routes, "start_queue", AsyncMock()) as start_mock,
        ):
            await live_routes._ensure_queue_started()

        assert start_mock.await_count == 0

    @pytest.mark.asyncio
    async def test_queue_status_returns_manager_status(self):
        mgr = QueueManager(running=True)
        mgr.queue = [SAMPLE_EVENT]
        mgr.ready = True
        with patch.object(live_routes, "queue_manager", mgr):
            status = await live_routes.queue_status()

        assert status["running"] is True
        assert status["queue_size"] == 1

    @pytest.mark.asyncio
    async def test_set_tps_updates_manager_when_not_running(self):
        mgr = QueueManager(running=False)
        mgr.tps = 2.0
        with patch.object(live_routes, "queue_manager", mgr):
            payload = await live_routes.set_tps(tps=5.0)

        assert payload == {"tps": 5.0}
        assert mgr.tps == 5.0

    @pytest.mark.asyncio
    async def test_set_tps_updates_running_manager(self):
        mgr = QueueManager(running=True)
        with patch.object(live_routes, "queue_manager", mgr):
            payload = await live_routes.set_tps(tps=5.0)

        assert payload == {"tps": 5.0}
        assert mgr.tps == 5.0

    @pytest.mark.asyncio
    async def test_rebuild_queue_restarts_running_manager(self):
        mgr = QueueManager(running=True)
        mgr.status = lambda: {"running": True, "queue_size": 0}  # type: ignore[method-assign]
        with (
            patch.object(live_routes, "queue_manager", mgr),
            patch.object(mgr, "stop", AsyncMock()) as stop_mock,
            patch.object(mgr, "start", AsyncMock()) as start_mock,
        ):
            payload = await live_routes.rebuild_queue()

        assert stop_mock.await_count == 1
        assert start_mock.await_count == 1
        assert payload == {"running": True, "queue_size": 0}

    @pytest.mark.asyncio
    async def test_rebuild_queue_starts_when_idle(self):
        mgr = QueueManager(running=False)
        mgr.status = lambda: {"running": False, "queue_size": 0}  # type: ignore[method-assign]
        with (
            patch.object(live_routes, "queue_manager", mgr),
            patch.object(mgr, "stop", AsyncMock()) as stop_mock,
            patch.object(mgr, "start", AsyncMock()) as start_mock,
        ):
            payload = await live_routes.rebuild_queue()

        assert stop_mock.await_count == 0
        assert start_mock.await_count == 1
        assert payload == {"running": False, "queue_size": 0}

    @pytest.mark.asyncio
    async def test_stream_claims_starts_queue_sets_tps_and_yields_event(self):
        mgr = QueueManager(running=False)

        async def fake_start() -> None:
            mgr.running = True

        with (
            patch.object(live_routes, "queue_manager", mgr),
            patch.object(live_routes, "start_queue", AsyncMock(side_effect=fake_start)),
        ):
            response = await live_routes.stream_claims(tps=5.0)
            assert response.media_type == "text/event-stream"
            assert mgr.tps == 5.0
            assert len(mgr._subscribers) == 1

            subscriber = mgr._subscribers[0]
            subscriber.put_nowait("data: test-event\n\n")
            iterator = response.body_iterator
            chunk = await iterator.__anext__()
            await iterator.aclose()

        assert chunk == "data: test-event\n\n"
        assert mgr._subscribers == []

    @pytest.mark.asyncio
    async def test_stream_claims_yields_keepalive_on_timeout(self):
        mgr = QueueManager(running=True)

        async def fake_wait_for(awaitable, timeout: float):
            awaitable.close()
            raise TimeoutError

        with (
            patch.object(live_routes, "queue_manager", mgr),
            patch("src.api.routes.live.asyncio.wait_for", side_effect=fake_wait_for),
        ):
            response = await live_routes.stream_claims(tps=0.0)
            iterator = response.body_iterator
            chunk = await iterator.__anext__()
            await iterator.aclose()

        assert chunk == ": keepalive\n\n"
