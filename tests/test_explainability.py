"""Tests for per-provider feature importance explainability."""

from __future__ import annotations

import pytest

from src.models.anomaly_scorer import _ML_AVAILABLE

pytestmark = pytest.mark.skipif(
    not _ML_AVAILABLE,
    reason="ML libraries (scikit-learn, joblib) not installed",
)


@pytest.fixture
def sample_feature_row() -> dict:
    """Minimal feature row with the 49 columns the model expects."""
    from src.models.anomaly_scorer import _load_bundle

    bundle = _load_bundle()
    # Create a row with all features at 0 except a few distinctive ones
    row = {col: 0.0 for col in bundle["feature_cols"]}
    row["provider_total_services"] = 5000.0
    row["provider_total_benes"] = 200.0
    row["enrolled_2025"] = 1.0
    return row


def test_explain_returns_dict(sample_feature_row: dict) -> None:
    from src.explainability.shap_explainer import explain_provider

    result = explain_provider(sample_feature_row)
    assert result is not None
    assert "anomaly_score" in result
    assert "top_features" in result
    assert 0 <= result["anomaly_score"] <= 100


def test_explain_top_n_default(sample_feature_row: dict) -> None:
    from src.explainability.shap_explainer import explain_provider

    result = explain_provider(sample_feature_row, top_n=5)
    assert result is not None
    assert len(result["top_features"]) == 5


def test_explain_top_n_custom(sample_feature_row: dict) -> None:
    from src.explainability.shap_explainer import explain_provider

    result = explain_provider(sample_feature_row, top_n=3)
    assert result is not None
    assert len(result["top_features"]) == 3


def test_feature_contribution_structure(sample_feature_row: dict) -> None:
    from src.explainability.shap_explainer import explain_provider

    result = explain_provider(sample_feature_row, top_n=1)
    assert result is not None
    feat = result["top_features"][0]
    assert "name" in feat
    assert "contribution" in feat
    assert "actual_value" in feat
    assert feat["direction"] in ("risk", "protective", "neutral")


def test_features_sorted_by_abs_contribution(sample_feature_row: dict) -> None:
    from src.explainability.shap_explainer import explain_provider

    result = explain_provider(sample_feature_row, top_n=10)
    assert result is not None
    contributions = [abs(f["contribution"]) for f in result["top_features"]]
    assert contributions == sorted(contributions, reverse=True)
