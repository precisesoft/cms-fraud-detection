"""Tests for the deterministic chart spec generator."""

from src.ai.chart_spec import generate_chart_spec


def test_bar_chart_categorical_plus_numeric():
    columns = ["state", "high_risk_count"]
    rows = [
        {"state": "FL", "high_risk_count": 42},
        {"state": "TX", "high_risk_count": 35},
        {"state": "CA", "high_risk_count": 28},
    ]
    spec = generate_chart_spec(columns, rows)
    assert spec is not None
    assert spec["type"] == "bar"
    assert spec["xKey"] == "state"
    assert spec["yKey"] == "high_risk_count"
    assert len(spec["data"]) == 3


def test_line_chart_time_series():
    columns = ["year", "total_payment"]
    rows = [
        {"year": 2020, "total_payment": 1000000},
        {"year": 2021, "total_payment": 1200000},
        {"year": 2022, "total_payment": 1500000},
    ]
    spec = generate_chart_spec(columns, rows)
    assert spec is not None
    assert spec["type"] == "line"
    assert spec["xKey"] == "year"
    assert spec["yKey"] == "total_payment"


def test_pie_chart_share_data():
    columns = ["risk_band", "flagging_rate"]
    rows = [
        {"risk_band": "high_risk", "flagging_rate": 0.85},
        {"risk_band": "review", "flagging_rate": 0.42},
        {"risk_band": "stable", "flagging_rate": 0.05},
    ]
    spec = generate_chart_spec(columns, rows)
    assert spec is not None
    assert spec["type"] == "pie"
    assert spec["nameKey"] == "risk_band"
    assert spec["valueKey"] == "flagging_rate"


def test_bar_chart_risk_band_with_count():
    columns = ["risk_band", "provider_count"]
    rows = [
        {"risk_band": "high_risk", "provider_count": 153},
        {"risk_band": "review", "provider_count": 420},
        {"risk_band": "stable", "provider_count": 9709},
    ]
    spec = generate_chart_spec(columns, rows)
    assert spec is not None
    assert spec["type"] == "bar"
    assert spec["xKey"] == "risk_band"


def test_no_chart_for_scalar():
    columns = ["total"]
    rows = [{"total": 153}]
    spec = generate_chart_spec(columns, rows)
    assert spec is None


def test_no_chart_for_single_row():
    columns = ["npi", "name", "score"]
    rows = [{"npi": "1234567890", "name": "Test", "score": 85}]
    spec = generate_chart_spec(columns, rows)
    assert spec is None


def test_no_chart_for_all_text_columns():
    columns = ["npi", "name", "state"]
    rows = [
        {"npi": "111", "name": "A", "state": "FL"},
        {"npi": "222", "name": "B", "state": "TX"},
    ]
    spec = generate_chart_spec(columns, rows)
    assert spec is None


def test_bar_chart_provider_type_with_score():
    columns = ["provider_type", "outlier_count", "avg_volume_z"]
    rows = [
        {"provider_type": "Internal Medicine", "outlier_count": 50, "avg_volume_z": 3.2},
        {"provider_type": "Cardiology", "outlier_count": 30, "avg_volume_z": 2.8},
        {"provider_type": "Clinical Lab", "outlier_count": 25, "avg_volume_z": 4.1},
    ]
    spec = generate_chart_spec(columns, rows)
    assert spec is not None
    assert spec["type"] == "bar"
    assert spec["xKey"] == "provider_type"


def test_data_capped_at_20():
    columns = ["state", "count"]
    rows = [{"state": f"S{i}", "count": i} for i in range(30)]
    spec = generate_chart_spec(columns, rows)
    assert spec is not None
    assert len(spec["data"]) == 20


def test_nan_replaced_with_zero():
    columns = ["state", "avg_score"]
    rows = [
        {"state": "FL", "avg_score": float("nan")},
        {"state": "TX", "avg_score": 42.5},
    ]
    spec = generate_chart_spec(columns, rows)
    assert spec is not None
    assert spec["data"][0]["avg_score"] == 0
