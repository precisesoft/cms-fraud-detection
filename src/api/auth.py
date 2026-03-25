"""JWT authentication helpers and FastAPI dependencies."""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.api.deps import get_db
from src.api.schemas import UserResponse

__all__ = [
    "create_access_token",
    "get_current_user",
    "invalidate_user_cache",
    "require_admin",
    "verify_password",
]

JWT_SECRET = os.environ.get("JWT_SECRET_KEY", "argus-dev-secret-change-in-prod!")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

_bearer = HTTPBearer()

# ---------------------------------------------------------------------------
# In-memory user cache (avoids a DB query on every authenticated request)
# ---------------------------------------------------------------------------

_USER_CACHE_TTL = 30  # seconds
_user_cache: dict[str, tuple[UserResponse, float]] = {}


def invalidate_user_cache(username: str | None = None) -> None:
    """Drop cached user(s). Call on role/profile changes."""
    if username is None:
        _user_cache.clear()
    else:
        _user_cache.pop(username, None)


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(
    data: dict[str, object],
    expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(UTC) + timedelta(minutes=expires_minutes)
    token: str = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    conn: AsyncConnection = Depends(get_db),
) -> UserResponse:
    """Decode JWT and return the user. Raises 401 on any failure."""
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # Check in-memory cache first
    now = time.monotonic()
    cached = _user_cache.get(username)
    if cached is not None:
        user_resp, cached_at = cached
        if (now - cached_at) < _USER_CACHE_TTL:
            return user_resp

    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT id, username, role, full_name, is_active FROM users WHERE username = %s",
            (username,),
        )
        row = await cur.fetchone()

    if row is None or not row["is_active"]:
        _user_cache.pop(username, None)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    user_resp = UserResponse(
        id=row["id"],
        username=row["username"],
        role=row["role"],
        full_name=row["full_name"],
    )
    _user_cache[username] = (user_resp, now)
    return user_resp


async def require_admin(user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """FastAPI dependency — requires the caller to have the 'admin' role.

    Raises:
        HTTPException: 403 if the authenticated user is not an admin.
    """
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
