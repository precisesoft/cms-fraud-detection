"""Live Payment Monitor — persistent shared SSE stream.

Clients connect to /live/stream and receive events from a shared
server-side queue that runs independently of any single connection.
The queue is built once at startup with a curated 10K-event set
and loops forever, broadcasting to all connected SSE clients.

Endpoints:
  GET /live/stream    — SSE stream (shared broadcast)
  GET /live/status    — Queue status / health
  POST /live/tps      — Adjust emission rate
  POST /live/rebuild  — Force queue rebuild

NOTE: No auth on SSE stream — demo-scoped. Production: gate via Istio JWT policy.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from src.api.live_queue import queue_manager, start_queue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/live", tags=["live"])


async def _ensure_queue_started() -> None:
    """Start the shared queue lazily so API pod startup stays lightweight."""
    if not queue_manager.running:
        await start_queue()


# ---------------------------------------------------------------------------
# SSE stream — shared broadcast
# ---------------------------------------------------------------------------


@router.get("/stream")
async def stream_claims(
    tps: float = Query(default=0.0, ge=0.0, le=20.0),
):
    """Stream scored claims as Server-Sent Events.

    All clients receive the same event stream from the persistent
    server-side queue. The stream survives browser refresh and works
    across different user logins.

    If tps > 0, updates the server-wide emission rate.
    """
    await _ensure_queue_started()

    if tps > 0:
        queue_manager.set_tps(tps)

    sub = queue_manager.subscribe()

    async def event_generator():
        try:
            while True:
                try:
                    data = await asyncio.wait_for(sub.get(), timeout=30.0)
                    yield data
                except TimeoutError:
                    # Send keepalive comment to prevent proxy/browser timeout
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            queue_manager.unsubscribe(sub)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Control endpoints
# ---------------------------------------------------------------------------


@router.get("/status")
async def queue_status():
    """Return current queue status — size, position, TPS, subscribers."""
    await _ensure_queue_started()
    return queue_manager.status()


@router.post("/tps")
async def set_tps(tps: float = Query(ge=0.1, le=20.0)):
    """Adjust the server-wide emission rate."""
    await _ensure_queue_started()
    queue_manager.set_tps(tps)
    return {"tps": queue_manager.tps}


@router.post("/rebuild")
async def rebuild_queue():
    """Force a queue rebuild (re-queries DB, re-scores, reshuffles)."""
    was_running = queue_manager.running
    if was_running:
        await queue_manager.stop()
    await queue_manager.start()
    return queue_manager.status()
