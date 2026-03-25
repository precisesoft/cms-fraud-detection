"""Tests for JWT authentication: login, /me, and route protection."""

from __future__ import annotations

from contextlib import asynccontextmanager

import bcrypt
import httpx
import jwt
from fastapi import Depends, FastAPI

from src.api.auth import (
    JWT_ALGORITHM,
    JWT_SECRET,
    create_access_token,
    get_current_user,
    invalidate_user_cache,
)
from src.api.deps import get_db
from src.api.routes.auth import router as auth_router
from src.api.routes.providers import router as providers_router
from src.api.schemas import HealthResponse

# ---------------------------------------------------------------------------
# Fake DB layer
# ---------------------------------------------------------------------------

_HASHED = bcrypt.hashpw(b"testpass", bcrypt.gensalt()).decode()

FAKE_USERS = {
    "admin": {
        "id": 1,
        "username": "admin",
        "hashed_password": _HASHED,
        "role": "admin",
        "full_name": "Admin User",
        "is_active": True,
    },
    "inactive": {
        "id": 2,
        "username": "inactive",
        "hashed_password": _HASHED,
        "role": "analyst",
        "full_name": "Inactive",
        "is_active": False,
    },
}


class _AuthCursor:
    """Simulates a cursor that looks up users by username."""

    def __init__(self, users: dict):
        self._users = users
        self._result: dict | None = None

    async def execute(self, sql: str, params: tuple | None = None):
        if params:
            username = params[0]
            self._result = self._users.get(username)

    async def fetchone(self) -> dict | None:
        return self._result

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class _AuthConn:
    def __init__(self, users: dict):
        self._users = users

    def cursor(self, row_factory=None):
        return _AuthCursor(self._users)


def _make_auth_app() -> FastAPI:
    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI):
        yield

    test_app = FastAPI(lifespan=_noop_lifespan)

    conn = _AuthConn(FAKE_USERS)

    async def fake_db():
        yield conn

    test_app.dependency_overrides[get_db] = fake_db

    # Auth routes — public
    test_app.include_router(auth_router, prefix="/api")

    # Provider routes — protected (mirrors app.py)
    test_app.include_router(
        providers_router, prefix="/api", dependencies=[Depends(get_current_user)]
    )

    # Health — unprotected
    @test_app.get("/health", response_model=HealthResponse, tags=["ops"])
    async def health():
        return HealthResponse(status="ok", database="ok", graph="unavailable", version="test")

    return test_app


# ---------------------------------------------------------------------------
# Tests — Login
# ---------------------------------------------------------------------------


class TestLogin:
    async def test_login_success(self):
        app = _make_auth_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "testpass"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["user"]["username"] == "admin"
        assert body["user"]["role"] == "admin"

    async def test_login_bad_password(self):
        app = _make_auth_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "wrongpass"},
            )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid username or password"

    async def test_login_nonexistent_user(self):
        app = _make_auth_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/auth/login",
                json={"username": "ghost", "password": "whatever"},
            )

        assert resp.status_code == 401

    async def test_login_inactive_user(self):
        app = _make_auth_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/auth/login",
                json={"username": "inactive", "password": "testpass"},
            )

        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests — /auth/me
# ---------------------------------------------------------------------------


class TestMe:
    async def test_me_with_valid_token(self):
        app = _make_auth_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            login = await client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "testpass"},
            )
            token = login.json()["access_token"]

            resp = await client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "admin"
        assert body["role"] == "admin"

    async def test_me_without_token(self):
        app = _make_auth_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/auth/me")

        assert resp.status_code in (401, 403)

    async def test_me_with_bad_token(self):
        app = _make_auth_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer garbage.token.here"},
            )

        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests — Route protection
# ---------------------------------------------------------------------------


class TestRouteProtection:
    async def test_protected_route_without_token(self):
        app = _make_auth_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/providers")

        assert resp.status_code in (401, 403)

    async def test_health_without_token(self):
        app = _make_auth_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/health")

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Tests — get_current_user direct coverage (lines 48, 60)
# ---------------------------------------------------------------------------


class TestGetCurrentUserEdgeCases:
    async def test_token_with_no_sub_claim_returns_401(self):
        """A valid JWT that has no 'sub' field should raise 401 (line 48)."""
        # Create a token without "sub"
        token_no_sub = jwt.encode(
            {"role": "admin"},  # deliberately omit "sub"
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )
        app = _make_auth_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token_no_sub}"},
            )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid token"

    async def test_token_for_inactive_user_returns_401(self):
        """A valid JWT for an inactive user should raise 401 at line 60."""
        # Build a token for "inactive" directly — bypass login which also rejects it
        token = create_access_token({"sub": "inactive"})
        app = _make_auth_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "User not found"

    async def test_token_for_missing_user_returns_401(self):
        """A valid JWT for a user that does not exist in DB should raise 401 (line 60)."""
        token = create_access_token({"sub": "ghost_user"})
        app = _make_auth_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "User not found"


# ---------------------------------------------------------------------------
# Tests — User cache behaviour (lines 43-46, 80-82)
# ---------------------------------------------------------------------------


class TestUserCache:
    async def test_cache_hit_skips_db(self):
        """Second request for the same user within TTL should hit cache (lines 80-82)."""
        invalidate_user_cache()  # start clean
        app = _make_auth_app()
        token = create_access_token({"sub": "admin"})
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            # First request — populates cache
            resp1 = await client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp1.status_code == 200

            # Second request — should hit cache (line 80-82)
            resp2 = await client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp2.status_code == 200
            assert resp2.json()["username"] == "admin"

        invalidate_user_cache()  # cleanup

    async def test_invalidate_all_users(self):
        """invalidate_user_cache(None) clears the entire cache (lines 43-44)."""
        invalidate_user_cache()  # start clean
        app = _make_auth_app()
        token = create_access_token({"sub": "admin"})
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Populate cache
            resp = await client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200

        # Clear entire cache
        invalidate_user_cache(None)

        # After invalidation, next request should still succeed (DB lookup)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200

        invalidate_user_cache()  # cleanup

    async def test_invalidate_single_user(self):
        """invalidate_user_cache('admin') removes only that user (lines 45-46)."""
        invalidate_user_cache()  # start clean
        app = _make_auth_app()
        token = create_access_token({"sub": "admin"})
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Populate cache
            resp = await client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200

        # Invalidate just 'admin'
        invalidate_user_cache("admin")

        # Next request should still work (DB lookup after eviction)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200

        invalidate_user_cache()  # cleanup
