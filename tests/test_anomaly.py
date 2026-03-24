"""Tests for src/models/anomaly.py — Isolation Forest anomaly detection."""

from __future__ import annotations

from unittest.mock import patch

import pytest

np = pytest.importorskip("numpy")
pl = pytest.importorskip("polars")
pytest.importorskip("sklearn")

from sklearn.ensemble import IsolationForest  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from src.models.anomaly import (  # noqa: E402
    EXCLUDE_COLS,
    _print_summary,
    build_feature_matrix,
    compute_correlation,
    compute_permutation_importance,
    detection_rate_at_k,
    load_features,
    run,
    select_feature_columns,
    train_model,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def synthetic_df() -> pl.DataFrame:
    """Small synthetic DataFrame that mirrors the real schema."""
    rng = np.random.default_rng(0)
    n = 200
    return pl.DataFrame(
        {
            # text / excluded columns
            "npi": list(range(1_000_000_000, 1_000_000_000 + n)),
            "provider_name": [f"Provider {i}" for i in range(n)],
            "entity_code": ["I"] * n,
            "city": ["Springfield"] * n,
            "state": ["IL"] * n,
            "zip5": [62701] * n,
            "provider_type": ["01"] * n,
            "medicare_participating": ["Y"] * n,
            "revocation_reason": [None] * n,
            # label columns
            "revoked_2026": [1] * 10 + [0] * (n - 10),
            "max_seed_risk_score": rng.integers(0, 100, n).tolist(),
            "avg_seed_risk_score": rng.random(n).tolist(),
            "min_seed_legitimacy_score": rng.integers(0, 50, n).tolist(),
            "avg_seed_legitimacy_score": rng.random(n).tolist(),
            # numeric feature columns
            "total_benes": rng.uniform(10, 1000, n).tolist(),
            "total_services": rng.uniform(50, 5000, n).tolist(),
            "mean_payment_amt": rng.uniform(20, 500, n).tolist(),
            "mean_charge_ratio": rng.uniform(0.5, 3.0, n).tolist(),
            "service_hhi": rng.uniform(0.0, 1.0, n).tolist(),
            "max_volume_z": rng.uniform(-2, 5, n).tolist(),
            "n_charge_outlier_lines": rng.integers(0, 10, n).tolist(),
            "frac_volume_outlier_lines": rng.uniform(0.0, 1.0, n).tolist(),
        }
    )


# ---------------------------------------------------------------------------
# Tests: select_feature_columns
# ---------------------------------------------------------------------------


class TestSelectFeatureColumns:
    def test_excludes_text_columns(self, synthetic_df: pl.DataFrame) -> None:
        cols = select_feature_columns(synthetic_df)
        for text_col in (
            "npi",
            "provider_name",
            "entity_code",
            "city",
            "state",
            "zip5",
            "provider_type",
            "medicare_participating",
            "revocation_reason",
        ):
            assert text_col not in cols, f"{text_col} should be excluded"

    def test_excludes_label_columns(self, synthetic_df: pl.DataFrame) -> None:
        cols = select_feature_columns(synthetic_df)
        for label_col in (
            "revoked_2026",
            "max_seed_risk_score",
            "avg_seed_risk_score",
            "min_seed_legitimacy_score",
            "avg_seed_legitimacy_score",
        ):
            assert label_col not in cols, f"{label_col} should be excluded"

    def test_returns_only_numeric(self, synthetic_df: pl.DataFrame) -> None:
        cols = select_feature_columns(synthetic_df)
        assert len(cols) > 0, "Should have at least one numeric feature"
        for col in cols:
            assert synthetic_df[col].dtype not in (
                pl.String,
                pl.Categorical,
                pl.Enum,
            ), f"{col} has non-numeric dtype"

    def test_exclude_cols_constant_matches_spec(self) -> None:
        """Ensure EXCLUDE_COLS covers all documented text cols."""
        expected_text = {
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
        assert expected_text.issubset(EXCLUDE_COLS)


# ---------------------------------------------------------------------------
# Tests: build_feature_matrix
# ---------------------------------------------------------------------------


class TestBuildFeatureMatrix:
    def test_shape(self, synthetic_df: pl.DataFrame) -> None:
        cols = select_feature_columns(synthetic_df)
        x_mat = build_feature_matrix(synthetic_df, cols)
        assert x_mat.shape == (len(synthetic_df), len(cols))

    def test_no_nans(self, synthetic_df: pl.DataFrame) -> None:
        cols = select_feature_columns(synthetic_df)
        x_mat = build_feature_matrix(synthetic_df, cols)
        assert not np.isnan(x_mat).any(), "Feature matrix must not contain NaN"

    def test_dtype_float64(self, synthetic_df: pl.DataFrame) -> None:
        cols = select_feature_columns(synthetic_df)
        x_mat = build_feature_matrix(synthetic_df, cols)
        assert x_mat.dtype == np.float64


# ---------------------------------------------------------------------------
# Tests: train_model
# ---------------------------------------------------------------------------


class TestTrainModel:
    def test_returns_isolation_forest(self, synthetic_df: pl.DataFrame) -> None:
        cols = select_feature_columns(synthetic_df)
        x_mat = build_feature_matrix(synthetic_df, cols)
        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x_mat)
        model = train_model(x_scaled)
        assert isinstance(model, IsolationForest)

    def test_model_is_fitted(self, synthetic_df: pl.DataFrame) -> None:
        cols = select_feature_columns(synthetic_df)
        x_mat = build_feature_matrix(synthetic_df, cols)
        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x_mat)
        model = train_model(x_scaled)
        # fitted models expose estimators_
        assert hasattr(model, "estimators_")
        assert len(model.estimators_) == 200  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests: anomaly scores
# ---------------------------------------------------------------------------


class TestAnomalyScores:
    def test_scores_shape(self, synthetic_df: pl.DataFrame) -> None:
        cols = select_feature_columns(synthetic_df)
        x_mat = build_feature_matrix(synthetic_df, cols)
        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x_mat)
        model = train_model(x_scaled)
        scores = model.decision_function(x_scaled)
        assert scores.shape == (len(synthetic_df),), "One score per provider"

    def test_scores_are_finite(self, synthetic_df: pl.DataFrame) -> None:
        cols = select_feature_columns(synthetic_df)
        x_mat = build_feature_matrix(synthetic_df, cols)
        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x_mat)
        model = train_model(x_scaled)
        scores = model.decision_function(x_scaled)
        assert np.isfinite(scores).all(), "All anomaly scores must be finite"

    def test_predict_returns_labels(self, synthetic_df: pl.DataFrame) -> None:
        cols = select_feature_columns(synthetic_df)
        x_mat = build_feature_matrix(synthetic_df, cols)
        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x_mat)
        model = train_model(x_scaled)
        labels = model.predict(x_scaled)
        assert set(labels).issubset({-1, 1}), "IsolationForest labels must be -1 or +1"


# ---------------------------------------------------------------------------
# Tests: validation helpers
# ---------------------------------------------------------------------------


class TestComputeCorrelation:
    def test_perfect_positive_correlation(self) -> None:
        # anomaly_scores that are very negative → high rule risk
        anomaly = np.array([-1.0, -0.5, 0.0, 0.5, 1.0])
        rule = np.array([4.0, 3.0, 2.0, 1.0, 0.0])
        corr = compute_correlation(anomaly, rule)
        assert corr > 0.99

    def test_returns_float(self) -> None:
        rng = np.random.default_rng(1)
        corr = compute_correlation(rng.random(50), rng.random(50))
        assert isinstance(corr, float)
        assert -1.0 <= corr <= 1.0


class TestDetectionRateAtK:
    def test_all_revoked_at_top(self) -> None:
        # 10 samples, first 2 are most anomalous (lowest score), both revoked
        scores = np.array([-2.0, -1.5, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7])
        revoked = np.array([1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        rate = detection_rate_at_k(scores, revoked, top_k_frac=0.2)
        assert rate == 1.0

    def test_no_revoked_providers(self) -> None:
        scores = np.array([-1.0, 0.0, 1.0])
        revoked = np.zeros(3)
        rate = detection_rate_at_k(scores, revoked, top_k_frac=0.5)
        assert rate == 0.0

    def test_rate_in_valid_range(self) -> None:
        rng = np.random.default_rng(2)
        scores = rng.random(100)
        revoked = (rng.random(100) > 0.9).astype(float)
        rate = detection_rate_at_k(scores, revoked, top_k_frac=0.1)
        assert 0.0 <= rate <= 1.0


# ---------------------------------------------------------------------------
# Tests: permutation importance
# ---------------------------------------------------------------------------


class TestPermutationImportance:
    def test_returns_top10(self, synthetic_df: pl.DataFrame) -> None:
        cols = select_feature_columns(synthetic_df)
        x_mat = build_feature_matrix(synthetic_df, cols)
        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x_mat)
        model = train_model(x_scaled)
        top10 = compute_permutation_importance(model, x_scaled, cols, n_repeats=3)
        assert len(top10) == min(10, len(cols))

    def test_result_structure(self, synthetic_df: pl.DataFrame) -> None:
        cols = select_feature_columns(synthetic_df)
        x_mat = build_feature_matrix(synthetic_df, cols)
        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x_mat)
        model = train_model(x_scaled)
        top10 = compute_permutation_importance(model, x_scaled, cols, n_repeats=3)
        for entry in top10:
            assert "feature" in entry
            assert "importance" in entry
            assert isinstance(entry["feature"], str)
            assert isinstance(entry["importance"], float)

    def test_feature_names_from_input(self, synthetic_df: pl.DataFrame) -> None:
        cols = select_feature_columns(synthetic_df)
        x_mat = build_feature_matrix(synthetic_df, cols)
        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x_mat)
        model = train_model(x_scaled)
        top10 = compute_permutation_importance(model, x_scaled, cols, n_repeats=3)
        returned_features = {e["feature"] for e in top10}
        assert returned_features.issubset(set(cols))


# ---------------------------------------------------------------------------
# Tests: load_features
# ---------------------------------------------------------------------------


class TestLoadFeatures:
    def test_loads_parquet(self, synthetic_df: pl.DataFrame, tmp_path) -> None:
        path = tmp_path / "features.parquet"
        synthetic_df.write_parquet(path)
        result = load_features(path)
        assert result.shape == synthetic_df.shape

    def test_raises_on_missing_file(self, tmp_path) -> None:
        with pytest.raises(Exception):
            load_features(tmp_path / "nonexistent.parquet")


# ---------------------------------------------------------------------------
# Tests: _print_summary
# ---------------------------------------------------------------------------


class TestPrintSummary:
    def test_prints_without_error(self, capsys) -> None:
        results = {
            "model_metadata": {
                "model_type": "IsolationForest",
                "n_estimators": 200,
                "contamination": 0.05,
                "random_state": 42,
                "n_features": 8,
                "n_samples": 200,
            },
            "correlation_anomaly_vs_rule_risk": -0.4321,
            "detection_rates": {
                "top_5pct": 0.3,
                "top_10pct": 0.5,
                "top_20pct": 0.7,
                "note": "test",
            },
            "top10_features_permutation_importance": [
                {"feature": "total_benes", "importance": 0.012345},
                {"feature": "mean_payment_amt", "importance": 0.009876},
            ],
        }
        _print_summary(results)
        captured = capsys.readouterr()
        assert "ISOLATION FOREST" in captured.out
        assert "total_benes" in captured.out
        assert "200" in captured.out


# ---------------------------------------------------------------------------
# Tests: run (full pipeline)
# ---------------------------------------------------------------------------


class TestRun:
    def test_full_pipeline(self, synthetic_df: pl.DataFrame, tmp_path) -> None:
        features_path = tmp_path / "features.parquet"
        model_path = tmp_path / "model.joblib"
        results_path = tmp_path / "results.json"

        synthetic_df.write_parquet(features_path)

        results = run(
            features_path=features_path,
            model_path=model_path,
            results_path=results_path,
        )

        # Verify return structure
        assert "model_metadata" in results
        assert "correlation_anomaly_vs_rule_risk" in results
        assert "detection_rates" in results
        assert "top10_features_permutation_importance" in results

        # Verify metadata
        meta = results["model_metadata"]
        assert meta["model_type"] == "IsolationForest"
        assert meta["n_samples"] == len(synthetic_df)
        assert meta["n_features"] > 0

        # Verify files written
        assert results_path.exists()
        assert model_path.exists()

        # Verify correlation is a float in range
        corr = results["correlation_anomaly_vs_rule_risk"]
        assert isinstance(corr, float)
        assert -1.0 <= corr <= 1.0

    def test_detection_rates_structure(self, synthetic_df: pl.DataFrame, tmp_path) -> None:
        features_path = tmp_path / "features.parquet"
        synthetic_df.write_parquet(features_path)

        results = run(
            features_path=features_path,
            model_path=tmp_path / "m.joblib",
            results_path=tmp_path / "r.json",
        )
        det = results["detection_rates"]
        for key in ("top_5pct", "top_10pct", "top_20pct"):
            assert 0.0 <= det[key] <= 1.0
