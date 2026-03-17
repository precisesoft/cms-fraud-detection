"""FastAPI application factory for CMS Fraud Detection API."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.deps import close_pool, open_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup/shutdown of the async DB pool."""
    await open_pool()
    yield
    await close_pool()


def create_app() -> FastAPI:
    app = FastAPI(
        title="CMS Fraud Detection API",
        description="Proactive provider fraud detection with explainable AI",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tighten for prod
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Health endpoint (no router needed) ---
    from src.api.schemas import HealthResponse

    @app.get("/health", response_model=HealthResponse, tags=["ops"])
    async def health():
        db_status = "ok"
        try:
            from src.api.deps import pool

            if pool is None:
                raise RuntimeError("Pool not initialized")
            async with pool.connection() as conn:
                await conn.execute("SELECT 1")
        except Exception:
            db_status = "unavailable"
        return HealthResponse(status="ok", database=db_status, version="0.1.0")

    return app


app = create_app()
