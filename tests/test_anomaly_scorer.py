"""Tests for src/models/anomaly_scorer.py — runtime IsolationForest scorer."""

from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("sklearn")
pytest.importorskip("joblib")

from unittest.mock import patch  # noqa: E402

import joblib  # noqa: E402
from sklearn.ensemble import IsolationForest  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from src.models.anomaly_scorer import _load_bundle, score_provider  # noqa: E402

# ---------------------------------------------------------------------------
# Constants shared across tests
# ---------------------------------------------------------------------------

FEATURE_COLS = [
    "total_benes",
    "total_services",
    "mean_payment_amt",
    "mean_charge_ratio",
    "service_hhi",
    "max_volume_z",
    "n_charge_outlier_lines",
    "frac_volume_outlier_lines",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def model_bundle(tmp_path) -> tuple:
    """Train a real IsolationForest + StandardScaler and save a bundle to tmp_path.

    Returns (bundle_path, feature_cols) so tests can patch MODEL_PATH.
    """
    rng = np.random.default_rng(42)
    n = 200
    x_raw = rng.uniform(0, 100, (n, len(FEATURE_COLS))).astype(np.float64)

    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x_raw)

    model = IsolationForest(n_estimators=20, contamination=0.05, random_state=42)
    model.fit(x_scaled)

    bundle_path = tmp_path / "isolation_forest.joblib"
    joblib.dump(
        {"model": model, "scaler": scaler, "feature_cols": FEATURE_COLS},
        bundle_path,
    )
    return bundle_path, FEATURE_COLS


@pytest.fixture(autouse=True)
def clear_lru_cache():
    """Clear the _load_bundle lru_cache before and after every test."""
    _load_bundle.cache_clear()
    yield
    _load_bundle.cache_clear()


@pytest.fixture()
def typical_feature_row() -> dict:
    """A representative feature dict that matches FEATURE_COLS."""
    return {
        "total_benes": 250.0,
        "total_services": 1200.0,
        "mean_payment_amt": 85.0,
        "mean_charge_ratio": 1.5,
        "service_hhi": 0.3,
        "max_volume_z": 0.4,
        "n_charge_outlier_lines": 2,
        "frac_volume_outlier_lines": 0.05,
    }


# ---------------------------------------------------------------------------
# Tests: normal scoring path
# ---------------------------------------------------------------------------


class TestScoreProviderNormalPath:
    def test_valid_features_returns_float(self, model_bundle, typical_feature_row) -> None:
        bundle_path, _ = model_bundle
        with patch("src.models.anomaly_scorer.MODEL_PATH", bundle_path):
            result = score_provider(typical_feature_row)
        assert isinstance(result, float), "score_provider should return a float"

    def test_score_in_valid_range(self, model_bundle, typical_feature_row) -> None:
        bundle_path, _ = model_bundle
        with patch("src.models.anomaly_scorer.MODEL_PATH", bundle_path):
            result = score_provider(typical_feature_row)
        assert result is not None
        assert 0.0 <= result <= 100.0, f"Score {result} outside [0, 100]"

    def test_score_rounded_to_one_decimal(self, model_bundle, typical_feature_row) -> None:
        bundle_path, _ = model_bundle
        with patch("src.models.anomaly_scorer.MODEL_PATH", bundle_path):
            result = score_provider(typical_feature_row)
        assert result is not None
        # round(x, 1) produces at most one decimal place
        assert result == round(result, 1)

    def test_multiple_calls_consistent(self, model_bundle, typical_feature_row) -> None:
        """Repeated calls with the same input return the same score (model is deterministic)."""
        bundle_path, _ = model_bundle
        with patch("src.models.anomaly_scorer.MODEL_PATH", bundle_path):
            score_a = score_provider(typical_feature_row)
            score_b = score_provider(typical_feature_row)
        assert score_a == score_b, "Scores must be deterministic for identical input"


# ---------------------------------------------------------------------------
# Tests: edge cases
# ---------------------------------------------------------------------------


class TestScoreProviderEdgeCases:
    def test_empty_feature_dict_defaults_to_zeros(self, model_bundle) -> None:
        """Missing keys are treated as 0 — should still return a valid score."""
        bundle_path, _ = model_bundle
        with patch("src.models.anomaly_scorer.MODEL_PATH", bundle_path):
            result = score_provider({})
        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0

    def test_all_zero_features_produces_valid_score(self, model_bundle) -> None:
        bundle_path, _ = model_bundle
        zero_row = {col: 0.0 for col in FEATURE_COLS}
        with patch("src.models.anomaly_scorer.MODEL_PATH", bundle_path):
            result = score_provider(zero_row)
        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0

    def test_nan_features_treated_as_zero(self, model_bundle) -> None:
        """NaN values are coerced to 0 via `float(x) or 0` logic in scorer."""
        bundle_path, _ = model_bundle
        nan_row = {col: float("nan") for col in FEATURE_COLS}
        with patch("src.models.anomaly_scorer.MODEL_PATH", bundle_path):
            result = score_provider(nan_row)
        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0

    def test_extra_unknown_keys_are_ignored(self, model_bundle, typical_feature_row) -> None:
        """Extra keys beyond the known feature_cols should not cause errors."""
        bundle_path, _ = model_bundle
        row_with_extras = {**typical_feature_row, "unknown_col": 999.0, "another_extra": -5.0}
        with patch("src.models.anomaly_scorer.MODEL_PATH", bundle_path):
            result = score_provider(row_with_extras)
        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0

    def test_single_provider_feature_row(self, model_bundle) -> None:
        """A single-provider dict still produces a valid score."""
        bundle_path, _ = model_bundle
        single_row = {FEATURE_COLS[0]: 42.0}  # only one feature provided
        with patch("src.models.anomaly_scorer.MODEL_PATH", bundle_path):
            result = score_provider(single_row)
        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0


# ---------------------------------------------------------------------------
# Tests: score bounds / clamping
# ---------------------------------------------------------------------------


class TestScoreProviderBounds:
    def test_extreme_low_decision_function_clamps_to_100(self, model_bundle) -> None:
        """When decision_function returns a very negative value, score clamps to 100."""
        bundle_path, _ = model_bundle

        # Patch _load_bundle to inject a model whose decision_function always returns -1.0
        class _FakeModel:
            def decision_function(self, x):
                return np.array([-1.0])

        class _IdentityScaler:
            def transform(self, x):
                return x

        fake_bundle = {
            "model": _FakeModel(),
            "scaler": _IdentityScaler(),
            "feature_cols": FEATURE_COLS,
        }
        with patch("src.models.anomaly_scorer._load_bundle", return_value=fake_bundle):
            result = score_provider({col: 1.0 for col in FEATURE_COLS})
        # 50.0 - (-1.0 * 100) = 150 → clamped to 100
        assert result == 100.0

    def test_extreme_high_decision_function_clamps_to_zero(self, model_bundle) -> None:
        """When decision_function returns a very positive value, score clamps to 0."""

        class _FakeModel:
            def decision_function(self, x):
                return np.array([1.0])

        class _IdentityScaler:
            def transform(self, x):
                return x

        fake_bundle = {
            "model": _FakeModel(),
            "scaler": _IdentityScaler(),
            "feature_cols": FEATURE_COLS,
        }
        with patch("src.models.anomaly_scorer._load_bundle", return_value=fake_bundle):
            result = score_provider({col: 1.0 for col in FEATURE_COLS})
        # 50.0 - (1.0 * 100) = -50 → clamped to 0
        assert result == 0.0

    def test_neutral_decision_function_yields_midpoint(self) -> None:
        """decision_function = 0.0 → normalized = 50.0."""

        class _FakeModel:
            def decision_function(self, x):
                return np.array([0.0])

        class _IdentityScaler:
            def transform(self, x):
                return x

        fake_bundle = {
            "model": _FakeModel(),
            "scaler": _IdentityScaler(),
            "feature_cols": FEATURE_COLS,
        }
        with patch("src.models.anomaly_scorer._load_bundle", return_value=fake_bundle):
            result = score_provider({col: 1.0 for col in FEATURE_COLS})
        assert result == 50.0

    def test_score_always_in_range_over_many_providers(self, model_bundle) -> None:
        """Scores for a batch of synthetic providers all lie within [0, 100]."""
        bundle_path, _ = model_bundle
        rng = np.random.default_rng(7)
        rows = [
            {
                col: float(v)
                for col, v in zip(FEATURE_COLS, rng.uniform(-10, 200, len(FEATURE_COLS)))
            }
            for _ in range(50)
        ]
        with patch("src.models.anomaly_scorer.MODEL_PATH", bundle_path):
            scores = [score_provider(row) for row in rows]
        assert all(s is not None for s in scores)
        assert all(0.0 <= s <= 100.0 for s in scores), "All scores must be in [0, 100]"  # type: ignore[operator]


# ---------------------------------------------------------------------------
# Tests: model loading (graceful error handling)
# ---------------------------------------------------------------------------


class TestModelLoading:
    def test_missing_model_file_returns_none(self, tmp_path) -> None:
        """If the model file does not exist, score_provider returns None gracefully."""
        missing_path = tmp_path / "does_not_exist.joblib"
        with patch("src.models.anomaly_scorer.MODEL_PATH", missing_path):
            result = score_provider({"total_benes": 100.0})
        assert result is None, "Should return None when model file is missing"

    def test_corrupt_model_file_returns_none(self, tmp_path) -> None:
        """A corrupt (non-joblib) file causes score_provider to return None gracefully."""
        corrupt_path = tmp_path / "corrupt.joblib"
        corrupt_path.write_bytes(b"this is not a valid joblib file %%%")
        with patch("src.models.anomaly_scorer.MODEL_PATH", corrupt_path):
            result = score_provider({"total_benes": 100.0})
        assert result is None, "Should return None when model file is corrupt"

    def test_load_bundle_caches_result(self, model_bundle) -> None:
        """_load_bundle uses lru_cache — the same bundle object is returned on repeated calls."""
        bundle_path, _ = model_bundle
        with patch("src.models.anomaly_scorer.MODEL_PATH", bundle_path):
            bundle_first = _load_bundle()
            bundle_second = _load_bundle()
        assert bundle_first is bundle_second, "_load_bundle result should be cached (same object)"

    def test_load_bundle_raises_on_missing_file(self, tmp_path) -> None:
        """_load_bundle raises an exception (not silently) when the file is absent."""
        missing_path = tmp_path / "no_model.joblib"
        with patch("src.models.anomaly_scorer.MODEL_PATH", missing_path):
            with pytest.raises(Exception):
                _load_bundle()

    def test_bundle_has_required_keys(self, model_bundle) -> None:
        """The loaded bundle must contain model, scaler, and feature_cols keys."""
        bundle_path, _ = model_bundle
        with patch("src.models.anomaly_scorer.MODEL_PATH", bundle_path):
            bundle = _load_bundle()
        assert "model" in bundle
        assert "scaler" in bundle
        assert "feature_cols" in bundle
        assert isinstance(bundle["feature_cols"], list)


# ---------------------------------------------------------------------------
# Tests: integration with anomaly.py / downstream consumption
# ---------------------------------------------------------------------------


class TestMLUnavailable:
    def test_returns_none_when_ml_unavailable(self, typical_feature_row) -> None:
        """If ML libraries are not installed, score_provider returns None immediately."""
        with patch("src.models.anomaly_scorer._ML_AVAILABLE", False):
            result = score_provider(typical_feature_row)
        assert result is None, "Should return None when _ML_AVAILABLE is False"

    def test_returns_none_empty_row_when_ml_unavailable(self) -> None:
        """Even an empty feature row returns None gracefully when ML is unavailable."""
        with patch("src.models.anomaly_scorer._ML_AVAILABLE", False):
            result = score_provider({})
        assert result is None


class TestIntegrationWithDownstream:
    def test_scorer_output_compatible_with_risk_band(
        self, model_bundle, typical_feature_row
    ) -> None:
        """Scores from score_provider fall within the risk-band input domain [0, 100]."""
        from src.api.schemas import risk_band_from_score  # noqa: PLC0415

        bundle_path, _ = model_bundle
        with patch("src.models.anomaly_scorer.MODEL_PATH", bundle_path):
            score = score_provider(typical_feature_row)

        assert score is not None
        band = risk_band_from_score(int(score))
        assert band in {"stable", "review", "high_risk"}, f"Unexpected band: {band}"

    def test_low_anomaly_score_maps_to_stable_band(self, model_bundle) -> None:
        """A near-zero anomaly score (normal provider) maps to stable risk band."""
        from src.api.schemas import risk_band_from_score  # noqa: PLC0415

        # Inject a model whose decision_function returns +0.4 → score ≈ 10 (stable)
        class _FakeModel:
            def decision_function(self, x):
                return np.array([0.4])

        class _IdentityScaler:
            def transform(self, x):
                return x

        fake_bundle = {
            "model": _FakeModel(),
            "scaler": _IdentityScaler(),
            "feature_cols": FEATURE_COLS,
        }
        with patch("src.models.anomaly_scorer._load_bundle", return_value=fake_bundle):
            score = score_provider({col: 1.0 for col in FEATURE_COLS})

        assert score is not None
        assert score <= 30.0, f"Expected stable-range score, got {score}"
        band = risk_band_from_score(int(score))
        assert band == "stable"

    def test_high_anomaly_score_maps_to_high_risk_band(self, model_bundle) -> None:
        """A high anomaly score (anomalous provider) maps to high_risk risk band."""
        from src.api.schemas import risk_band_from_score  # noqa: PLC0415

        # Inject a model whose decision_function returns -0.5 → score = 100 (clamped)
        class _FakeModel:
            def decision_function(self, x):
                return np.array([-0.5])

        class _IdentityScaler:
            def transform(self, x):
                return x

        fake_bundle = {
            "model": _FakeModel(),
            "scaler": _IdentityScaler(),
            "feature_cols": FEATURE_COLS,
        }
        with patch("src.models.anomaly_scorer._load_bundle", return_value=fake_bundle):
            score = score_provider({col: 1.0 for col in FEATURE_COLS})

        assert score is not None
        assert score >= 51.0, f"Expected high-risk-range score, got {score}"
        band = risk_band_from_score(int(score))
        assert band == "high_risk"

    def test_scorer_feature_cols_subset_of_anomaly_feature_cols(self, model_bundle) -> None:
        """Feature columns used by the scorer are a subset of what anomaly.py selects."""
        import polars as pl  # noqa: PLC0415

        from src.models.anomaly import select_feature_columns  # noqa: PLC0415

        _, feature_cols = model_bundle

        # Build a minimal DataFrame that includes FEATURE_COLS as numeric columns
        n = 10
        rng = np.random.default_rng(99)
        data = {col: rng.uniform(0, 100, n).tolist() for col in FEATURE_COLS}
        data["npi"] = list(range(n))
        df = pl.DataFrame(data)

        selected = select_feature_columns(df)
        # The scorer's feature_cols must be a subset of what the training pipeline selects
        assert set(feature_cols).issubset(set(selected)), (
            "Scorer feature_cols must be compatible with anomaly.py feature selection"
        )
