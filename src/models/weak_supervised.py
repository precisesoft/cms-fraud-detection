"""Weakly supervised hybrid-risk model for K8s-backed observations.

Loads a trained logistic-regression bundle at runtime and can also train the
bundle from additive bridge views in Postgres.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, TypedDict

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "data" / "models" / "weak_supervised_k8s_model.joblib"
RESULTS_PATH = ROOT / "data" / "validation" / "weak_supervised_results.json"

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://cms:cms_local_dev@172.16.0.191:30432/cms_fraud",
)

FEATURE_COLS = [
    "avg_submitted_charge",
    "avg_allowed_amount",
    "avg_payment_amount",
    "total_services",
    "total_beneficiaries",
    "rule_score",
    "anomaly_score",
    "provider_context_score",
    "hybrid_risk_score",
    "charge_delta_pct",
    "utilization_delta_pct",
    "charge_per_service",
    "services_per_bene",
    "payment_to_charge_ratio",
    "is_revoked",
    "is_excluded",
    "graph_node_degree",
    "graph_hcpcs_count",
    "graph_drug_count",
    "graph_shared_specialty_count",
]

TRAINING_SQL = "SELECT * FROM bridge_training_examples_v"

try:
    import joblib
    import numpy as np

    _RUNTIME_ML_AVAILABLE = True
except ImportError:
    _RUNTIME_ML_AVAILABLE = False


class TrainingMetrics(TypedDict):
    train_rows: int
    test_rows: int
    positive_rate_train: float
    positive_rate_test: float
    roc_auc: float | None
    average_precision: float | None


HybridRiskLabel = Literal["low", "medium", "high", "critical"]


def _clip(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _safe_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(number) or math.isinf(number):
        return 0.0
    return number


def compute_rule_score(row: dict[str, Any]) -> float:
    score = 0.0
    if _safe_float(row.get("present_in_2026_revocation_file", row.get("is_revoked"))) >= 1.0:
        score += 25.0
    enrolled = row.get("present_in_2025_enrollment_file")
    if enrolled is not None and _safe_float(enrolled) <= 0.0:
        score += 10.0
    return _clip(score, 0.0, 35.0)


def _services_per_bene_ratio(row: dict[str, Any]) -> float:
    explicit = row.get("spb_ratio")
    if explicit is not None:
        return max(_safe_float(explicit), 0.0)
    services_per_bene = row.get("services_per_bene")
    peer_avg_spb = row.get("peer_avg_spb")
    denominator = _safe_float(peer_avg_spb)
    if denominator <= 0.0:
        return 1.0
    return max(_safe_float(services_per_bene) / denominator, 0.0)


def compute_anomaly_score(row: dict[str, Any]) -> float:
    charge_component = _clip(_safe_float(row.get("submitted_to_allowed_peer_z")) * 15.0, 0.0, 45.0)
    spb_component = _clip((_services_per_bene_ratio(row) - 1.0) * 10.0, 0.0, 20.0)
    return _clip(charge_component + spb_component, 0.0, 65.0)


def compute_provider_context_score(row: dict[str, Any]) -> float:
    total_payment = _safe_float(row.get("provider_total_payment_amt", row.get("total_payment")))
    drug_count = _safe_float(row.get("unique_hcpcs_codes", row.get("drug_count")))
    graph_node_degree = row.get("graph_node_degree")
    if graph_node_degree is None:
        graph_node_degree = _safe_float(row.get("unique_hcpcs_codes")) + _safe_float(
            row.get("unique_place_of_service")
        )
    degree = _safe_float(graph_node_degree)
    context = (
        _clip(total_payment / 100000.0, 0.0, 5.0)
        + _clip(drug_count / 5.0, 0.0, 5.0)
        + _clip(degree / 10.0, 0.0, 5.0)
    )
    return _clip(context, 0.0, 15.0)


def build_feature_row(row: dict[str, Any]) -> dict[str, float]:
    avg_allowed_amount = row.get(
        "avg_allowed_amount",
        row.get("avg_medicare_allowed_amt", row.get("mean_allowed_amt")),
    )
    avg_payment_amount = row.get(
        "avg_payment_amount",
        row.get("avg_medicare_payment_amt", row.get("mean_payment_amt")),
    )
    provider_avg_services_per_bene = row.get(
        "provider_avg_services_per_bene",
        row.get("avg_services_per_bene", row.get("services_per_bene")),
    )
    is_revoked = row.get(
        "is_revoked",
        row.get("present_in_2026_revocation_file", row.get("revoked_2026")),
    )

    return {
        "avg_submitted_charge": _safe_float(row.get("avg_submitted_charge")),
        "avg_allowed_amount": _safe_float(avg_allowed_amount),
        "avg_payment_amount": _safe_float(avg_payment_amount),
        "total_services": _safe_float(row.get("total_services", row.get("tot_srvcs"))),
        "total_beneficiaries": _safe_float(row.get("total_beneficiaries", row.get("tot_benes"))),
        "rule_score": compute_rule_score(row),
        "anomaly_score": compute_anomaly_score(row),
        "provider_context_score": compute_provider_context_score(row),
        "hybrid_risk_score": _safe_float(
            row.get("hybrid_risk_score", row.get("seed_risk_score", row.get("risk_score")))
        ),
        "charge_delta_pct": _safe_float(row.get("submitted_to_allowed_peer_z")) * 100.0,
        "utilization_delta_pct": _safe_float(row.get("services_per_bene_peer_z")) * 100.0,
        "charge_per_service": _safe_float(
            row.get("charge_per_service", row.get("mean_submitted_charge"))
        ),
        "services_per_bene": _safe_float(provider_avg_services_per_bene),
        "payment_to_charge_ratio": _safe_float(
            row.get("payment_to_charge_ratio", row.get("mean_payment_ratio"))
        ),
        "is_revoked": _safe_float(is_revoked),
        "is_excluded": _safe_float(row.get("is_excluded")),
        "graph_node_degree": _safe_float(
            row.get(
                "graph_node_degree",
                _safe_float(row.get("unique_hcpcs_codes"))
                + _safe_float(row.get("unique_place_of_service")),
            )
        ),
        "graph_hcpcs_count": _safe_float(
            row.get("graph_hcpcs_count", row.get("unique_hcpcs_codes"))
        ),
        "graph_drug_count": _safe_float(row.get("graph_drug_count")),
        "graph_shared_specialty_count": _safe_float(row.get("graph_shared_specialty_count")),
    }


def compute_rule_component_score(row: dict[str, Any]) -> float:
    charge_ratio = _safe_float(row.get("submitted_to_allowed_ratio", row.get("charge_ratio")))
    spb_ratio = _services_per_bene_ratio(row)
    validation_issue_count = _safe_float(row.get("validation_issue_count"))
    score = 0.0
    if _safe_float(row.get("is_revoked", row.get("present_in_2026_revocation_file"))) >= 1.0:
        score += 40.0
    if _safe_float(row.get("is_excluded")) >= 1.0:
        score += 30.0
    if charge_ratio >= 3.0:
        score += 20.0
    if spb_ratio >= 3.0:
        score += 10.0
    if validation_issue_count > 0.0:
        score += 10.0
    return _clip(score, 0.0, 100.0)


def compute_composite_score(
    row: dict[str, Any],
    learned_score: float | None,
) -> tuple[float, HybridRiskLabel]:
    rule = compute_rule_component_score(row)
    anomaly = compute_anomaly_score(row)
    context = compute_provider_context_score(row)
    learned = _clip(_safe_float(learned_score), 0.0, 100.0)
    composite = _clip(
        0.45 * rule + 0.30 * anomaly + 0.10 * context + 0.15 * learned,
        0.0,
        100.0,
    )

    is_revoked = (
        _safe_float(row.get("is_revoked", row.get("present_in_2026_revocation_file"))) >= 1.0
    )
    is_excluded = _safe_float(row.get("is_excluded")) >= 1.0
    charge_ratio = _safe_float(row.get("submitted_to_allowed_ratio", row.get("charge_ratio")))
    spb_ratio = _services_per_bene_ratio(row)

    if is_revoked:
        composite = max(composite, 92.0)
    if is_excluded and not is_revoked:
        composite = max(composite, 82.0)
    if charge_ratio >= 4.0 and spb_ratio >= 3.0:
        composite = max(composite, 70.0)

    if composite >= 90.0:
        return round(composite, 1), "critical"
    if composite >= 70.0:
        return round(composite, 1), "high"
    if composite >= 40.0:
        return round(composite, 1), "medium"
    return round(composite, 1), "low"


@lru_cache(maxsize=1)
def _load_bundle() -> dict[str, Any]:
    logger.info("Loading weak-supervision model bundle from %s", MODEL_PATH)
    bundle: dict[str, Any] = joblib.load(MODEL_PATH)
    return bundle


def score_observation(row: dict[str, Any]) -> float | None:
    if not _RUNTIME_ML_AVAILABLE:
        logger.debug("ML libraries not installed — weak supervision scoring unavailable")
        return None

    try:
        bundle = _load_bundle()
    except Exception:
        logger.warning("Weak supervision model not available — skipping", exc_info=True)
        return None

    feature_cols: list[str] = bundle.get("feature_cols", FEATURE_COLS)
    feature_row = build_feature_row(row)
    values = [feature_row.get(col, 0.0) for col in feature_cols]
    x_vec = np.array([values], dtype=np.float64)

    scaler = bundle.get("scaler")
    if scaler is not None:
        x_vec = scaler.transform(x_vec)

    model = bundle["model"]
    probability = float(model.predict_proba(x_vec)[0][1]) * 100.0
    return round(_clip(probability, 0.0, 100.0), 1)


def _import_training_deps():
    import polars as pl
    import psycopg
    from psycopg.rows import dict_row
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, roc_auc_score
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    return {
        "pl": pl,
        "psycopg": psycopg,
        "dict_row": dict_row,
        "LogisticRegression": LogisticRegression,
        "average_precision_score": average_precision_score,
        "roc_auc_score": roc_auc_score,
        "train_test_split": train_test_split,
        "StandardScaler": StandardScaler,
    }


def load_training_frame(database_url: str = DATABASE_URL):
    deps = _import_training_deps()
    psycopg = deps["psycopg"]
    dict_row = deps["dict_row"]
    pl = deps["pl"]

    logger.info("Loading weak-supervision training rows from Postgres")
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(TRAINING_SQL)
            rows = cur.fetchall()
    return pl.DataFrame(rows)


def _build_xy(df):
    np = __import__("numpy")

    x_mat = df.select(FEATURE_COLS).fill_null(0).to_numpy().astype(np.float64)
    y_vec = df["weak_label"].to_numpy().astype(np.int64)
    return x_mat, y_vec


def train_model(df) -> tuple[dict[str, Any], TrainingMetrics]:
    deps = _import_training_deps()
    logistic_regression = deps["LogisticRegression"]
    standard_scaler = deps["StandardScaler"]
    average_precision_score = deps["average_precision_score"]
    roc_auc_score = deps["roc_auc_score"]
    train_test_split = deps["train_test_split"]
    np = __import__("numpy")

    x_raw, y = _build_xy(df)
    if len(set(y.tolist())) < 2:
        raise ValueError("Weak supervision training requires both positive and negative labels")

    x_train, x_test, y_train, y_test = train_test_split(
        x_raw,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    scaler = standard_scaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)

    model = logistic_regression(
        max_iter=1000,
        class_weight="balanced",
        solver="lbfgs",
        random_state=42,
    )
    model.fit(x_train_scaled, y_train)

    y_prob = model.predict_proba(x_test_scaled)[:, 1]
    roc_auc = float(roc_auc_score(y_test, y_prob)) if len(np.unique(y_test)) > 1 else None
    avg_precision = (
        float(average_precision_score(y_test, y_prob)) if len(np.unique(y_test)) > 1 else None
    )

    bundle = {
        "model": model,
        "scaler": scaler,
        "feature_cols": FEATURE_COLS,
        "metadata": {
            "model_type": "LogisticRegression",
            "trained_at": datetime.now(UTC).isoformat(),
            "n_rows": int(df.height),
            "positive_rate": round(float(df["weak_label"].mean()), 6),
        },
    }
    metrics: TrainingMetrics = {
        "train_rows": int(len(y_train)),
        "test_rows": int(len(y_test)),
        "positive_rate_train": round(float(y_train.mean()), 6),
        "positive_rate_test": round(float(y_test.mean()), 6),
        "roc_auc": round(roc_auc, 6) if roc_auc is not None else None,
        "average_precision": round(avg_precision, 6) if avg_precision is not None else None,
    }
    return bundle, metrics


def save_bundle(bundle: dict[str, Any], model_path: Path = MODEL_PATH) -> Path:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, model_path)
    logger.info("Saved weak-supervision model bundle to %s", model_path)
    return model_path


def save_results(metrics: TrainingMetrics, results_path: Path = RESULTS_PATH) -> Path:
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w") as handle:
        json.dump(metrics, handle, indent=2)
    logger.info("Saved weak-supervision metrics to %s", results_path)
    return results_path


def write_training_artifacts_to_db(
    df,
    bundle: dict[str, Any],
    metrics: TrainingMetrics,
    database_url: str,
    model_name: str,
    model_version: str,
) -> None:
    deps = _import_training_deps()
    psycopg = deps["psycopg"]

    model = bundle["model"]
    scaler = bundle["scaler"]
    x_raw, _ = _build_xy(df)
    x_scaled = scaler.transform(x_raw)
    probs = model.predict_proba(x_scaled)[:, 1] * 100.0

    rows = df.select(["observation_id", "npi"]).to_dicts()
    feature_rows_by_observation = {row["observation_id"]: row for row in df.to_dicts()}

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO trained_models (
                    model_name,
                    model_version,
                    model_type,
                    feature_columns,
                    training_metrics,
                    artifact_path
                )
                VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s)
                ON CONFLICT (model_name, model_version) DO UPDATE SET
                    model_type = EXCLUDED.model_type,
                    feature_columns = EXCLUDED.feature_columns,
                    training_metrics = EXCLUDED.training_metrics,
                    artifact_path = EXCLUDED.artifact_path,
                    trained_at = NOW()
                """,
                (
                    model_name,
                    model_version,
                    bundle["metadata"]["model_type"],
                    json.dumps(FEATURE_COLS),
                    json.dumps(metrics),
                    str(MODEL_PATH),
                ),
            )

            for row, prob in zip(rows, probs.tolist(), strict=False):
                training_row = feature_rows_by_observation[row["observation_id"]]
                feature_row = build_feature_row(training_row)
                composite, label = compute_composite_score(feature_row, prob)
                cur.execute(
                    """
                    INSERT INTO observation_model_scores (
                        case_id,
                        npi,
                        model_name,
                        model_version,
                        predicted_probability,
                        composite_score,
                        risk_label,
                        score_metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        row["observation_id"],
                        row["npi"],
                        model_name,
                        model_version,
                        round(float(prob), 1),
                        composite,
                        label,
                        json.dumps(feature_row),
                    ),
                )
        conn.commit()


def run_training(
    database_url: str = DATABASE_URL,
    model_path: Path = MODEL_PATH,
    results_path: Path = RESULTS_PATH,
    model_name: str = "weak_supervised_k8s_model",
    model_version: str = datetime.now(UTC).strftime("v%Y%m%d%H%M%S"),
    no_db_write: bool = True,
) -> TrainingMetrics:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    df = load_training_frame(database_url)
    if df.is_empty():
        raise ValueError("No labeled rows available from bridge_training_examples_v")

    bundle, metrics = train_model(df)
    save_bundle(bundle, model_path)
    save_results(metrics, results_path)

    if not no_db_write:
        write_training_artifacts_to_db(df, bundle, metrics, database_url, model_name, model_version)

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the weak-supervised K8s risk model")
    parser.add_argument("--database-url", default=DATABASE_URL)
    parser.add_argument("--model-path", type=Path, default=MODEL_PATH)
    parser.add_argument("--results-path", type=Path, default=RESULTS_PATH)
    parser.add_argument("--model-name", default="weak_supervised_k8s_model")
    parser.add_argument(
        "--model-version",
        default=datetime.now(UTC).strftime("v%Y%m%d%H%M%S"),
    )
    parser.add_argument("--no-db-write", action="store_true")
    args = parser.parse_args()

    metrics = run_training(
        database_url=args.database_url,
        model_path=args.model_path,
        results_path=args.results_path,
        model_name=args.model_name,
        model_version=args.model_version,
        no_db_write=args.no_db_write,
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
