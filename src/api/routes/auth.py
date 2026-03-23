"""Authentication endpoints: login and current-user info."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.api.auth import create_access_token, get_current_user, verify_password
from src.api.deps import get_db
from src.api.schemas import LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    conn: AsyncConnection = Depends(get_db),
) -> TokenResponse:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT id, username, hashed_password, role, full_name, is_active "
            "FROM users WHERE username = %s",
            (body.username,),
        )
        user = await cur.fetchone()

    if (
        user is None
        or not user["is_active"]
        or not verify_password(body.password, user["hashed_password"])
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_access_token({"sub": user["username"], "role": user["role"]})
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            username=user["username"],
            role=user["role"],
            full_name=user["full_name"],
        ),
    )


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    return current_user
