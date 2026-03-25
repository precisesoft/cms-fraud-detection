"""Ingest / pipeline-trigger endpoints.

Endpoints
---------
POST /ingest/upload          — Upload a raw CMS CSV (admin only)
GET  /ingest/sources         — List current source versions with freshness
POST /ingest/recalibrate     — Trigger full recalibration (admin only)
POST /ingest/retrain         — Retrain ML models + recalibrate (admin only)
GET  /ingest/runs            — List pipeline runs (paginated, newest first)
GET  /ingest/runs/{run_id}   — Single run with stage_results for progress polling
GET  /ingest/status          — Quick freshness summary for dashboard banner

Admin endpoints (upload, recalibrate, retrain) require the caller to hold the
``admin`` role; non-admin users receive a 403 response.

Recalibrate/retrain reject concurrent runs with 409 to prevent result
corruption when two callers race to start a pipeline simultaneously.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from math import ceil
from pathlib import Path
from typing import Annotated, Any

import psycopg
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from psycopg import AsyncConnection

from src.api.auth import require_admin
from src.api.deps import DATABASE_URL, get_db
from src.api.schemas import (
    IngestStatus,
    LastRecalibration,
    PaginationMeta,
    PipelineRunDetail,
    PipelineRunList,
    PipelineRunSummary,
    SourceVersion,
    UploadResponse,
    UserResponse,
)
from src.pipeline.column_maps import SOURCE_TYPES
from src.pipeline.orchestrator import recalibrate, retrain_and_recalibrate
from src.pipeline.raw_loader import LoadResult, load_raw_csv
from src.pipeline.synthetic import SYNTHETIC_VERSIONS, generate_all

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])

# ---------------------------------------------------------------------------
# Shared SQL fragments
# ---------------------------------------------------------------------------

_SELECT_RUN_COLS = """
    id, run_type, status, current_stage, progress_pct,
    source_versions, stage_results, error_message,
    started_at::text, completed_at::text, triggered_by
"""


def _row_to_detail(run: dict[str, Any]) -> PipelineRunDetail:
    return PipelineRunDetail(
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


def _row_to_summary(run: dict[str, Any]) -> PipelineRunSummary:
    return PipelineRunSummary(
        id=run["id"],
        run_type=run["run_type"],
        status=run["status"],
        progress_pct=float(run.get("progress_pct") or 0.0),
        started_at=run.get("started_at"),
        completed_at=run.get("completed_at"),
        triggered_by=run.get("triggered_by"),
    )


# ---------------------------------------------------------------------------
# Concurrency guard
# ---------------------------------------------------------------------------


async def _assert_no_running_pipeline(conn: AsyncConnection) -> None:
    """Raise 409 if a pipeline run is already in progress."""
    cur = await conn.execute("SELECT count(*) FROM pipeline_runs WHERE status = 'running'")
    row = await cur.fetchone()
    running: int = int(row[0]) if row else 0
    if running > 0:
        raise HTTPException(status_code=409, detail="A pipeline is already running")


# ---------------------------------------------------------------------------
# POST /ingest/upload — upload a raw CMS CSV file (admin only)
# ---------------------------------------------------------------------------


@router.post("/upload", response_model=UploadResponse, status_code=200)
async def upload_source(
    file: Annotated[UploadFile, File()],
    source_type: Annotated[SOURCE_TYPES, Form()],
    version: Annotated[str, Form()],
    user: UserResponse = Depends(require_admin),
) -> UploadResponse:
    """Upload a raw CMS CSV file and load it into the corresponding raw table.

    Only CSV files are accepted. The file is validated for required columns
    before loading. Returns row count, file hash, and any column warnings.
    """
    # Validate content type — only CSV
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=422, detail="Only CSV files are accepted (.csv extension required)"
        )

    # Save to a temp file so load_raw_csv (sync) can read it
    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        result: LoadResult = await asyncio.to_thread(
            _load_csv_sync,
            tmp_path,
            source_type,
            version,
            user.username,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    return UploadResponse(
        row_count=result.row_count,
        file_hash=result.file_hash,
        validation_warnings=result.validation_warnings,
        duplicate_detected=False,  # load_raw_csv is idempotent; no explicit dupe flag
    )


def _load_csv_sync(
    file_path: Path,
    source_type: str,
    version: str,
    uploaded_by: str,
) -> LoadResult:
    """Run load_raw_csv synchronously with a dedicated psycopg connection."""
    with psycopg.connect(DATABASE_URL) as conn:
        return load_raw_csv(file_path, source_type, version, conn, uploaded_by)


# ---------------------------------------------------------------------------
# GET /ingest/sources — list current source versions
# ---------------------------------------------------------------------------

_LIST_SOURCES_SQL = """
SELECT source_type, current_version, file_hash, row_count,
       uploaded_at::text, uploaded_by
FROM data_source_versions
ORDER BY source_type
"""


@router.get("/sources", response_model=list[SourceVersion])
async def list_sources(
    conn: AsyncConnection = Depends(get_db),
) -> list[SourceVersion]:
    """Return the current version of each loaded CMS data source."""
    cur = await conn.execute(_LIST_SOURCES_SQL)
    rows = await cur.fetchall()
    cols = [d[0] for d in (cur.description or [])]

    return [
        SourceVersion(
            type=row_dict["source_type"],
            version=row_dict["current_version"],
            file_hash=row_dict.get("file_hash"),
            row_count=row_dict.get("row_count"),
            uploaded_at=row_dict.get("uploaded_at"),
            uploaded_by=row_dict.get("uploaded_by"),
        )
        for row_dict in (dict(zip(cols, r)) for r in rows)
    ]


# ---------------------------------------------------------------------------
# POST /ingest/recalibrate — trigger recalibration (admin only)
# ---------------------------------------------------------------------------


@router.post("/recalibrate", response_model=PipelineRunDetail, status_code=202)
async def trigger_recalibrate(
    background_tasks: BackgroundTasks,
    user: UserResponse = Depends(require_admin),
    conn: AsyncConnection = Depends(get_db),
) -> PipelineRunDetail:
    """Start a full recalibration pipeline run in the background.

    Returns immediately with the new run ID so callers can poll
    ``GET /ingest/runs/{id}`` for progress. Returns 409 if a pipeline
    is already running.
    """
    await _assert_no_running_pipeline(conn)

    cur = await conn.execute(
        "INSERT INTO pipeline_runs (run_type, status, triggered_by, started_at) "
        "VALUES (%s, 'pending', %s, NOW()) RETURNING id",
        ("recalibration", user.username),
    )
    run_row = await cur.fetchone()
    if run_row is None:
        raise HTTPException(status_code=500, detail="Failed to create pipeline run record")
    run_id: int = int(run_row[0])
    await conn.commit()

    background_tasks.add_task(recalibrate, run_id, DATABASE_URL)
    logger.info("Recalibration run %d triggered by %s", run_id, user.username)

    return PipelineRunDetail(
        id=run_id,
        run_type="recalibration",
        status="pending",
        triggered_by=user.username,
    )


# ---------------------------------------------------------------------------
# POST /ingest/retrain — retrain ML models + recalibrate (admin only)
# ---------------------------------------------------------------------------


@router.post("/retrain", response_model=PipelineRunDetail, status_code=202)
async def trigger_retrain(
    background_tasks: BackgroundTasks,
    user: UserResponse = Depends(require_admin),
    conn: AsyncConnection = Depends(get_db),
) -> PipelineRunDetail:
    """Retrain ML models and run full recalibration in the background.

    Returns immediately with run ID for progress polling. Returns 409
    if a pipeline is already running.
    """
    await _assert_no_running_pipeline(conn)

    cur = await conn.execute(
        "INSERT INTO pipeline_runs (run_type, status, triggered_by, started_at) "
        "VALUES (%s, 'pending', %s, NOW()) RETURNING id",
        ("retrain_and_recalibrate", user.username),
    )
    run_row = await cur.fetchone()
    if run_row is None:
        raise HTTPException(status_code=500, detail="Failed to create pipeline run record")
    run_id: int = int(run_row[0])
    await conn.commit()

    background_tasks.add_task(retrain_and_recalibrate, run_id, DATABASE_URL)
    logger.info("Retrain+recalibrate run %d triggered by %s", run_id, user.username)

    return PipelineRunDetail(
        id=run_id,
        run_type="retrain_and_recalibrate",
        status="pending",
        triggered_by=user.username,
    )


# ---------------------------------------------------------------------------
# POST /ingest/seed — generate synthetic data + recalibrate (admin only)
# ---------------------------------------------------------------------------


def _seed_synthetic_sync(run_id: int, db_url: str) -> None:
    """Generate synthetic CSVs, load into raw tables, then run recalibration.

    Runs synchronously — designed to be called via ``asyncio.to_thread``.
    """
    import csv
    import json

    from src.pipeline.orchestrator import _run_recalibrate_sync, update_stage

    with psycopg.connect(db_url) as conn:
        # --- Stage: data_generation ---
        update_stage(
            conn,
            run_id,
            "data_generation",
            "running",
            {},
            progress_pct=0,
            stage_results=[],
        )
        ds = generate_all()
        gen_metrics = {
            "providers": len(ds.providers),
            "service_rows": len(ds.service_rows),
            "provider_rows": len(ds.provider_rows),
            "enrollment_rows": len(ds.enrollment_rows),
            "revocation_rows": len(ds.revocation_rows),
        }
        stage_records: list[dict[str, Any]] = [
            {"stage": "data_generation", "status": "completed", "metrics": gen_metrics},
        ]
        update_stage(
            conn,
            run_id,
            "data_generation",
            "running",
            gen_metrics,
            progress_pct=5,
            stage_results=stage_records,
        )

        # --- Stage: data_loading ---
        update_stage(
            conn,
            run_id,
            "data_loading",
            "running",
            {},
            progress_pct=5,
            stage_results=stage_records,
        )
        sources = [
            ("part_b_service", ds.service_rows, SYNTHETIC_VERSIONS["part_b_service"]),
            ("part_b_provider", ds.provider_rows, SYNTHETIC_VERSIONS["part_b_provider"]),
            ("enrollment", ds.enrollment_rows, SYNTHETIC_VERSIONS["enrollment"]),
            ("revocations", ds.revocation_rows, SYNTHETIC_VERSIONS["revocations"]),
        ]
        load_metrics: dict[str, Any] = {}
        for source_type, rows, version in sources:
            if not rows:
                continue
            # Write to temp CSV
            tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", newline="")
            writer = csv.DictWriter(tmp, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
            tmp.close()
            result = load_raw_csv(Path(tmp.name), source_type, version, conn, "seed_synthetic")
            Path(tmp.name).unlink(missing_ok=True)
            load_metrics[source_type] = result.row_count

        stage_records.append(
            {"stage": "data_loading", "status": "completed", "metrics": load_metrics},
        )
        update_stage(
            conn,
            run_id,
            "data_loading",
            "running",
            load_metrics,
            progress_pct=20,
            stage_results=stage_records,
        )

        # Store source versions on the run record
        conn.execute(
            "UPDATE pipeline_runs SET source_versions = %s::jsonb WHERE id = %s",
            (json.dumps(SYNTHETIC_VERSIONS), run_id),
        )
        conn.commit()

    # --- Stages 1-6: recalibration pipeline ---
    _run_recalibrate_sync(run_id, db_url)


async def _seed_synthetic_background(run_id: int, db_url: str) -> None:
    """Async wrapper for the seed-synthetic background task."""
    try:
        await asyncio.to_thread(_seed_synthetic_sync, run_id, db_url)
    except Exception as exc:
        logger.exception("[%s] Seed synthetic pipeline failed", run_id)
        try:
            with psycopg.connect(db_url) as conn:
                conn.execute(
                    "UPDATE pipeline_runs SET status='failed', error_message=%s, "
                    "completed_at=NOW() WHERE id=%s",
                    (str(exc), run_id),
                )
                conn.commit()
        except Exception:
            logger.exception("[%s] Failed to update run status after seed failure", run_id)


@router.post("/seed", response_model=PipelineRunDetail, status_code=202)
async def seed_synthetic_data(
    background_tasks: BackgroundTasks,
    user: UserResponse = Depends(require_admin),
    conn: AsyncConnection = Depends(get_db),
) -> PipelineRunDetail:
    """Generate synthetic CMS data and run full recalibration pipeline.

    Creates 250 synthetic providers across 4 specialties, loads them into
    the raw tables, and triggers a complete 6-stage recalibration. Progress
    is tracked in ``pipeline_runs`` and can be polled via
    ``GET /ingest/runs/{id}``.
    """
    await _assert_no_running_pipeline(conn)

    cur = await conn.execute(
        "INSERT INTO pipeline_runs (run_type, status, triggered_by, started_at) "
        "VALUES (%s, 'running', %s, NOW()) RETURNING id",
        ("seed_synthetic", user.username),
    )
    run_row = await cur.fetchone()
    if run_row is None:
        raise HTTPException(status_code=500, detail="Failed to create pipeline run record")
    run_id: int = int(run_row[0])
    await conn.commit()

    background_tasks.add_task(_seed_synthetic_background, run_id, DATABASE_URL)
    logger.info("Seed synthetic run %d triggered by %s", run_id, user.username)

    return PipelineRunDetail(
        id=run_id,
        run_type="seed_synthetic",
        status="running",
        triggered_by=user.username,
    )


# ---------------------------------------------------------------------------
# GET /ingest/runs — paginated list of pipeline runs
# ---------------------------------------------------------------------------

_COUNT_RUNS_SQL = "SELECT count(*) FROM pipeline_runs"

_LIST_RUNS_SQL = f"""
SELECT {_SELECT_RUN_COLS}
FROM pipeline_runs
ORDER BY started_at DESC
LIMIT %s OFFSET %s
"""


@router.get("/runs", response_model=PipelineRunList)
async def list_pipeline_runs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    conn: AsyncConnection = Depends(get_db),
) -> PipelineRunList:
    """List recent pipeline runs, newest first (paginated)."""
    count_cur = await conn.execute(_COUNT_RUNS_SQL)
    count_row = await count_cur.fetchone()
    total: int = int(count_row[0]) if count_row else 0

    offset = (page - 1) * per_page
    cur = await conn.execute(_LIST_RUNS_SQL, (per_page, offset))
    rows = await cur.fetchall()
    cols = [d[0] for d in (cur.description or [])]

    summaries = [_row_to_summary(dict(zip(cols, r))) for r in rows]

    return PipelineRunList(
        data=summaries,
        meta=PaginationMeta(
            total=total,
            page=page,
            per_page=per_page,
            pages=ceil(total / per_page) if per_page else 1,
        ),
    )


# ---------------------------------------------------------------------------
# GET /ingest/runs/{run_id} — single run with stage_results
# ---------------------------------------------------------------------------

_GET_RUN_SQL = f"""
SELECT {_SELECT_RUN_COLS}
FROM pipeline_runs
WHERE id = %s
"""


@router.get("/runs/{run_id}", response_model=PipelineRunDetail)
async def get_pipeline_run(
    run_id: int,
    conn: AsyncConnection = Depends(get_db),
) -> PipelineRunDetail:
    """Return the current status of a pipeline run including per-stage results.

    The frontend polls this endpoint every 2 seconds to display real-time
    pipeline progress.
    """
    cur = await conn.execute(_GET_RUN_SQL, (run_id,))
    row = await cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")

    cols = [d[0] for d in (cur.description or [])]
    return _row_to_detail(dict(zip(cols, row)))


# ---------------------------------------------------------------------------
# GET /ingest/status — quick freshness summary for dashboard banner
# ---------------------------------------------------------------------------

_STATUS_SQL = """
SELECT
    (SELECT count(*) FROM provider_features)::int                     AS providers_in_system,
    (SELECT id          FROM pipeline_runs WHERE status = 'completed'
     ORDER BY completed_at DESC LIMIT 1)                              AS last_run_id,
    (SELECT run_type    FROM pipeline_runs WHERE status = 'completed'
     ORDER BY completed_at DESC LIMIT 1)                              AS last_run_type,
    (SELECT completed_at::text FROM pipeline_runs WHERE status = 'completed'
     ORDER BY completed_at DESC LIMIT 1)                              AS last_completed_at,
    (SELECT status      FROM pipeline_runs WHERE status = 'completed'
     ORDER BY completed_at DESC LIMIT 1)                              AS last_run_status
"""

_SOURCES_SQL = """
SELECT source_type, current_version, file_hash, row_count,
       uploaded_at::text, uploaded_by
FROM data_source_versions
ORDER BY source_type
"""


@router.get("/status", response_model=IngestStatus)
async def ingest_status(
    conn: AsyncConnection = Depends(get_db),
) -> IngestStatus:
    """Quick freshness summary for the dashboard banner.

    Returns current source versions, last recalibration run metadata,
    and total number of providers scored in the system.
    """
    # Fetch aggregate status
    cur = await conn.execute(_STATUS_SQL)
    row = await cur.fetchone()
    cols = [d[0] for d in (cur.description or [])]
    stat = dict(zip(cols, row)) if row else {}

    providers_in_system: int = int(stat.get("providers_in_system") or 0)

    last_recalibration: LastRecalibration | None = None
    if stat.get("last_run_id") is not None:
        last_recalibration = LastRecalibration(
            run_id=int(stat["last_run_id"]),
            completed_at=stat.get("last_completed_at"),
            providers_scored=providers_in_system or None,
            status=str(stat.get("last_run_status") or "completed"),
        )

    # Fetch source versions
    src_cur = await conn.execute(_SOURCES_SQL)
    src_rows = await src_cur.fetchall()
    src_cols = [d[0] for d in (src_cur.description or [])]

    sources = [
        SourceVersion(
            type=r["source_type"],
            version=r["current_version"],
            file_hash=r.get("file_hash"),
            row_count=r.get("row_count"),
            uploaded_at=r.get("uploaded_at"),
            uploaded_by=r.get("uploaded_by"),
        )
        for r in (dict(zip(src_cols, row)) for row in src_rows)
    ]

    return IngestStatus(
        sources=sources,
        last_recalibration=last_recalibration,
        providers_in_system=providers_in_system,
    )
