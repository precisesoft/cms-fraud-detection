"""Runtime anomaly scorer — loads the trained IsolationForest and scores providers on demand.

The model bundle (model + scaler + feature_cols) is loaded lazily on first call
and cached for the lifetime of the process.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).resolve().parents[2] / "data" / "models" / "isolation_forest.joblib"


@lru_cache(maxsize=1)
def _load_bundle() -> dict[str, Any]:
    """Load and cache the model bundle from disk."""
    logger.info("Loading anomaly model bundle from %s", MODEL_PATH)
    bundle: dict[str, Any] = joblib.load(MODEL_PATH)
    logger.info(
        "Anomaly model loaded: %d features, %s",
        len(bundle["feature_cols"]),
        type(bundle["model"]).__name__,
    )
    return bundle


def score_provider(feature_row: dict) -> float | None:
    """Score a single provider using the isolation forest.

    Args:
        feature_row: dict of provider features (column_name → value).
            Must contain the 49 feature columns the model was trained on.

    Returns:
        Anomaly score in [0, 100] where higher = more anomalous.
        Returns None if the model cannot be loaded or features are insufficient.
    """
    try:
        bundle = _load_bundle()
    except Exception:
        logger.warning("Anomaly model not available — skipping", exc_info=True)
        return None

    model = bundle["model"]
    scaler = bundle["scaler"]
    feature_cols: list[str] = bundle["feature_cols"]

    # Build feature vector in the same column order as training
    values = [float(feature_row.get(col) or 0) for col in feature_cols]
    x = np.array([values], dtype=np.float64)
    x_scaled = scaler.transform(x)

    # decision_function: lower = more anomalous. Negate and normalize to 0-100.
    raw_score = float(model.decision_function(x_scaled)[0])
    # Typical range is roughly [-0.5, 0.5]. Clamp to [0, 100].
    normalized = max(0.0, min(100.0, 50.0 - raw_score * 100.0))
    return round(normalized, 1)
