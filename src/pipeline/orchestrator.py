"""Pipeline orchestrator — drives the 6-stage recalibration pipeline.

Updates ``pipeline_runs`` at each stage so the frontend can track real-time
progress.  Designed to run as a FastAPI ``BackgroundTask`` (fire-and-forget).

Stages
------
1. ingest          — join raw sources → provider_service_cases (temp)
2. peer_baselines  — state + national peer statistics
3. z_scores        — 4 peer-comparison z-scores
4. seed_scoring    — rules-based risk/legitimacy labels → provider_service_cases
5. provider_profiles — feature engineering → provider_features upsert
6. ml_scoring      — IsolationForest + weak-supervised bulk scoring → observation_model_scores
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://cms:cms_local_dev@172.16.0.191:30432/cms_fraud",
)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class StageRecord:
    """Serialisable record for one completed pipeline stage."""

    stage: str
    status: str  # "completed" | "failed" | "skipped"
    metrics: dict[str, Any] = field(default_factory=dict)
    started_at: str = ""
    completed_at: str = ""
    error: str | None = None


@dataclass
class PipelineResult:
    """Final outcome of a pipeline run."""

    run_id: int
    status: str  # "completed" | "failed"
    stages: list[StageRecord] = field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# Sync DB helpers (used inside asyncio.to_thread)
# ---------------------------------------------------------------------------


def create_pipeline_run(conn: Any, run_type: str, triggered_by: str) -> int:
    """Insert a new ``pipeline_runs`` row and return the generated run_id."""
    row = conn.execute(
        """
        INSERT INTO pipeline_runs (run_type, status, triggered_by, started_at)
        VALUES (%s, %s, %s, NOW())
        RETURNING id
        """,
        (run_type, "running", triggered_by),
    ).fetchone()
    conn.commit()
    return int(row[0])


def update_stage(
    conn: Any,
    run_id: int,
    stage: str,
    status: str,
    metrics: dict[str, Any],
    *,
    progress_pct: float,
    stage_results: list[dict[str, Any]],
    error_message: str | None = None,
) -> None:
    """Update ``pipeline_runs`` with stage progress information.

    Args:
        conn: Open sync psycopg connection.
        run_id: The pipeline run to update.
        stage: Name of the current stage.
        status: Overall pipeline status (``'running'``, ``'completed'``, ``'failed'``).
        metrics: Stage-level metrics dict (stored in ``stage_results`` JSONB).
        progress_pct: Cumulative pipeline progress (0–100).
        stage_results: Current accumulated list of stage result objects.
        error_message: Optional error message on failure.
    """
    conn.execute(
        """
        UPDATE pipeline_runs
        SET current_stage  = %s,
            status         = %s,
            progress_pct   = %s,
            stage_results  = %s::jsonb,
            error_message  = %s,
            completed_at   = CASE WHEN %s IN ('completed', 'failed') THEN NOW() ELSE NULL END
        WHERE id = %s
        """,
        (
            stage,
            status,
            progress_pct,
            json.dumps(stage_results),
            error_message,
            status,
            run_id,
        ),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Stage 6 — Bulk ML scoring
# ---------------------------------------------------------------------------


def _bulk_ml_scoring(conn: Any, run_id: int) -> dict[str, Any]:
    """Bulk-score all providers and observations, write to observation_model_scores.

    1. Reads ``provider_features`` → IsolationForest anomaly scores.
    2. Reads ``bridge_training_examples_v`` → weak-supervised fraud probabilities.
    3. Computes composite scores.
    4. Bulk-INSERTs all scored rows into ``observation_model_scores``.

    Returns a metrics dict.
    """
    import polars as pl

    from src.models.anomaly_scorer import _load_bundle as _load_anomaly_bundle
    from src.models.anomaly_scorer import score_provider
    from src.models.weak_supervised import _load_bundle as _load_ws_bundle
    from src.models.weak_supervised import (
        build_feature_row,
        compute_composite_score,
        score_observation,
    )

    # --- Determine model versions ---
    anomaly_model_version = "unknown"
    ws_model_version = "unknown"

    try:
        ab = _load_anomaly_bundle()
        anomaly_model_version = ab.get("metadata", {}).get(  # type: ignore[union-attr]
            "model_version", "v1"
        )
    except Exception:
        logger.debug("Could not load anomaly model metadata", exc_info=True)

    try:
        wb = _load_ws_bundle()
        ws_model_version = wb.get("metadata", {}).get(  # type: ignore[union-attr]
            "model_version", "v1"
        )
    except Exception:
        logger.debug("Could not load weak-supervised model metadata", exc_info=True)

    # --- Score providers (IsolationForest) ---
    pf_cur = conn.execute("SELECT * FROM provider_features")
    provider_rows: list[Any] = pf_cur.fetchall()
    # fetchall() with default row_factory returns tuples; we need dicts.
    # Use dict_row if available, otherwise fall back to manual mapping.
    pf_cols = [desc[0] for desc in (pf_cur.description or [])]
    provider_dicts = [dict(zip(pf_cols, row)) for row in provider_rows]

    providers_scored = 0
    anomaly_scores: list[float] = []
    provider_score_map: dict[str, float | None] = {}

    for prow in provider_dicts:
        score = score_provider(prow)
        provider_score_map[prow.get("npi", "")] = score
        if score is not None:
            anomaly_scores.append(score)
            providers_scored += 1

    # --- Score observations (weak-supervised) via bridge_training_examples_v ---
    obs_cur = conn.execute("SELECT * FROM bridge_training_examples_v")
    obs_rows: list[Any] = obs_cur.fetchall()
    obs_cols = [desc[0] for desc in (obs_cur.description or [])]
    obs_dicts = [dict(zip(obs_cols, row)) for row in obs_rows]

    observations_scored = 0
    composite_scores: list[float] = []

    scored_obs: list[dict[str, Any]] = []
    for orow in obs_dicts:
        # observation_id is the case_id alias in the view
        case_id = orow.get("observation_id") or orow.get("case_id")
        npi = orow.get("npi")
        if not case_id or not npi:
            continue

        feature_row = build_feature_row(orow)
        learned = score_observation(orow)
        composite, label = compute_composite_score(feature_row, learned)

        scored_obs.append(
            {
                "case_id": case_id,
                "npi": npi,
                "model_name": "weak_supervised_k8s_model",
                "model_version": ws_model_version,
                "predicted_probability": round(float(learned), 1) if learned is not None else None,
                "composite_score": round(float(composite), 1),
                "risk_label": str(label),
                "score_metadata": json.dumps({"anomaly_score": provider_score_map.get(npi)}),
            }
        )
        composite_scores.append(float(composite))
        observations_scored += 1

    # --- Bulk INSERT into observation_model_scores (append-only) ---
    if scored_obs:
        csv_buf = io.StringIO()
        pl.DataFrame(scored_obs).write_csv(csv_buf)
        csv_buf.seek(0)
        csv_buf.readline()  # skip header

        copy_sql = (
            "COPY observation_model_scores "
            "(case_id, npi, model_name, model_version, predicted_probability, "
            "composite_score, risk_label, score_metadata) "
            "FROM STDIN WITH (FORMAT CSV, NULL '')"
        )
        with conn.cursor().copy(copy_sql) as copy:
            while True:
                chunk = csv_buf.read(65536)
                if not chunk:
                    break
                copy.write(chunk)

    conn.commit()

    anomaly_mean = round(sum(anomaly_scores) / len(anomaly_scores), 2) if anomaly_scores else None
    composite_mean = (
        round(sum(composite_scores) / len(composite_scores), 2) if composite_scores else None
    )

    return {
        "providers_scored": providers_scored,
        "observations_scored": observations_scored,
        "model_versions": {
            "isolation_forest": anomaly_model_version,
            "weak_supervised": ws_model_version,
        },
        "anomaly_mean": anomaly_mean,
        "composite_mean": composite_mean,
    }


# ---------------------------------------------------------------------------
# Core sync pipeline runner (runs inside asyncio.to_thread)
# ---------------------------------------------------------------------------


def _run_recalibrate_sync(run_id: int, db_url: str) -> PipelineResult:
    """Synchronous implementation of the 6-stage recalibration pipeline.

    This function is intended to be called via ``asyncio.to_thread`` so it
    does not block the asyncio event loop.
    """
    import psycopg

    from src.pipeline.build_features import (
        build_provider_features_from_db,
        upsert_provider_features,
    )
    from src.pipeline.etl import (
        SourceVersions,
        run_stage_ingest,
        run_stage_peer_baselines,
        run_stage_seed_scoring,
        run_stage_zscores,
    )
    from src.pipeline.stages import ORDERED_STAGES, STAGE_WEIGHTS, PipelineStage

    stages_completed: list[StageRecord] = []
    accumulated_weight = 0.0

    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def _progress_after(stage: PipelineStage) -> float:
        return min(
            100.0,
            accumulated_weight + STAGE_WEIGHTS[stage],
        )

    def _append_stage(
        stage_name: str,
        status: str,
        metrics: dict[str, Any],
        started: str,
        error: str | None = None,
    ) -> dict[str, Any]:
        rec = {
            "stage": stage_name,
            "status": status,
            "metrics": metrics,
            "started_at": started,
            "completed_at": _now(),
        }
        if error:
            rec["error"] = error
        stages_completed.append(StageRecord(**rec))  # type: ignore[arg-type]
        return rec

    with psycopg.connect(db_url) as conn:
        # --- Determine which stages already completed (retry support) ---
        run_row = conn.execute(
            "SELECT stage_results FROM pipeline_runs WHERE id = %s",
            (run_id,),
        ).fetchone()

        existing_stage_results: list[dict[str, Any]] = []
        already_done: set[str] = set()
        if run_row and run_row[0]:
            raw = run_row[0]
            existing_stage_results = raw if isinstance(raw, list) else json.loads(raw)
            for rec in existing_stage_results:
                if rec.get("status") == "completed":
                    already_done.add(rec["stage"])
                    # Re-count progress for already-completed stages
                    for ps in ORDERED_STAGES:
                        if ps.value == rec["stage"]:
                            accumulated_weight += STAGE_WEIGHTS[ps]
                            break

        stage_records_json: list[dict[str, Any]] = list(existing_stage_results)

        # --- Fetch current source versions ---
        version_rows = conn.execute(
            "SELECT source_type, current_version FROM data_source_versions"
        ).fetchall()
        versions_map = {r[0]: r[1] for r in version_rows}

        source_versions = SourceVersions(
            service=versions_map.get("part_b_service", versions_map.get("service", "demo")),
            provider=versions_map.get("part_b_provider", versions_map.get("provider", "demo")),
            enrollment=versions_map.get("enrollment", "demo"),
            revocations=versions_map.get("revocations", "demo"),
        )

        # ----------------------------------------------------------------
        # Stage 1 — Ingest
        # ----------------------------------------------------------------
        stage = PipelineStage.INGEST
        if stage.value not in already_done:
            stage_start = _now()
            update_stage(
                conn,
                run_id,
                stage.value,
                "running",
                {},
                progress_pct=accumulated_weight,
                stage_results=stage_records_json,
            )
            try:
                result = run_stage_ingest(conn, source_versions, run_id=str(run_id))
                metrics: dict[str, Any] = {
                    "base_records": result.row_count,
                    "sources_joined": 4,
                    "source_versions": {
                        "service": source_versions.service,
                        "provider": source_versions.provider,
                        "enrollment": source_versions.enrollment,
                        "revocations": source_versions.revocations,
                    },
                }
            except Exception as exc:
                logger.exception("[%s] Stage ingest failed", run_id)
                rec = _append_stage(stage.value, "failed", {}, stage_start, error=str(exc))
                stage_records_json.append(rec)  # type: ignore[arg-type]
                update_stage(
                    conn,
                    run_id,
                    stage.value,
                    "failed",
                    {},
                    progress_pct=accumulated_weight,
                    stage_results=stage_records_json,
                    error_message=f"Stage {stage.value} failed: {exc}",
                )
                return PipelineResult(
                    run_id=run_id,
                    status="failed",
                    stages=stages_completed,
                    error=str(exc),
                )
            accumulated_weight = _progress_after(stage)
            rec = _append_stage(stage.value, "completed", metrics, stage_start)
            stage_records_json.append(rec)  # type: ignore[arg-type]
            update_stage(
                conn,
                run_id,
                stage.value,
                "running",
                metrics,
                progress_pct=accumulated_weight,
                stage_results=stage_records_json,
            )

        # ----------------------------------------------------------------
        # Stage 2 — Peer baselines
        # ----------------------------------------------------------------
        stage = PipelineStage.PEER_BASELINES
        if stage.value not in already_done:
            stage_start = _now()
            update_stage(
                conn,
                run_id,
                stage.value,
                "running",
                {},
                progress_pct=accumulated_weight,
                stage_results=stage_records_json,
            )
            try:
                result = run_stage_peer_baselines(conn, run_id=str(run_id))
                extra = result.extra
                metrics = {
                    "state_groups": extra.get("n_state_groups", 0),
                    "national_fallback_groups": extra.get("n_national_groups", 0),
                }
            except Exception as exc:
                logger.exception("[%s] Stage peer_baselines failed", run_id)
                rec = _append_stage(stage.value, "failed", {}, stage_start, error=str(exc))
                stage_records_json.append(rec)  # type: ignore[arg-type]
                update_stage(
                    conn,
                    run_id,
                    stage.value,
                    "failed",
                    {},
                    progress_pct=accumulated_weight,
                    stage_results=stage_records_json,
                    error_message=f"Stage {stage.value} failed: {exc}",
                )
                return PipelineResult(
                    run_id=run_id,
                    status="failed",
                    stages=stages_completed,
                    error=str(exc),
                )
            accumulated_weight = _progress_after(stage)
            rec = _append_stage(stage.value, "completed", metrics, stage_start)
            stage_records_json.append(rec)  # type: ignore[arg-type]
            update_stage(
                conn,
                run_id,
                stage.value,
                "running",
                metrics,
                progress_pct=accumulated_weight,
                stage_results=stage_records_json,
            )

        # ----------------------------------------------------------------
        # Stage 3 — Z-scores
        # ----------------------------------------------------------------
        stage = PipelineStage.Z_SCORES
        if stage.value not in already_done:
            stage_start = _now()
            update_stage(
                conn,
                run_id,
                stage.value,
                "running",
                {},
                progress_pct=accumulated_weight,
                stage_results=stage_records_json,
            )
            try:
                result = run_stage_zscores(conn, run_id=str(run_id))
                metrics = {
                    "cases_scored": result.row_count,
                    "dimensions": ["volume", "intensity", "charge", "payment"],
                }
            except Exception as exc:
                logger.exception("[%s] Stage z_scores failed", run_id)
                rec = _append_stage(stage.value, "failed", {}, stage_start, error=str(exc))
                stage_records_json.append(rec)  # type: ignore[arg-type]
                update_stage(
                    conn,
                    run_id,
                    stage.value,
                    "failed",
                    {},
                    progress_pct=accumulated_weight,
                    stage_results=stage_records_json,
                    error_message=f"Stage {stage.value} failed: {exc}",
                )
                return PipelineResult(
                    run_id=run_id,
                    status="failed",
                    stages=stages_completed,
                    error=str(exc),
                )
            accumulated_weight = _progress_after(stage)
            rec = _append_stage(stage.value, "completed", metrics, stage_start)
            stage_records_json.append(rec)  # type: ignore[arg-type]
            update_stage(
                conn,
                run_id,
                stage.value,
                "running",
                metrics,
                progress_pct=accumulated_weight,
                stage_results=stage_records_json,
            )

        # ----------------------------------------------------------------
        # Stage 4 — Seed scoring
        # ----------------------------------------------------------------
        stage = PipelineStage.SEED_SCORING
        if stage.value not in already_done:
            stage_start = _now()
            update_stage(
                conn,
                run_id,
                stage.value,
                "running",
                {},
                progress_pct=accumulated_weight,
                stage_results=stage_records_json,
            )
            try:
                result = run_stage_seed_scoring(conn, run_id=str(run_id))
                label_counts: dict[str, int] = result.extra.get("label_counts", {})
                metrics = {
                    "high_risk": label_counts.get("high_risk", 0),
                    "review": label_counts.get("review", 0),
                    "stable": label_counts.get("stable", 0),
                    "cases_upserted": result.row_count,
                }
            except Exception as exc:
                logger.exception("[%s] Stage seed_scoring failed", run_id)
                rec = _append_stage(stage.value, "failed", {}, stage_start, error=str(exc))
                stage_records_json.append(rec)  # type: ignore[arg-type]
                update_stage(
                    conn,
                    run_id,
                    stage.value,
                    "failed",
                    {},
                    progress_pct=accumulated_weight,
                    stage_results=stage_records_json,
                    error_message=f"Stage {stage.value} failed: {exc}",
                )
                return PipelineResult(
                    run_id=run_id,
                    status="failed",
                    stages=stages_completed,
                    error=str(exc),
                )
            accumulated_weight = _progress_after(stage)
            rec = _append_stage(stage.value, "completed", metrics, stage_start)
            stage_records_json.append(rec)  # type: ignore[arg-type]
            update_stage(
                conn,
                run_id,
                stage.value,
                "running",
                metrics,
                progress_pct=accumulated_weight,
                stage_results=stage_records_json,
            )

        # ----------------------------------------------------------------
        # Stage 5 — Provider profiles (feature engineering)
        # ----------------------------------------------------------------
        stage = PipelineStage.PROVIDER_PROFILES
        if stage.value not in already_done:
            stage_start = _now()
            update_stage(
                conn,
                run_id,
                stage.value,
                "running",
                {},
                progress_pct=accumulated_weight,
                stage_results=stage_records_json,
            )
            try:
                features_df = build_provider_features_from_db(conn)
                upsert_result = upsert_provider_features(features_df, conn, run_id=run_id)
                metrics = {
                    "providers_built": features_df.shape[0],
                    "feature_groups": 6,
                    "rows_inserted": upsert_result.rows_inserted,
                    "rows_updated": upsert_result.rows_updated,
                    "rows_unchanged": upsert_result.rows_unchanged,
                }
            except Exception as exc:
                logger.exception("[%s] Stage provider_profiles failed", run_id)
                rec = _append_stage(stage.value, "failed", {}, stage_start, error=str(exc))
                stage_records_json.append(rec)  # type: ignore[arg-type]
                update_stage(
                    conn,
                    run_id,
                    stage.value,
                    "failed",
                    {},
                    progress_pct=accumulated_weight,
                    stage_results=stage_records_json,
                    error_message=f"Stage {stage.value} failed: {exc}",
                )
                return PipelineResult(
                    run_id=run_id,
                    status="failed",
                    stages=stages_completed,
                    error=str(exc),
                )
            accumulated_weight = _progress_after(stage)
            rec = _append_stage(stage.value, "completed", metrics, stage_start)
            stage_records_json.append(rec)  # type: ignore[arg-type]
            update_stage(
                conn,
                run_id,
                stage.value,
                "running",
                metrics,
                progress_pct=accumulated_weight,
                stage_results=stage_records_json,
            )

        # ----------------------------------------------------------------
        # Stage 6 — ML scoring (bulk)
        # ----------------------------------------------------------------
        stage = PipelineStage.ML_SCORING
        if stage.value not in already_done:
            stage_start = _now()
            update_stage(
                conn,
                run_id,
                stage.value,
                "running",
                {},
                progress_pct=accumulated_weight,
                stage_results=stage_records_json,
            )
            try:
                metrics = _bulk_ml_scoring(conn, run_id)
            except Exception as exc:
                logger.exception("[%s] Stage ml_scoring failed", run_id)
                rec = _append_stage(stage.value, "failed", {}, stage_start, error=str(exc))
                stage_records_json.append(rec)  # type: ignore[arg-type]
                update_stage(
                    conn,
                    run_id,
                    stage.value,
                    "failed",
                    {},
                    progress_pct=accumulated_weight,
                    stage_results=stage_records_json,
                    error_message=f"Stage {stage.value} failed: {exc}",
                )
                return PipelineResult(
                    run_id=run_id,
                    status="failed",
                    stages=stages_completed,
                    error=str(exc),
                )
            accumulated_weight = _progress_after(stage)
            rec = _append_stage(stage.value, "completed", metrics, stage_start)
            stage_records_json.append(rec)  # type: ignore[arg-type]
            update_stage(
                conn,
                run_id,
                stage.value,
                "completed",
                metrics,
                progress_pct=100.0,
                stage_results=stage_records_json,
            )

        return PipelineResult(run_id=run_id, status="completed", stages=stages_completed)


# ---------------------------------------------------------------------------
# Retraining helper (sync, runs inside asyncio.to_thread)
# ---------------------------------------------------------------------------


def _retrain_models_sync(db_url: str) -> dict[str, Any]:
    """Retrain IsolationForest and weak-supervised models on current data.

    Returns a dict with model version strings.
    """
    from src.models.anomaly_scorer import _load_bundle as _load_anomaly_bundle
    from src.models.weak_supervised import run_training as run_ws_training

    model_version = datetime.now(UTC).strftime("v%Y%m%d%H%M%S")

    # 1. Retrain weak-supervised model
    try:
        run_ws_training(
            database_url=db_url,
            model_version=model_version,
            no_db_write=False,
        )
        ws_version = model_version
        logger.info("Weak-supervised model retrained: %s", ws_version)
    except Exception:
        logger.warning("Weak-supervised retrain failed — using existing model", exc_info=True)
        ws_version = "existing"

    # 2. Retrain IsolationForest
    try:
        import polars as pl
        import psycopg

        from src.models.anomaly_scorer import MODEL_PATH

        with psycopg.connect(db_url) as conn:
            df = pl.read_database("SELECT * FROM provider_features", conn)

        _retrain_isolation_forest(df, MODEL_PATH, model_version)
        # Clear cached model so the next call reloads
        _load_anomaly_bundle.cache_clear()
        af_version = model_version
        logger.info("IsolationForest model retrained: %s", af_version)
    except Exception:
        logger.warning("IsolationForest retrain failed — using existing model", exc_info=True)
        af_version = "existing"

    return {"isolation_forest": af_version, "weak_supervised": ws_version}


def _retrain_isolation_forest(df: Any, model_path: Any, model_version: str) -> None:
    """Train a new IsolationForest on ``provider_features`` and save the bundle."""
    try:
        import joblib
        import numpy as np
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        raise RuntimeError("scikit-learn / joblib required for IsolationForest retraining")

    # Feature columns used by the anomaly scorer
    # Load existing bundle to get the feature column list
    try:
        existing = joblib.load(model_path)
        feature_cols: list[str] = existing["feature_cols"]
    except Exception:
        # Fallback: use all numeric columns except npi
        feature_cols = [
            c for c in df.columns if c != "npi" and str(df[c].dtype).startswith("Float")
        ]

    x_raw = df.select(feature_cols).fill_null(0).to_numpy().astype(np.float64)

    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x_raw)

    model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    model.fit(x_scaled)

    bundle = {
        "model": model,
        "scaler": scaler,
        "feature_cols": feature_cols,
        "metadata": {
            "model_type": "IsolationForest",
            "model_version": model_version,
            "trained_at": datetime.now(UTC).isoformat(),
            "n_rows": int(len(x_raw)),
        },
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, model_path)


# ---------------------------------------------------------------------------
# Async public interface
# ---------------------------------------------------------------------------


async def recalibrate(run_id: int, db_url: str = DATABASE_URL) -> PipelineResult:
    """Run the full 6-stage recalibration pipeline with progress tracking.

    Executes the synchronous pipeline in a thread pool so the asyncio event
    loop is not blocked.  Progress is recorded in ``pipeline_runs`` after
    each stage, enabling real-time frontend polling.

    Args:
        run_id: An existing ``pipeline_runs.id`` (must already be ``status='running'``).
        db_url: Postgres connection string.

    Returns:
        :class:`PipelineResult` with the final status and per-stage records.
    """
    logger.info("[%s] Starting recalibration pipeline", run_id)
    try:
        result = await asyncio.to_thread(_run_recalibrate_sync, run_id, db_url)
    except Exception as exc:
        logger.exception("[%s] Unexpected orchestrator error", run_id)
        result = PipelineResult(run_id=run_id, status="failed", error=str(exc))
    logger.info("[%s] Pipeline finished: %s", run_id, result.status)
    return result


async def retrain_and_recalibrate(run_id: int, db_url: str = DATABASE_URL) -> PipelineResult:
    """Retrain ML models then run the full recalibration pipeline.

    1. Retrains IsolationForest on current ``provider_features``.
    2. Retrains weak-supervised model on current ``bridge_training_examples_v``.
    3. Calls :func:`recalibrate` with the freshly trained models.

    Args:
        run_id: An existing ``pipeline_runs.id``.
        db_url: Postgres connection string.

    Returns:
        :class:`PipelineResult` from the subsequent :func:`recalibrate` call.
    """
    logger.info("[%s] Starting retrain + recalibrate", run_id)
    try:
        model_versions = await asyncio.to_thread(_retrain_models_sync, db_url)
        logger.info("[%s] Retraining complete: %s", run_id, model_versions)
    except Exception as exc:
        logger.warning(
            "[%s] Retraining step failed — proceeding with existing models: %s",
            run_id,
            exc,
        )
    return await recalibrate(run_id, db_url)
