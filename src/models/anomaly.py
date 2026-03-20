"""Isolation Forest anomaly detection for CMS provider fraud.

Trains an unsupervised anomaly model on provider-level features,
then validates against revocation ground truth and correlates with
rule-based risk scores.

Usage:
    python -m src.models.anomaly
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import joblib
import numpy as np
import polars as pl
from sklearn.ensemble import IsolationForest
from sklearn.inspection import permutation_importance
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
FEATURES_PATH = ROOT / "data" / "features" / "provider_features.parquet"
MODEL_PATH = ROOT / "data" / "models" / "isolation_forest.joblib"
RESULTS_PATH = ROOT / "data" / "validation" / "anomaly_results.json"

# ---------------------------------------------------------------------------
# Column configuration
# ---------------------------------------------------------------------------
TEXT_COLS = {
    "npi",
    "provider_name",
    "entity_code",
    "city",
    "state",
    "zip5",
    "provider_type",
    "medicare_participating",
    "revocation_reason",
}

# Columns used as labels/targets (not model inputs)
LABEL_COLS = {
    "revoked_2026",
    "max_seed_risk_score",
    "avg_seed_risk_score",
    "min_seed_legitimacy_score",
    "avg_seed_legitimacy_score",
}

EXCLUDE_COLS = TEXT_COLS | LABEL_COLS


def select_feature_columns(df: pl.DataFrame) -> list[str]:
    """Return numeric feature columns, excluding text and label columns."""
    return [
        col
        for col in df.columns
        if col not in EXCLUDE_COLS and df[col].dtype not in (pl.String, pl.Categorical, pl.Enum)
    ]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_features(path: Path = FEATURES_PATH) -> pl.DataFrame:
    """Load provider features parquet file."""
    logger.info("Loading features from %s", path)
    df = pl.read_parquet(path)
    logger.info("Loaded %d providers, %d columns", *df.shape)
    return df


# ---------------------------------------------------------------------------
# Model training
# ---------------------------------------------------------------------------


def build_feature_matrix(df: pl.DataFrame, feature_cols: list[str]) -> np.ndarray:
    """Extract feature matrix: select columns, fill nulls, convert to numpy."""
    x_mat = df.select(feature_cols).fill_null(0).to_numpy().astype(np.float64)
    return x_mat


def train_model(
    x_scaled: np.ndarray,
    contamination: float = 0.05,
    n_estimators: int = 200,
    random_state: int = 42,
) -> IsolationForest:
    """Fit an IsolationForest and return the trained model."""
    model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=random_state,
    )
    model.fit(x_scaled)
    logger.info(
        "Trained IsolationForest: n_estimators=%d, contamination=%.2f, n_samples=%d",
        n_estimators,
        contamination,
        x_scaled.shape[0],
    )
    return model


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def compute_correlation(
    anomaly_scores: np.ndarray,
    rule_scores: np.ndarray,
) -> float:
    """Pearson correlation between anomaly score and rule-based risk score.

    IsolationForest decision_function: lower (more negative) = more anomalous.
    Rule-based risk: higher = more risky.
    So we negate anomaly_scores for an intuitive positive correlation.
    """
    neg_anomaly = -anomaly_scores
    corr_matrix = np.corrcoef(neg_anomaly, rule_scores)
    return float(corr_matrix[0, 1])


def detection_rate_at_k(
    anomaly_scores: np.ndarray,
    revoked: np.ndarray,
    top_k_frac: float,
) -> float:
    """Fraction of revoked providers appearing in the top-k most anomalous."""
    n = len(anomaly_scores)
    k = max(1, int(n * top_k_frac))
    # Argsort ascending: most anomalous (lowest score) first
    top_k_idx = np.argsort(anomaly_scores)[:k]
    n_revoked_in_top_k = int(revoked[top_k_idx].sum())
    n_revoked_total = int(revoked.sum())
    if n_revoked_total == 0:
        return 0.0
    return round(n_revoked_in_top_k / n_revoked_total, 4)


# ---------------------------------------------------------------------------
# Feature importance
# ---------------------------------------------------------------------------


def compute_permutation_importance(
    model: IsolationForest,
    x_scaled: np.ndarray,
    feature_cols: list[str],
    n_repeats: int = 10,
    random_state: int = 42,
) -> list[dict[str, object]]:
    """Compute permutation importance and return top 10 features.

    Uses anomaly scores (decision_function) as a proxy target so that
    permutation_importance can measure how much each feature contributes
    to the unsupervised anomaly detection signal.
    """
    # Use decision_function output as proxy labels — lower = more anomalous.
    # Negated so that higher values indicate more anomalous (consistent direction).
    y_proxy = -model.decision_function(x_scaled)

    result = permutation_importance(
        model,
        x_scaled,
        y=y_proxy,
        n_repeats=n_repeats,
        random_state=random_state,
        scoring="r2",  # regression scorer against proxy labels
    )
    importances = result.importances_mean  # type: ignore[attr-defined]

    ranked = sorted(
        zip(feature_cols, importances.tolist()),
        key=lambda x: abs(x[1]),
        reverse=True,
    )
    top10 = [{"feature": feat, "importance": round(imp, 6)} for feat, imp in ranked[:10]]
    return top10


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run(
    features_path: Path = FEATURES_PATH,
    model_path: Path = MODEL_PATH,
    results_path: Path = RESULTS_PATH,
) -> dict[str, object]:
    """Full pipeline: load → scale → train → validate → save."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # 1. Load data
    df = load_features(features_path)
    feature_cols = select_feature_columns(df)
    logger.info("Selected %d numeric feature columns", len(feature_cols))

    # 2. Build feature matrix and scale
    x_raw = build_feature_matrix(df, feature_cols)
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x_raw)

    # 3. Train model
    model = train_model(x_scaled)

    # 4. Anomaly scores
    anomaly_scores = model.decision_function(x_scaled)  # lower = more anomalous

    # 5. Correlation with rule-based risk
    rule_scores = df["max_seed_risk_score"].fill_null(0).to_numpy().astype(np.float64)
    correlation = compute_correlation(anomaly_scores, rule_scores)
    logger.info("Correlation (anomaly vs rule-based risk): %.4f", correlation)

    # 6. Detection rates against revoked providers
    revoked = df["revoked_2026"].fill_null(0).to_numpy().astype(np.float64)
    det_5 = detection_rate_at_k(anomaly_scores, revoked, 0.05)
    det_10 = detection_rate_at_k(anomaly_scores, revoked, 0.10)
    det_20 = detection_rate_at_k(anomaly_scores, revoked, 0.20)
    logger.info(
        "Revocation detection rates — top5%%: %.1f%%, top10%%: %.1f%%, top20%%: %.1f%%",
        det_5 * 100,
        det_10 * 100,
        det_20 * 100,
    )

    # 7. Permutation importance
    logger.info("Computing permutation importance (n_repeats=10)...")
    top10_features = compute_permutation_importance(model, x_scaled, feature_cols)

    # 8. Assemble results
    results: dict[str, object] = {
        "model_metadata": {
            "model_type": "IsolationForest",
            "n_estimators": 200,
            "contamination": 0.05,
            "random_state": 42,
            "n_features": len(feature_cols),
            "n_samples": int(x_scaled.shape[0]),
        },
        "correlation_anomaly_vs_rule_risk": round(correlation, 4),
        "detection_rates": {
            "top_5pct": det_5,
            "top_10pct": det_10,
            "top_20pct": det_20,
            "note": "Fraction of all revoked providers appearing in top-N most anomalous",
        },
        "top10_features_permutation_importance": top10_features,
    }

    # 9. Save results JSON
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info("Saved results to %s", results_path)

    # 10. Save model + scaler bundle
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "scaler": scaler, "feature_cols": feature_cols}, model_path)
    logger.info("Saved model bundle to %s", model_path)

    # 11. Print summary
    _print_summary(results)

    return results


def _print_summary(results: dict[str, object]) -> None:
    meta: dict[str, object] = results["model_metadata"]  # type: ignore[assignment]
    corr = float(results["correlation_anomaly_vs_rule_risk"])  # type: ignore[arg-type]
    det: dict[str, object] = results["detection_rates"]  # type: ignore[assignment]
    feats: list[dict[str, object]] = results[  # type: ignore[assignment]
        "top10_features_permutation_importance"
    ]

    print("\n" + "=" * 60)
    print("ISOLATION FOREST — ANOMALY DETECTION RESULTS")
    print("=" * 60)
    print(f"Samples: {meta['n_samples']:,}  |  Features: {meta['n_features']}")
    print(f"Contamination: {meta['contamination']:.0%}  |  Estimators: {meta['n_estimators']}")
    print()
    print(f"Correlation (anomaly score vs rule-based risk): {corr:+.4f}")
    print()
    print("Revoked provider detection rates:")
    print(f"  Top  5% most anomalous: {float(det['top_5pct']):.1%} of all revoked captured")  # type: ignore[arg-type]
    print(f"  Top 10% most anomalous: {float(det['top_10pct']):.1%} of all revoked captured")  # type: ignore[arg-type]
    print(f"  Top 20% most anomalous: {float(det['top_20pct']):.1%} of all revoked captured")  # type: ignore[arg-type]
    print()
    print("Top 10 features by permutation importance:")
    for i, feat_entry in enumerate(feats, 1):
        print(f"  {i:2d}. {feat_entry['feature']!s:<35s}  {float(feat_entry['importance'])!s:>12s}")  # type: ignore[arg-type]
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run()
