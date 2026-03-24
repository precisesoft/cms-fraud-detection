"""Tests for src/models/weak_supervised.py."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

pytest.importorskip("joblib")
pytest.importorskip("numpy")
pl = pytest.importorskip("polars")
pytest.importorskip("sklearn")

from src.models.weak_supervised import (  # noqa: E402
    FEATURE_COLS,
    build_feature_row,
    compute_anomaly_score,
    compute_composite_score,
    compute_provider_context_score,
    compute_rule_component_score,
    compute_rule_score,
    load_training_frame,
    run_training,
    save_bundle,
    save_results,
    score_observation,
    train_model,
    write_training_artifacts_to_db,
)


class _FakeScaler:
    def transform(self, values):
        return values


class _FakeModel:
    def predict_proba(self, values):
        return [[0.18, 0.82]]


class _MatrixFakeModel:
    def fit(self, x_values, y_values):
        self.fit_shape = (len(x_values), len(y_values))

    def predict_proba(self, x_values):
        return [[0.4, 0.6] for _ in x_values]


class _DbFakeModel:
    def predict_proba(self, x_values):
        import numpy as np

        return np.array([[0.2, 0.8] for _ in x_values])


def _training_frame():
    rows = []
    for index in range(12):
        base = float(index + 1)
        row = {feature: base for feature in FEATURE_COLS}
        row["observation_id"] = f"obs-{index}"
        row["npi"] = f"npi-{index % 3}"
        row["weak_label"] = 1 if index % 2 == 0 else 0
        row["is_revoked"] = 1.0 if index % 4 == 0 else 0.0
        row["is_excluded"] = 1.0 if index % 5 == 0 else 0.0
        row["submitted_to_allowed_ratio"] = 4.2 if index % 3 == 0 else 1.4
        row["services_per_bene"] = 3.5 if index % 3 == 0 else 1.2
        row["peer_avg_spb"] = 1.0
        row["validation_issue_count"] = 1.0 if index % 6 == 0 else 0.0
        row["present_in_2026_revocation_file"] = row["is_revoked"]
        row["present_in_2025_enrollment_file"] = 1.0
        rows.append(row)
    return pl.DataFrame(rows)


def test_compute_rule_score_uses_revocation_and_enrollment_only():
    row = {
        "present_in_2026_revocation_file": 1,
        "present_in_2025_enrollment_file": 0,
        "is_excluded": 1,
    }
    assert compute_rule_score(row) == 35.0


def test_compute_anomaly_score_uses_charge_z_and_spb_ratio():
    row = {
        "submitted_to_allowed_peer_z": 2.0,
        "services_per_bene": 9.0,
        "peer_avg_spb": 3.0,
    }
    assert compute_anomaly_score(row) == 50.0


def test_compute_provider_context_score_uses_proxies_when_needed():
    row = {
        "provider_total_payment_amt": 250000.0,
        "unique_hcpcs_codes": 10,
        "unique_place_of_service": 5,
    }
    assert compute_provider_context_score(row) == 6.0


def test_build_feature_row_maps_runtime_keys():
    row = {
        "avg_submitted_charge": 120.0,
        "mean_allowed_amt": 80.0,
        "mean_payment_amt": 60.0,
        "tot_srvcs": 20.0,
        "tot_benes": 10.0,
        "seed_risk_score": 44.0,
        "submitted_to_allowed_peer_z": 1.5,
        "services_per_bene_peer_z": 0.5,
        "mean_submitted_charge": 130.0,
        "avg_services_per_bene": 2.5,
        "mean_payment_ratio": 0.6,
        "revoked_2026": 0,
        "unique_hcpcs_codes": 4,
        "unique_place_of_service": 2,
    }
    features = build_feature_row(row)
    assert features["avg_allowed_amount"] == 80.0
    assert features["hybrid_risk_score"] == 44.0
    assert features["graph_node_degree"] == 6.0


def test_score_observation_returns_percent_probability():
    row = {
        "avg_submitted_charge": 100.0,
        "avg_medicare_allowed_amt": 60.0,
        "avg_medicare_payment_amt": 50.0,
        "tot_srvcs": 10.0,
        "tot_benes": 5.0,
        "submitted_to_allowed_peer_z": 1.0,
        "services_per_bene": 2.0,
        "peer_avg_spb": 1.0,
        "seed_risk_score": 40.0,
        "mean_submitted_charge": 100.0,
        "avg_services_per_bene": 2.0,
        "mean_payment_ratio": 0.5,
        "revoked_2026": 0,
        "unique_hcpcs_codes": 3,
        "unique_place_of_service": 2,
        "provider_total_payment_amt": 200000.0,
    }
    fake_bundle = {
        "model": _FakeModel(),
        "scaler": _FakeScaler(),
        "feature_cols": list(build_feature_row(row).keys()),
    }
    with patch("src.models.weak_supervised._load_bundle", return_value=fake_bundle):
        result = score_observation(row)
    assert result == 82.0


def test_score_observation_returns_none_without_ml_libs():
    with patch("src.models.weak_supervised._RUNTIME_ML_AVAILABLE", False):
        assert score_observation({}) is None


def test_score_observation_returns_none_when_bundle_load_fails():
    with patch(
        "src.models.weak_supervised._load_bundle",
        side_effect=RuntimeError("missing bundle"),
    ):
        assert score_observation({"avg_submitted_charge": 10.0}) is None


def test_compute_rule_component_score_and_composite_floor_for_revocation():
    row = {
        "is_revoked": 1.0,
        "is_excluded": 0.0,
        "submitted_to_allowed_ratio": 1.0,
        "services_per_bene": 1.0,
        "peer_avg_spb": 1.0,
        "provider_total_payment_amt": 100000.0,
        "unique_hcpcs_codes": 5,
        "graph_node_degree": 10.0,
    }
    assert compute_rule_component_score(row) == 40.0
    score, label = compute_composite_score(row, 10.0)
    assert score == 92.0
    assert label == "critical"


def test_compute_composite_score_uses_extreme_behavior_floor():
    row = {
        "is_revoked": 0.0,
        "is_excluded": 0.0,
        "submitted_to_allowed_ratio": 4.5,
        "services_per_bene": 3.5,
        "peer_avg_spb": 1.0,
        "submitted_to_allowed_peer_z": 0.5,
        "provider_total_payment_amt": 50000.0,
        "unique_hcpcs_codes": 3,
        "graph_node_degree": 5.0,
    }
    score, label = compute_composite_score(row, 20.0)
    assert score == 70.0
    assert label == "high"


def test_train_model_returns_bundle_and_metrics():
    bundle, metrics = train_model(_training_frame())
    assert bundle["metadata"]["model_type"] == "LogisticRegression"
    assert bundle["feature_cols"] == FEATURE_COLS
    assert metrics["train_rows"] > 0
    assert metrics["test_rows"] > 0
    assert metrics["roc_auc"] is not None
    assert metrics["average_precision"] is not None


def test_train_model_requires_two_classes():
    df = _training_frame().with_columns(pl.lit(1).alias("weak_label"))
    with pytest.raises(ValueError, match="requires both positive and negative"):
        train_model(df)


def test_save_bundle_and_results_write_files(tmp_path):
    bundle_path = tmp_path / "models" / "bundle.joblib"
    results_path = tmp_path / "validation" / "results.json"
    metrics = {
        "train_rows": 8,
        "test_rows": 2,
        "positive_rate_train": 0.5,
        "positive_rate_test": 0.5,
        "roc_auc": 0.9,
        "average_precision": 0.8,
    }

    saved_bundle = save_bundle({"model": "fake"}, bundle_path)
    saved_results = save_results(metrics, results_path)

    assert saved_bundle == bundle_path
    assert saved_results == results_path
    assert bundle_path.exists()
    assert json.loads(results_path.read_text()) == metrics


def test_load_training_frame_uses_imported_deps():
    rows = [{"observation_id": "obs-1", "weak_label": 1}]

    class _FakeCursor:
        def execute(self, sql):
            self.sql = sql

        def fetchall(self):
            return rows

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    class _FakeConn:
        def cursor(self):
            return _FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    class _FakePsycopg:
        @staticmethod
        def connect(database_url, row_factory=None):
            assert database_url == "postgresql://example"
            assert row_factory == "dict-row"
            return _FakeConn()

    fake_polars = SimpleNamespace(DataFrame=lambda values: {"rows": values})

    deps = {"psycopg": _FakePsycopg, "dict_row": "dict-row", "pl": fake_polars}
    with patch("src.models.weak_supervised._import_training_deps", return_value=deps):
        frame = load_training_frame("postgresql://example")

    assert frame == {"rows": rows}


def test_write_training_artifacts_to_db_inserts_model_and_scores():
    executed: list[tuple[str, tuple | None]] = []

    class _FakeCursor:
        def execute(self, sql, params=None):
            executed.append((sql, params))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    class _FakeConn:
        def cursor(self):
            return _FakeCursor()

        def commit(self):
            executed.append(("COMMIT", None))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    class _FakePsycopg:
        @staticmethod
        def connect(database_url):
            assert database_url == "postgresql://example"
            return _FakeConn()

    bundle = {
        "model": _DbFakeModel(),
        "scaler": _FakeScaler(),
        "metadata": {"model_type": "LogisticRegression"},
    }
    metrics = {
        "train_rows": 8,
        "test_rows": 2,
        "positive_rate_train": 0.5,
        "positive_rate_test": 0.5,
        "roc_auc": 0.9,
        "average_precision": 0.8,
    }
    deps = {"psycopg": _FakePsycopg}

    with patch("src.models.weak_supervised._import_training_deps", return_value=deps):
        write_training_artifacts_to_db(
            _training_frame(),
            bundle,
            metrics,
            "postgresql://example",
            "weak_supervised_k8s_model",
            "v-test",
        )

    assert any("INSERT INTO trained_models" in sql for sql, _ in executed)
    assert any("INSERT INTO observation_model_scores" in sql for sql, _ in executed)
    assert executed[-1][0] == "COMMIT"


def test_run_training_calls_db_write_when_enabled(tmp_path):
    df = _training_frame()
    bundle = {"model": _MatrixFakeModel(), "scaler": _FakeScaler(), "metadata": {}}
    metrics = {
        "train_rows": 8,
        "test_rows": 2,
        "positive_rate_train": 0.5,
        "positive_rate_test": 0.5,
        "roc_auc": 0.9,
        "average_precision": 0.8,
    }

    with (
        patch("src.models.weak_supervised.load_training_frame", return_value=df),
        patch("src.models.weak_supervised.train_model", return_value=(bundle, metrics)),
        patch("src.models.weak_supervised.save_bundle") as save_bundle_mock,
        patch("src.models.weak_supervised.save_results") as save_results_mock,
        patch("src.models.weak_supervised.write_training_artifacts_to_db") as write_db_mock,
    ):
        result = run_training(
            database_url="postgresql://example",
            model_path=tmp_path / "bundle.joblib",
            results_path=tmp_path / "results.json",
            model_name="weak_supervised_k8s_model",
            model_version="v-test",
            no_db_write=False,
        )

    assert result == metrics
    save_bundle_mock.assert_called_once()
    save_results_mock.assert_called_once()
    write_db_mock.assert_called_once_with(
        df,
        bundle,
        metrics,
        "postgresql://example",
        "weak_supervised_k8s_model",
        "v-test",
    )


def test_run_training_raises_when_frame_is_empty(tmp_path):
    empty_df = pl.DataFrame({"weak_label": []})
    with patch("src.models.weak_supervised.load_training_frame", return_value=empty_df):
        with pytest.raises(ValueError, match="No labeled rows available"):
            run_training(
                database_url="postgresql://example",
                model_path=tmp_path / "bundle.joblib",
                results_path=tmp_path / "results.json",
            )
