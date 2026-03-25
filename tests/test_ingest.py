"""Tests for src/api/routes/ingest.py — upload, recalibrate, retrain, RBAC, and
concurrent-run guard.

All tests use mocks — no live database connection required.
"""

from __future__ import annotations

import io
from contextlib import asynccontextmanager
from unittest.mock import patch

import bcrypt
import httpx
import pytest
from fastapi import Depends, FastAPI

from src.api.auth import create_access_token, get_current_user, require_admin
from src.api.deps import get_db
from src.api.routes.ingest import router as ingest_router
from src.api.schemas import UserResponse

# ---------------------------------------------------------------------------
# Fake users
# ---------------------------------------------------------------------------

_HASHED = bcrypt.hashpw(b"pass", bcrypt.gensalt()).decode()

FAKE_USERS = {
    "admin_user": {
        "id": 1,
        "username": "admin_user",
        "hashed_password": _HASHED,
        "role": "admin",
        "full_name": "Admin User",
        "is_active": True,
    },
    "analyst_user": {
        "id": 2,
        "username": "analyst_user",
        "hashed_password": _HASHED,
        "role": "analyst",
        "full_name": "Analyst User",
        "is_active": True,
    },
}


# ---------------------------------------------------------------------------
# Fake DB layer
# ---------------------------------------------------------------------------


class _FakeCursor:
    """Async cursor that returns a fixed sequence of rows."""

    def __init__(self, rows: list, cols: list[str] | None = None):
        self._rows = rows
        self._idx = 0
        self.description = [(c,) for c in (cols or [])]

    async def execute(self, sql: str, params=None):
        return self

    async def fetchone(self):
        if self._rows:
            return self._rows[0]
        return None

    async def fetchall(self):
        return list(self._rows)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class _FakeConn:
    """Minimal async psycopg connection mock."""

    def __init__(self, execute_return=None):
        self._execute_return = execute_return or _FakeCursor([])
        self.committed = False

    async def execute(self, sql: str, params=None):
        return self._execute_return

    async def commit(self):
        self.committed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class _AuthCursor:
    def __init__(self):
        self._result: dict | None = None

    async def execute(self, sql: str, params=None):
        if params:
            username = params[0]
            self._result = FAKE_USERS.get(username)

    async def fetchone(self):
        return self._result

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class _AuthConn:
    def cursor(self, row_factory=None):
        return _AuthCursor()


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def _make_app(fake_conn=None) -> FastAPI:
    """Create a minimal test FastAPI app with the ingest router."""

    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI):
        yield

    test_app = FastAPI(lifespan=_noop_lifespan)

    auth_conn = _AuthConn()

    async def fake_auth_db():
        yield auth_conn

    async def fake_ingest_db():
        yield fake_conn or _FakeConn()

    # Override DB for auth middleware and route
    test_app.dependency_overrides[get_db] = fake_ingest_db

    # Include ingest router with auth protection
    test_app.include_router(
        ingest_router,
        prefix="/api",
        dependencies=[Depends(get_current_user)],
    )

    # Patch auth dependency to use our fake auth conn
    from src.api import auth as auth_module

    async def patched_get_current_user(
        creds=Depends(auth_module._bearer),
    ) -> UserResponse:
        import jwt as pyjwt

        from src.api.auth import JWT_ALGORITHM, JWT_SECRET

        try:
            payload = pyjwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            username: str | None = payload.get("sub")
            if username is None:
                from fastapi import HTTPException

                raise HTTPException(status_code=401, detail="Invalid token")
        except pyjwt.PyJWTError:
            from fastapi import HTTPException

            raise HTTPException(status_code=401, detail="Invalid token")

        user_data = FAKE_USERS.get(username or "")
        if user_data is None or not user_data["is_active"]:
            from fastapi import HTTPException

            raise HTTPException(status_code=401, detail="User not found")

        return UserResponse(
            id=user_data["id"],
            username=user_data["username"],
            role=user_data["role"],
            full_name=user_data["full_name"],
        )

    test_app.dependency_overrides[get_current_user] = patched_get_current_user

    return test_app


def _admin_headers() -> dict[str, str]:
    token = create_access_token({"sub": "admin_user"})
    return {"Authorization": f"Bearer {token}"}


def _analyst_headers() -> dict[str, str]:
    token = create_access_token({"sub": "analyst_user"})
    return {"Authorization": f"Bearer {token}"}


def _no_headers() -> dict[str, str]:
    return {}


# ---------------------------------------------------------------------------
# Minimal fixture CSV for part_b_service
# ---------------------------------------------------------------------------

# Required columns for part_b_service:
# Rndrng_NPI, HCPCS_Cd, Tot_Benes, Tot_Srvcs, Avg_Sbmtd_Chrg,
# Avg_Mdcr_Alowd_Amt, Avg_Mdcr_Pymt_Amt

_FIXTURE_CSV = (
    "Rndrng_NPI,HCPCS_Cd,Tot_Benes,Tot_Srvcs,Avg_Sbmtd_Chrg,"
    "Avg_Mdcr_Alowd_Amt,Avg_Mdcr_Pymt_Amt\n"
    "1234567890,99213,10,20,100.00,80.00,70.00\n"
    "0987654321,99214,5,10,200.00,160.00,140.00\n"
)

_MISSING_COL_CSV = "Rndrng_NPI,HCPCS_Cd\n1234567890,99213\n"


# ---------------------------------------------------------------------------
# Helpers for multi-execute mocks
# ---------------------------------------------------------------------------


class _MultiCursor:
    """Cursor that cycles through a list of return values per execute call."""

    def __init__(self, results: list[tuple | None]):
        self._results = list(results)
        self._call = 0
        self.description = []

    async def execute(self, *args, **kwargs):
        self._call += 1
        return self

    async def fetchone(self):
        idx = self._call - 1
        if idx < len(self._results):
            return self._results[idx]
        return None

    async def fetchall(self):
        return []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class _MultiConn:
    """Connection whose execute() cycles through a list of cursors."""

    def __init__(self, cursors: list):
        self._cursors = list(cursors)
        self._call = 0
        self.committed = False

    async def execute(self, *args, **kwargs):
        idx = self._call
        self._call += 1
        if idx < len(self._cursors):
            return self._cursors[idx]
        return _FakeCursor([])

    async def commit(self):
        self.committed = True


# ---------------------------------------------------------------------------
# Tests — GET /ingest/runs
# ---------------------------------------------------------------------------


class TestListRuns:
    async def test_returns_paginated_list(self):
        """list_pipeline_runs returns PipelineRunList with meta."""
        count_cur = _FakeCursor([(3,)])
        _cols = [
            "id",
            "run_type",
            "status",
            "current_stage",
            "progress_pct",
            "source_versions",
            "stage_results",
            "error_message",
            "started_at",
            "completed_at",
            "triggered_by",
        ]
        list_cur = _FakeCursor(
            [
                (
                    1,
                    "recalibration",
                    "completed",
                    None,
                    100.0,
                    {},
                    [],
                    None,
                    "2026-01-01",
                    "2026-01-02",
                    "admin",
                ),
                (
                    2,
                    "recalibration",
                    "running",
                    "ingest",
                    15.0,
                    {},
                    [],
                    None,
                    "2026-01-03",
                    None,
                    "admin",
                ),
            ],
            cols=_cols,
        )
        conn = _MultiConn([count_cur, list_cur])
        app = _make_app(fake_conn=conn)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/ingest/runs", headers=_admin_headers())

        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert body["meta"]["total"] == 3

    async def test_requires_auth(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/ingest/runs")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Tests — GET /ingest/runs/{id}
# ---------------------------------------------------------------------------


class TestGetRun:
    async def test_returns_run_detail(self):
        cur = _FakeCursor(
            [
                (
                    7,
                    "recalibration",
                    "completed",
                    None,
                    100.0,
                    {},
                    [],
                    None,
                    "2026-01-01",
                    "2026-01-02",
                    "admin",
                )
            ],
            cols=[
                "id",
                "run_type",
                "status",
                "current_stage",
                "progress_pct",
                "source_versions",
                "stage_results",
                "error_message",
                "started_at",
                "completed_at",
                "triggered_by",
            ],
        )
        conn = _FakeConn(execute_return=cur)
        app = _make_app(fake_conn=conn)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/ingest/runs/7", headers=_admin_headers())

        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == 7
        assert body["run_type"] == "recalibration"
        assert body["status"] == "completed"

    async def test_returns_404_for_missing_run(self):
        cur = _FakeCursor([])  # fetchone returns None
        conn = _FakeConn(execute_return=cur)
        app = _make_app(fake_conn=conn)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/ingest/runs/9999", headers=_admin_headers())

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests — POST /ingest/recalibrate (RBAC + concurrency)
# ---------------------------------------------------------------------------


class TestRecalibrate:
    async def test_admin_can_trigger_recalibrate(self):
        """Admin user gets 202 and run_id from recalibrate."""
        # 1st execute: COUNT for concurrency check → 0 running
        # 2nd execute: INSERT returning run_id=42
        count_cur = _FakeCursor([(0,)])
        insert_cur = _FakeCursor([(42,)])
        conn = _MultiConn([count_cur, insert_cur])
        app = _make_app(fake_conn=conn)

        with patch("src.api.routes.ingest.recalibrate") as mock_recal:
            mock_recal.return_value = None
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/ingest/recalibrate", headers=_admin_headers())

        assert resp.status_code == 202
        body = resp.json()
        assert body["id"] == 42
        assert body["run_type"] == "recalibration"
        assert body["status"] == "pending"

    async def test_analyst_cannot_recalibrate(self):
        """Non-admin user gets 403."""
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/ingest/recalibrate", headers=_analyst_headers())

        assert resp.status_code == 403

    async def test_unauthenticated_cannot_recalibrate(self):
        """No token → 401 or 403."""
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/ingest/recalibrate")

        assert resp.status_code in (401, 403)

    async def test_concurrent_pipeline_rejected_with_409(self):
        """Returns 409 when a pipeline is already running."""
        # COUNT returns 1 → pipeline already running
        count_cur = _FakeCursor([(1,)])
        conn = _MultiConn([count_cur])
        app = _make_app(fake_conn=conn)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/ingest/recalibrate", headers=_admin_headers())

        assert resp.status_code == 409
        assert "already running" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Tests — POST /ingest/retrain (RBAC + concurrency)
# ---------------------------------------------------------------------------


class TestRetrain:
    async def test_admin_can_trigger_retrain(self):
        count_cur = _FakeCursor([(0,)])
        insert_cur = _FakeCursor([(55,)])
        conn = _MultiConn([count_cur, insert_cur])
        app = _make_app(fake_conn=conn)

        with patch("src.api.routes.ingest.retrain_and_recalibrate") as mock_retrain:
            mock_retrain.return_value = None
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/ingest/retrain", headers=_admin_headers())

        assert resp.status_code == 202
        body = resp.json()
        assert body["id"] == 55
        assert body["run_type"] == "retrain_and_recalibrate"

    async def test_analyst_cannot_retrain(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/ingest/retrain", headers=_analyst_headers())

        assert resp.status_code == 403

    async def test_concurrent_pipeline_rejected_with_409(self):
        count_cur = _FakeCursor([(2,)])
        conn = _MultiConn([count_cur])
        app = _make_app(fake_conn=conn)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/ingest/retrain", headers=_admin_headers())

        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Tests — POST /ingest/upload (RBAC + validation)
# ---------------------------------------------------------------------------


class TestUpload:
    def _csv_file(self, content: str, filename: str = "data.csv"):
        return ("file", (filename, io.BytesIO(content.encode()), "text/csv"))

    async def test_analyst_cannot_upload(self):
        """Non-admin gets 403 before load_raw_csv is ever called."""
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ingest/upload",
                headers=_analyst_headers(),
                data={"source_type": "part_b_service", "version": "2024"},
                files=[self._csv_file(_FIXTURE_CSV)],
            )

        assert resp.status_code == 403

    async def test_unauthenticated_cannot_upload(self):
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ingest/upload",
                data={"source_type": "part_b_service", "version": "2024"},
                files=[self._csv_file(_FIXTURE_CSV)],
            )

        assert resp.status_code in (401, 403)

    async def test_non_csv_rejected(self):
        """Files without .csv extension are rejected with 422."""
        app = _make_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ingest/upload",
                headers=_admin_headers(),
                data={"source_type": "part_b_service", "version": "2024"},
                files=[("file", ("data.xlsx", io.BytesIO(b"not csv"), "application/vnd.ms-excel"))],
            )

        assert resp.status_code == 422

    async def test_missing_columns_rejected(self):
        """CSV missing required columns returns 422."""

        app = _make_app()
        with patch(
            "src.api.routes.ingest._load_csv_sync",
            side_effect=ValueError("CSV is missing required columns: ['Tot_Benes']"),
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/ingest/upload",
                    headers=_admin_headers(),
                    data={"source_type": "part_b_service", "version": "2024"},
                    files=[self._csv_file(_MISSING_COL_CSV)],
                )

        assert resp.status_code == 422

    async def test_admin_upload_success(self):
        """Admin upload returns UploadResponse on success."""
        from src.pipeline.raw_loader import LoadResult

        mock_result = LoadResult(row_count=2, file_hash="abc123", validation_warnings=[])

        app = _make_app()
        with patch("src.api.routes.ingest._load_csv_sync", return_value=mock_result):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/ingest/upload",
                    headers=_admin_headers(),
                    data={"source_type": "part_b_service", "version": "2024"},
                    files=[self._csv_file(_FIXTURE_CSV)],
                )

        assert resp.status_code == 200
        body = resp.json()
        assert body["row_count"] == 2
        assert body["file_hash"] == "abc123"
        assert body["validation_warnings"] == []
        assert body["duplicate_detected"] is False


# ---------------------------------------------------------------------------
# Tests — GET /ingest/sources
# ---------------------------------------------------------------------------


class TestListSources:
    async def test_returns_source_list(self):
        _src_cols = [
            "source_type",
            "current_version",
            "file_hash",
            "row_count",
            "uploaded_at",
            "uploaded_by",
        ]
        cur = _FakeCursor(
            [
                ("part_b_service", "2024", "hash1", 100000, "2026-01-01", "admin"),
                ("enrollment", "Q1-2026", "hash2", 200000, "2026-01-10", "admin"),
            ],
            cols=_src_cols,
        )
        conn = _FakeConn(execute_return=cur)
        app = _make_app(fake_conn=conn)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/ingest/sources", headers=_admin_headers())

        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        assert body[0]["type"] == "part_b_service"
        assert body[0]["version"] == "2024"
        assert body[1]["type"] == "enrollment"


# ---------------------------------------------------------------------------
# Tests — GET /ingest/status
# ---------------------------------------------------------------------------


class TestIngestStatus:
    _stat_cols = [
        "providers_in_system",
        "last_run_id",
        "last_run_type",
        "last_completed_at",
        "last_run_status",
    ]
    _src_cols = [
        "source_type",
        "current_version",
        "file_hash",
        "row_count",
        "uploaded_at",
        "uploaded_by",
    ]

    async def test_returns_status_structure(self):
        stat_cur = _FakeCursor(
            [(18412, 47, "recalibration", "2026-03-24T14:17:00", "completed")],
            cols=self._stat_cols,
        )
        sources_cur = _FakeCursor(
            [("part_b_service", "2024", "hash1", 847231, "2026-01-01", "admin")],
            cols=self._src_cols,
        )
        conn = _MultiConn([stat_cur, sources_cur])
        app = _make_app(fake_conn=conn)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/ingest/status", headers=_admin_headers())

        assert resp.status_code == 200
        body = resp.json()
        assert body["providers_in_system"] == 18412
        assert body["last_recalibration"] is not None
        assert body["last_recalibration"]["run_id"] == 47
        assert body["last_recalibration"]["status"] == "completed"
        assert len(body["sources"]) == 1
        assert body["sources"][0]["type"] == "part_b_service"

    async def test_status_no_prior_run(self):
        """status endpoint handles no prior completed runs gracefully."""
        stat_cur = _FakeCursor(
            [(0, None, None, None, None)],
            cols=self._stat_cols,
        )
        sources_cur = _FakeCursor([], cols=self._src_cols)
        conn = _MultiConn([stat_cur, sources_cur])
        app = _make_app(fake_conn=conn)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/ingest/status", headers=_admin_headers())

        assert resp.status_code == 200
        body = resp.json()
        assert body["providers_in_system"] == 0
        assert body["last_recalibration"] is None
        assert body["sources"] == []


# ---------------------------------------------------------------------------
# Tests — require_admin dependency directly
# ---------------------------------------------------------------------------


class TestRequireAdmin:
    async def test_admin_user_passes(self):

        admin = UserResponse(id=1, username="admin_user", role="admin", full_name="Admin")
        result = await require_admin(user=admin)
        assert result.username == "admin_user"

    async def test_non_admin_raises_403(self):
        from fastapi import HTTPException

        analyst = UserResponse(id=2, username="analyst", role="analyst", full_name="Analyst")
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user=analyst)
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Admin access required"
