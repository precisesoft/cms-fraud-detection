"""FastAPI application factory for CMS Fraud Detection API."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth import get_current_user
from src.api.deps import close_pool, open_pool
from src.api.graph_client import close_neo4j, open_neo4j


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup/shutdown of the async DB pool and Neo4j driver."""
    await open_pool()
    try:
        await open_neo4j()
    except Exception:
        pass  # Neo4j is optional — API works without it
    yield
    await close_neo4j()
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

    # --- Auth router (public — no token required) ---
    from src.api.routes.auth import router as auth_router

    app.include_router(auth_router, prefix="/api")

    # --- Protected routers (require valid JWT) ---
    _auth = [Depends(get_current_user)]

    from src.api.routes.cases import router as cases_router
    from src.api.routes.chat import router as chat_router
    from src.api.routes.claims import router as claims_router
    from src.api.routes.dashboard import router as dashboard_router
    from src.api.routes.fairness import router as fairness_router
    from src.api.routes.graph import router as graph_router
    from src.api.routes.network import router as network_router
    from src.api.routes.providers import router as providers_router
    from src.api.routes.score import router as score_router
    from src.api.routes.score_v2 import router as score_v2_router
    from src.api.routes.signals import router as signals_router
    from src.api.routes.simulate import router as simulate_router
    from src.api.routes.simulate_v2 import router as simulate_v2_router
    from src.api.routes.validation import router as validation_router

    app.include_router(providers_router, prefix="/api", dependencies=_auth)
    app.include_router(cases_router, prefix="/api", dependencies=_auth)
    app.include_router(claims_router, prefix="/api", dependencies=_auth)
    app.include_router(score_router, prefix="/api", dependencies=_auth)
    app.include_router(score_v2_router, prefix="/api", dependencies=_auth)
    app.include_router(simulate_router, prefix="/api", dependencies=_auth)
    app.include_router(simulate_v2_router, prefix="/api", dependencies=_auth)
    app.include_router(fairness_router, prefix="/api", dependencies=_auth)
    app.include_router(signals_router, prefix="/api", dependencies=_auth)
    app.include_router(dashboard_router, prefix="/api", dependencies=_auth)
    app.include_router(graph_router, prefix="/api", dependencies=_auth)
    app.include_router(network_router, prefix="/api", dependencies=_auth)
    app.include_router(chat_router, prefix="/api", dependencies=_auth)
    app.include_router(validation_router, prefix="/api", dependencies=_auth)

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

        graph_status = "ok"
        try:
            from src.api.graph_client import driver as neo4j_driver

            if neo4j_driver is None:
                raise RuntimeError("Neo4j driver not initialized")
            await neo4j_driver.verify_connectivity()
        except Exception:
            graph_status = "unavailable"

        return HealthResponse(status="ok", database=db_status, graph=graph_status, version="0.1.0")

    return app


app = create_app()
