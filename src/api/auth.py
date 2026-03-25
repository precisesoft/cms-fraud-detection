"""JWT authentication helpers and FastAPI dependencies."""

from __future__ import annotations

import os
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
    "require_admin",
    "verify_password",
]

JWT_SECRET = os.environ.get("JWT_SECRET_KEY", "argus-dev-secret-change-in-prod!")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

_bearer = HTTPBearer()


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

    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT id, username, role, full_name, is_active FROM users WHERE username = %s",
            (username,),
        )
        row = await cur.fetchone()

    if row is None or not row["is_active"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return UserResponse(
        id=row["id"],
        username=row["username"],
        role=row["role"],
        full_name=row["full_name"],
    )


async def require_admin(user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """FastAPI dependency — requires the caller to have the 'admin' role.

    Raises:
        HTTPException: 403 if the authenticated user is not an admin.
    """
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
