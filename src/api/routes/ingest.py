"""Ingest / pipeline-trigger endpoints.

Provides three endpoints:

* ``POST /ingest/runs``          — trigger a new pipeline run (background task)
* ``GET  /ingest/runs``          — list recent pipeline runs
* ``GET  /ingest/runs/{run_id}`` — poll progress of a specific run

The frontend polls ``GET /api/ingest/runs/{id}`` every 2 seconds to show
real-time progress.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from psycopg import AsyncConnection
from pydantic import BaseModel, Field

from src.api.deps import DATABASE_URL, get_db
from src.pipeline.orchestrator import recalibrate, retrain_and_recalibrate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class TriggerRunRequest(BaseModel):
    """Request body for triggering a new pipeline run."""

    run_type: Literal["recalibration", "retrain_and_recalibrate"] = Field(
        default="recalibration",
        description="Which pipeline to execute.",
    )
    triggered_by: str = Field(
        default="api",
        max_length=100,
        description="Identifier of the user or system that triggered the run.",
    )


class PipelineRunResponse(BaseModel):
    """Serialised view of a ``pipeline_runs`` row."""

    id: int
    run_type: str
    status: str
    current_stage: str | None = None
    progress_pct: float = 0.0
    source_versions: dict[str, Any] = Field(default_factory=dict)
    stage_results: list[dict[str, Any]] = Field(default_factory=list)
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    triggered_by: str | None = None


# ---------------------------------------------------------------------------
# POST /ingest/runs — trigger a new pipeline run
# ---------------------------------------------------------------------------


@router.post("/runs", response_model=PipelineRunResponse, status_code=202)
async def trigger_pipeline_run(
    body: TriggerRunRequest,
    background_tasks: BackgroundTasks,
    conn: AsyncConnection = Depends(get_db),
) -> PipelineRunResponse:
    """Trigger a new recalibration pipeline run.

    Inserts a ``pipeline_runs`` record, fires a background task, and returns
    immediately with the new run's ID so the caller can poll for progress.
    """
    cur = await conn.execute(
        "INSERT INTO pipeline_runs (run_type, status, triggered_by, started_at) "
        "VALUES (%s, 'pending', %s, NOW()) RETURNING id",
        (body.run_type, body.triggered_by),
    )
    run_row = await cur.fetchone()
    if run_row is None:
        raise HTTPException(status_code=500, detail="Failed to create pipeline run record")
    run_id: int = int(run_row[0])
    await conn.commit()

    # Choose the pipeline function based on run_type
    if body.run_type == "retrain_and_recalibrate":
        pipeline_fn = retrain_and_recalibrate
    else:
        pipeline_fn = recalibrate

    background_tasks.add_task(pipeline_fn, run_id, DATABASE_URL)

    logger.info("Pipeline run %d (%s) triggered by %s", run_id, body.run_type, body.triggered_by)

    return PipelineRunResponse(
        id=run_id,
        run_type=body.run_type,
        status="pending",
        triggered_by=body.triggered_by,
    )


# ---------------------------------------------------------------------------
# GET /ingest/runs/{run_id} — poll a specific run
# ---------------------------------------------------------------------------

_GET_RUN_SQL = """
SELECT id, run_type, status, current_stage, progress_pct,
       source_versions, stage_results, error_message,
       started_at::text, completed_at::text, triggered_by
FROM pipeline_runs
WHERE id = %s
"""


@router.get("/runs/{run_id}", response_model=PipelineRunResponse)
async def get_pipeline_run(
    run_id: int,
    conn: AsyncConnection = Depends(get_db),
) -> PipelineRunResponse:
    """Return the current status of a pipeline run.

    The frontend polls this endpoint every 2 seconds to display real-time
    pipeline progress.
    """
    cur = await conn.execute(_GET_RUN_SQL, (run_id,))
    row = await cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")

    cols = [d[0] for d in (cur.description or [])]
    run = dict(zip(cols, row))

    return PipelineRunResponse(
        id=run["id"],
        run_type=run["run_type"],
        status=run["status"],
        current_stage=run.get("current_stage"),
        progress_pct=float(run.get("progress_pct") or 0.0),
        source_versions=run.get("source_versions") or {},
        stage_results=run.get("stage_results") or [],
        error_message=run.get("error_message"),
        started_at=run.get("started_at"),
        completed_at=run.get("completed_at"),
        triggered_by=run.get("triggered_by"),
    )


# ---------------------------------------------------------------------------
# GET /ingest/runs — list recent runs
# ---------------------------------------------------------------------------

_LIST_RUNS_SQL = """
SELECT id, run_type, status, current_stage, progress_pct,
       source_versions, stage_results, error_message,
       started_at::text, completed_at::text, triggered_by
FROM pipeline_runs
ORDER BY started_at DESC
LIMIT %s
"""


@router.get("/runs", response_model=list[PipelineRunResponse])
async def list_pipeline_runs(
    limit: int = Query(20, ge=1, le=100),
    conn: AsyncConnection = Depends(get_db),
) -> list[PipelineRunResponse]:
    """List recent pipeline runs, newest first."""
    cur = await conn.execute(_LIST_RUNS_SQL, (limit,))
    rows = await cur.fetchall()
    cols = [d[0] for d in (cur.description or [])]

    runs = []
    for row in rows:
        run = dict(zip(cols, row))
        runs.append(
            PipelineRunResponse(
                id=run["id"],
                run_type=run["run_type"],
                status=run["status"],
                current_stage=run.get("current_stage"),
                progress_pct=float(run.get("progress_pct") or 0.0),
                source_versions=run.get("source_versions") or {},
                stage_results=run.get("stage_results") or [],
                error_message=run.get("error_message"),
                started_at=run.get("started_at"),
                completed_at=run.get("completed_at"),
                triggered_by=run.get("triggered_by"),
            )
        )
    return runs
