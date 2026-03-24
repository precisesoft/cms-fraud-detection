"""Per-provider feature importance for the Isolation Forest anomaly model.

Uses a leave-one-out approximation: for each feature, zero it out and
measure the change in anomaly score.  Positive delta means that feature
was pushing the score higher (more anomalous); negative means it was
protective.

This avoids a runtime dependency on the ``shap`` package while giving
directionally identical results for tree-based models.
"""

from __future__ import annotations

import logging
from typing import Any

from src.models.anomaly_scorer import _ML_AVAILABLE

logger = logging.getLogger(__name__)

# Re-export for convenience
__all__ = ["explain_provider"]


def _load_bundle() -> dict[str, Any]:
    """Load the cached model bundle (same as anomaly_scorer)."""
    from src.models.anomaly_scorer import _load_bundle

    return _load_bundle()


def _raw_anomaly_score(model: Any, scaler: Any, x_row: list[float]) -> float:
    """Compute the normalized anomaly score (0-100) for a single row."""
    import numpy as np

    x = scaler.transform(np.array([x_row], dtype=np.float64))
    raw = float(model.decision_function(x)[0])
    return max(0.0, min(100.0, 50.0 - raw * 100.0))


def explain_provider(
    feature_row: dict,
    top_n: int = 5,
) -> dict | None:
    """Compute per-feature importance for one provider.

    Args:
        feature_row: dict of column_name → value (must contain the 49 model features).
        top_n: number of top contributing features to return.

    Returns:
        ``{"anomaly_score": float, "top_features": [...]}`` or ``None``
        if the model is unavailable.
    """
    if not _ML_AVAILABLE:
        return None

    try:
        bundle = _load_bundle()
    except Exception:
        logger.warning("Anomaly model not available", exc_info=True)
        return None

    model = bundle["model"]
    scaler = bundle["scaler"]
    feature_cols: list[str] = bundle["feature_cols"]

    # Build the original feature vector
    values = [float(feature_row.get(col) or 0) for col in feature_cols]
    base_score = _raw_anomaly_score(model, scaler, values)

    # Leave-one-out: zero each feature and measure delta
    contributions: list[dict] = []
    for i, col in enumerate(feature_cols):
        if values[i] == 0.0:
            # Feature already zero — contribution is 0
            contributions.append(
                {
                    "name": col,
                    "contribution": 0.0,
                    "actual_value": 0.0,
                    "direction": "neutral",
                }
            )
            continue

        perturbed = values.copy()
        perturbed[i] = 0.0
        perturbed_score = _raw_anomaly_score(model, scaler, perturbed)
        delta = base_score - perturbed_score  # positive = feature increases anomaly

        contributions.append(
            {
                "name": col,
                "contribution": round(delta, 2),
                "actual_value": round(values[i], 4),
                "direction": "risk" if delta > 0 else "protective",
            }
        )

    # Sort by absolute contribution descending
    contributions.sort(key=lambda c: abs(c["contribution"]), reverse=True)

    return {
        "anomaly_score": round(base_score, 1),
        "top_features": contributions[:top_n],
    }
