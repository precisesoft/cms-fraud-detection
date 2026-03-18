"""Tests for src/data/project_graph — projection logic and helpers."""

from __future__ import annotations

from src.data.project_graph import (
    _SIGNAL_SOURCE_MAP,
    SOURCES,
    _risk_band,
)
from src.scoring.taxonomy import ALL_SIGNALS


class TestRiskBand:
    def test_none_is_stable(self):
        assert _risk_band(None) == "stable"

    def test_zero_is_stable(self):
        assert _risk_band(0) == "stable"

    def test_30_is_stable(self):
        assert _risk_band(30) == "stable"

    def test_31_is_review(self):
        assert _risk_band(31) == "review"

    def test_50_is_review(self):
        assert _risk_band(50) == "review"

    def test_51_is_high_risk(self):
        assert _risk_band(51) == "high_risk"

    def test_100_is_high_risk(self):
        assert _risk_band(100) == "high_risk"


class TestSources:
    def test_three_sources_defined(self):
        assert len(SOURCES) == 3

    def test_each_source_has_required_keys(self):
        for src in SOURCES:
            assert "dataset" in src
            assert "year" in src
            assert "url" in src

    def test_source_datasets_unique(self):
        datasets = [s["dataset"] for s in SOURCES]
        assert len(datasets) == len(set(datasets))


class TestSignalSourceMap:
    def test_all_categories_mapped(self):
        categories = {s.category.value for s in ALL_SIGNALS}
        for cat in categories:
            assert cat in _SIGNAL_SOURCE_MAP, f"Category {cat} missing from source map"

    def test_all_signals_have_source(self):
        for signal in ALL_SIGNALS:
            source = _SIGNAL_SOURCE_MAP.get(signal.category.value)
            assert source is not None, f"Signal {signal.name} has no source mapping"
            # Verify it maps to an actual source
            source_datasets = [s["dataset"] for s in SOURCES]
            # Special case for revoked_provider
            if signal.name == "revoked_provider":
                assert "CMS Provider Revocation File" in source_datasets
            else:
                assert source in source_datasets, (
                    f"Signal {signal.name} maps to unknown source: {source}"
                )


class TestCypherTemplates:
    def test_constraint_count_matches_node_types(self):
        from src.data.project_graph import _CREATE_CONSTRAINTS

        # 5 node types: Provider, Case, Signal, PeerGroup, Source
        assert len(_CREATE_CONSTRAINTS) == 5

    def test_all_constraints_use_merge_safe_pattern(self):
        from src.data.project_graph import _CREATE_CONSTRAINTS

        for c in _CREATE_CONSTRAINTS:
            assert "IF NOT EXISTS" in c
