"""Tests for src/data/project_graph — projection logic and helpers."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from src.data.project_graph import (
    _SIGNAL_SOURCE_MAP,
    SOURCES,
    _risk_band,
)
from src.scoring.taxonomy import ALL_SIGNALS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_neo4j_driver():
    """Return a mock AsyncDriver whose .session() is an async context manager."""
    mock_session = AsyncMock()

    @asynccontextmanager
    async def _session_ctx():
        yield mock_session

    mock_driver = MagicMock()
    mock_driver.session = _session_ctx
    mock_driver.verify_connectivity = AsyncMock()
    mock_driver.close = AsyncMock()
    return mock_driver, mock_session


def _make_async_cursor_iter(rows: list):
    """
    Build a mock psycopg async cursor that yields `rows` when iterated with
    `async for row in cur`.  Also supports .execute() as an AsyncMock.
    """
    mock_cur = AsyncMock()
    mock_cur.execute = AsyncMock()

    # Build an async iterator over the supplied rows.
    async def _aiter(self):
        for row in rows:
            yield row

    mock_cur.__aiter__ = lambda self: _aiter(mock_cur)
    return mock_cur


def _make_pg_conn(cursor_mock):
    """
    Return a mock psycopg.AsyncConnection that works as an async context
    manager and yields cursor_mock from .cursor().
    """

    @asynccontextmanager
    async def _cursor_ctx(*args, **kwargs):
        yield cursor_mock

    mock_conn = MagicMock()
    mock_conn.cursor = _cursor_ctx

    # Make connect() return an object that is itself an async context manager
    # wrapping mock_conn.
    async def _connect_aenter(self):
        return mock_conn

    async def _connect_aexit(self, *exc):
        return False

    mock_aconn = MagicMock()
    mock_aconn.__aenter__ = _connect_aenter
    mock_aconn.__aexit__ = _connect_aexit
    return mock_aconn


# ---------------------------------------------------------------------------
# _risk_band
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# SOURCES
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# _SIGNAL_SOURCE_MAP
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Cypher templates
# ---------------------------------------------------------------------------


class TestCypherTemplates:
    def test_constraint_count_matches_node_types(self):
        from src.data.project_graph import _CREATE_CONSTRAINTS

        # 5 node types: Provider, Case, Signal, PeerGroup, Source
        assert len(_CREATE_CONSTRAINTS) == 5

    def test_all_constraints_use_merge_safe_pattern(self):
        from src.data.project_graph import _CREATE_CONSTRAINTS

        for c in _CREATE_CONSTRAINTS:
            assert "IF NOT EXISTS" in c


# ---------------------------------------------------------------------------
# _create_constraints
# ---------------------------------------------------------------------------


class TestCreateConstraints:
    async def test_runs_all_constraints(self):
        from src.data.project_graph import _CREATE_CONSTRAINTS, _create_constraints

        driver, session = _make_neo4j_driver()
        await _create_constraints(driver)

        assert session.run.await_count == len(_CREATE_CONSTRAINTS)
        actual_calls = [c.args[0] for c in session.run.call_args_list]
        assert actual_calls == _CREATE_CONSTRAINTS


# ---------------------------------------------------------------------------
# _project_sources
# ---------------------------------------------------------------------------


class TestProjectSources:
    async def test_merges_source_nodes(self):
        from src.data.project_graph import _MERGE_SOURCES, _project_sources

        driver, session = _make_neo4j_driver()
        await _project_sources(driver)

        session.run.assert_awaited_once_with(_MERGE_SOURCES, rows=SOURCES)


# ---------------------------------------------------------------------------
# _project_signals
# ---------------------------------------------------------------------------


class TestProjectSignals:
    async def test_runs_merge_and_link_queries(self):
        from src.data.project_graph import (
            _LINK_SIGNAL_SOURCE,
            _MERGE_SIGNALS,
            _project_signals,
        )

        driver, session = _make_neo4j_driver()
        await _project_signals(driver)

        assert session.run.await_count == 2
        first_call, second_call = session.run.call_args_list
        assert first_call.args[0] == _MERGE_SIGNALS
        assert second_call.args[0] == _LINK_SIGNAL_SOURCE

    async def test_signal_rows_contain_all_signals(self):
        from src.data.project_graph import _project_signals

        driver, session = _make_neo4j_driver()
        await _project_signals(driver)

        signal_rows = session.run.call_args_list[0].kwargs["rows"]
        signal_names = {r["name"] for r in signal_rows}
        expected_names = {s.name for s in ALL_SIGNALS}
        assert signal_names == expected_names

    async def test_revoked_provider_linked_to_revocation_file(self):
        from src.data.project_graph import _project_signals

        driver, session = _make_neo4j_driver()
        await _project_signals(driver)

        link_rows = session.run.call_args_list[1].kwargs["rows"]
        revoked_row = next(r for r in link_rows if r["signal_name"] == "revoked_provider")
        assert revoked_row["source_dataset"] == "CMS Provider Revocation File"

    async def test_signal_rows_have_required_keys(self):
        from src.data.project_graph import _project_signals

        driver, session = _make_neo4j_driver()
        await _project_signals(driver)

        signal_rows = session.run.call_args_list[0].kwargs["rows"]
        for row in signal_rows:
            for key in ("name", "category", "direction", "description", "points"):
                assert key in row, f"Missing key {key!r} in signal row for {row.get('name')}"


# ---------------------------------------------------------------------------
# _project_providers
# ---------------------------------------------------------------------------


class TestProjectProviders:
    async def test_projects_small_batch_under_batch_size(self):
        """A result set smaller than BATCH_SIZE is flushed in the final tail flush."""
        from src.data.project_graph import _MERGE_PROVIDERS, _project_providers

        rows = [
            ("NPI001", "Dr A", "MD", "CA", "Los Angeles", "90001", 10, True, False),
            ("NPI002", "Dr B", "DO", "NY", "New York", "10001", 60, True, True),
        ]
        mock_cur = _make_async_cursor_iter(rows)
        mock_aconn = _make_pg_conn(mock_cur)
        driver, session = _make_neo4j_driver()

        with patch("psycopg.AsyncConnection.connect", return_value=mock_aconn):
            count = await _project_providers(driver, "postgresql://fake/db")

        assert count == 2
        session.run.assert_awaited_once()
        call_kwargs = session.run.call_args
        assert call_kwargs.args[0] == _MERGE_PROVIDERS
        merged = call_kwargs.kwargs["rows"]
        assert len(merged) == 2
        assert merged[0]["npi"] == "NPI001"
        assert merged[0]["risk_band"] == "stable"
        assert merged[1]["risk_band"] == "high_risk"

    async def test_projects_exact_batch_size_triggers_mid_loop_flush(self):
        """When batch reaches BATCH_SIZE, it is flushed mid-loop; remainder flushed at end."""
        from src.data.project_graph import BATCH_SIZE, _project_providers

        # Create exactly BATCH_SIZE + 1 rows so we get one mid-loop flush and one tail flush.
        rows = [
            (f"NPI{i:04d}", f"Dr {i}", "MD", "TX", "Austin", "73301", 20, True, False)
            for i in range(BATCH_SIZE + 1)
        ]
        mock_cur = _make_async_cursor_iter(rows)
        mock_aconn = _make_pg_conn(mock_cur)
        driver, session = _make_neo4j_driver()

        with patch("psycopg.AsyncConnection.connect", return_value=mock_aconn):
            count = await _project_providers(driver, "postgresql://fake/db")

        assert count == BATCH_SIZE + 1
        # Two session.run calls: one for the full batch, one for the leftover row.
        assert session.run.await_count == 2

    async def test_empty_table_returns_zero(self):
        """An empty provider_features table returns 0 and makes no Neo4j calls."""
        from src.data.project_graph import _project_providers

        mock_cur = _make_async_cursor_iter([])
        mock_aconn = _make_pg_conn(mock_cur)
        driver, session = _make_neo4j_driver()

        with patch("psycopg.AsyncConnection.connect", return_value=mock_aconn):
            count = await _project_providers(driver, "postgresql://fake/db")

        assert count == 0
        session.run.assert_not_awaited()

    async def test_risk_band_mapping_applied_per_row(self):
        """_risk_band is applied to column index 6 for each row."""
        from src.data.project_graph import _project_providers

        rows = [
            ("A", "Name", "MD", "CA", "City", "90001", None, False, False),  # stable
            ("B", "Name", "MD", "CA", "City", "90001", 40, True, False),     # review
            ("C", "Name", "MD", "CA", "City", "90001", 75, True, True),      # high_risk
        ]
        mock_cur = _make_async_cursor_iter(rows)
        mock_aconn = _make_pg_conn(mock_cur)
        driver, session = _make_neo4j_driver()

        with patch("psycopg.AsyncConnection.connect", return_value=mock_aconn):
            await _project_providers(driver, "postgresql://fake/db")

        merged = session.run.call_args.kwargs["rows"]
        bands = {r["npi"]: r["risk_band"] for r in merged}
        assert bands["A"] == "stable"
        assert bands["B"] == "review"
        assert bands["C"] == "high_risk"


# ---------------------------------------------------------------------------
# _project_cases_and_signals
# ---------------------------------------------------------------------------


def _case_row(
    case_id="CASE001",
    npi="NPI001",
    hcpcs_cd="99213",
    provider_type="Internal Medicine",
    peer_case_count=30,
    peer_scope="state",
    seed_risk_score=20,
    seed_legitimacy_score=80,
    seed_case_label="stable",
):
    """Return a dict-like row matching provider_service_cases schema."""
    return {
        "case_id": case_id,
        "npi": npi,
        "hcpcs_cd": hcpcs_cd,
        "provider_type": provider_type,
        "peer_case_count": peer_case_count,
        "peer_scope": peer_scope,
        "seed_risk_score": seed_risk_score,
        "seed_legitimacy_score": seed_legitimacy_score,
        "seed_case_label": seed_case_label,
        # Fields consumed by extract_signals — provide safe defaults
        "enrolled_2025": True,
        "revoked_2026": False,
        "total_services": 100,
        "total_unique_benes": 50,
        "total_submitted_chrg_amt": 10000.0,
        "total_medicare_payment_amt": 8000.0,
        "avg_submitted_chrg_amt": 100.0,
        "avg_medicare_payment_amt": 80.0,
        "peer_avg_submitted_chrg_amt": 95.0,
        "peer_avg_medicare_payment_amt": 76.0,
        "peer_z_submitted_chrg_amt": 0.5,
        "peer_z_service_count": 0.3,
        "peer_z_bene_count": 0.2,
        "peer_z_payment_amt": 0.4,
        "is_participating": True,
    }


class TestProjectCasesAndSignals:
    async def test_single_case_no_peer(self):
        """A case with peer_case_count=0 skips peer group creation."""
        from src.data.project_graph import _MERGE_CASES, _project_cases_and_signals

        row = _case_row(peer_case_count=0, peer_scope="")
        mock_cur = _make_async_cursor_iter([row])
        mock_aconn = _make_pg_conn(mock_cur)
        driver, session = _make_neo4j_driver()

        with patch("psycopg.AsyncConnection.connect", return_value=mock_aconn):
            count = await _project_cases_and_signals(driver, "postgresql://fake/db")

        assert count == 1
        # At minimum _MERGE_CASES must have been called
        cypher_calls = [c.args[0] for c in session.run.call_args_list]
        assert _MERGE_CASES in cypher_calls

    async def test_single_case_with_peer(self):
        """A case with a peer group triggers _MERGE_PEER_GROUP."""
        from src.data.project_graph import (
            _MERGE_CASES,
            _MERGE_PEER_GROUP,
            _project_cases_and_signals,
        )

        row = _case_row(peer_case_count=50, peer_scope="national")
        mock_cur = _make_async_cursor_iter([row])
        mock_aconn = _make_pg_conn(mock_cur)
        driver, session = _make_neo4j_driver()

        with patch("psycopg.AsyncConnection.connect", return_value=mock_aconn):
            count = await _project_cases_and_signals(driver, "postgresql://fake/db")

        assert count == 1
        cypher_calls = [c.args[0] for c in session.run.call_args_list]
        assert _MERGE_CASES in cypher_calls
        assert _MERGE_PEER_GROUP in cypher_calls

    async def test_empty_table_returns_zero(self):
        """Empty provider_service_cases returns 0; no Neo4j calls."""
        from src.data.project_graph import _project_cases_and_signals

        mock_cur = _make_async_cursor_iter([])
        mock_aconn = _make_pg_conn(mock_cur)
        driver, session = _make_neo4j_driver()

        with patch("psycopg.AsyncConnection.connect", return_value=mock_aconn):
            count = await _project_cases_and_signals(driver, "postgresql://fake/db")

        assert count == 0
        session.run.assert_not_awaited()

    async def test_batch_overflow_triggers_mid_loop_flush(self):
        """BATCH_SIZE+1 rows produce a mid-loop flush plus a tail flush."""
        from src.data.project_graph import BATCH_SIZE, _project_cases_and_signals

        rows = [
            _case_row(
                case_id=f"CASE{i:04d}",
                npi=f"NPI{i:04d}",
                peer_case_count=0,
            )
            for i in range(BATCH_SIZE + 1)
        ]
        mock_cur = _make_async_cursor_iter(rows)
        mock_aconn = _make_pg_conn(mock_cur)
        driver, session = _make_neo4j_driver()

        with patch("psycopg.AsyncConnection.connect", return_value=mock_aconn):
            count = await _project_cases_and_signals(driver, "postgresql://fake/db")

        assert count == BATCH_SIZE + 1
        # Each flush calls at least _MERGE_CASES, so at least 2 run() calls total.
        assert session.run.await_count >= 2

    async def test_batch_with_peer_and_signals_at_overflow(self):
        """At BATCH_SIZE boundary with peers and signals, all three queries fire."""
        from src.data.project_graph import (
            BATCH_SIZE,
            _MERGE_CASE_SIGNALS,
            _MERGE_CASES,
            _MERGE_PEER_GROUP,
            _project_cases_and_signals,
        )

        # BATCH_SIZE rows with peers so every flush includes peer+signal queries
        # enrolled_2025=True is already the default in _case_row
        rows = [
            _case_row(
                case_id=f"CASE{i:04d}",
                npi=f"NPI{i:04d}",
                peer_case_count=30,
                peer_scope="state",
            )
            for i in range(BATCH_SIZE)
        ]
        mock_cur = _make_async_cursor_iter(rows)
        mock_aconn = _make_pg_conn(mock_cur)
        driver, session = _make_neo4j_driver()

        with patch("psycopg.AsyncConnection.connect", return_value=mock_aconn):
            count = await _project_cases_and_signals(driver, "postgresql://fake/db")

        assert count == BATCH_SIZE
        cypher_calls = [c.args[0] for c in session.run.call_args_list]
        assert _MERGE_CASES in cypher_calls
        assert _MERGE_PEER_GROUP in cypher_calls
        assert _MERGE_CASE_SIGNALS in cypher_calls

    async def test_case_row_fields_mapped_correctly(self):
        """Verify case dict keys are populated from the row correctly."""
        from src.data.project_graph import _MERGE_CASES, _project_cases_and_signals

        row = _case_row(
            case_id="CASEABC",
            npi="NPI999",
            hcpcs_cd="G0008",
            seed_risk_score=55,
            seed_legitimacy_score=10,
            seed_case_label="high_risk",
            peer_case_count=0,
        )
        mock_cur = _make_async_cursor_iter([row])
        mock_aconn = _make_pg_conn(mock_cur)
        driver, session = _make_neo4j_driver()

        with patch("psycopg.AsyncConnection.connect", return_value=mock_aconn):
            await _project_cases_and_signals(driver, "postgresql://fake/db")

        # Find the _MERGE_CASES call (not the last call, which may be signals)
        cases_call = next(
            c for c in session.run.call_args_list if c.args[0] == _MERGE_CASES
        )
        case_rows = cases_call.kwargs["rows"]
        assert len(case_rows) == 1
        cr = case_rows[0]
        assert cr["case_id"] == "CASEABC"
        assert cr["npi"] == "NPI999"
        assert cr["hcpcs_cd"] == "G0008"
        assert cr["risk_score"] == 55
        assert cr["legitimacy_score"] == 10
        assert cr["label"] == "high_risk"

    async def test_peer_scope_none_skips_peer_batch(self):
        """peer_case_count > 0 but peer_scope=None/empty skips peer group."""
        from src.data.project_graph import _MERGE_PEER_GROUP, _project_cases_and_signals

        row = _case_row(peer_case_count=10, peer_scope=None)
        # peer_scope=None means the condition `row.get("peer_scope")` is falsy
        row["peer_scope"] = None
        mock_cur = _make_async_cursor_iter([row])
        mock_aconn = _make_pg_conn(mock_cur)
        driver, session = _make_neo4j_driver()

        with patch("psycopg.AsyncConnection.connect", return_value=mock_aconn):
            await _project_cases_and_signals(driver, "postgresql://fake/db")

        cypher_calls = [c.args[0] for c in session.run.call_args_list]
        assert _MERGE_PEER_GROUP not in cypher_calls


# ---------------------------------------------------------------------------
# run_projection
# ---------------------------------------------------------------------------


class TestRunProjection:
    async def test_full_pipeline_returns_counts(self):
        """run_projection wires all helpers and returns provider/case counts."""
        from src.data.project_graph import run_projection

        mock_driver = AsyncMock()
        mock_driver.verify_connectivity = AsyncMock()
        mock_driver.close = AsyncMock()

        mock_result = AsyncMock()
        mock_summary = MagicMock()
        mock_summary.counters.relationships_created = 7
        mock_result.consume = AsyncMock(return_value=mock_summary)

        mock_session = AsyncMock()
        mock_session.run = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def _session_ctx():
            yield mock_session

        mock_driver.session = _session_ctx

        with (
            patch(
                "src.data.project_graph.AsyncGraphDatabase.driver",
                return_value=mock_driver,
            ),
            patch(
                "src.data.project_graph._create_constraints",
                new=AsyncMock(),
            ),
            patch(
                "src.data.project_graph._project_sources",
                new=AsyncMock(),
            ),
            patch(
                "src.data.project_graph._project_signals",
                new=AsyncMock(),
            ),
            patch(
                "src.data.project_graph._project_providers",
                new=AsyncMock(return_value=42),
            ),
            patch(
                "src.data.project_graph._project_cases_and_signals",
                new=AsyncMock(return_value=100),
            ),
        ):
            result = await run_projection(
                pg_conninfo="postgresql://fake/db",
                neo4j_uri="bolt://fake:7687",
                neo4j_user="neo4j",
                neo4j_password="secret",
            )

        assert result == {"providers": 42, "cases": 100}

    async def test_driver_always_closed_on_success(self):
        """run_projection closes the driver in the finally block."""
        from src.data.project_graph import run_projection

        mock_driver = AsyncMock()
        mock_driver.verify_connectivity = AsyncMock()
        mock_driver.close = AsyncMock()

        mock_result = AsyncMock()
        mock_summary = MagicMock()
        mock_summary.counters.relationships_created = 0
        mock_result.consume = AsyncMock(return_value=mock_summary)
        mock_session = AsyncMock()
        mock_session.run = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def _session_ctx():
            yield mock_session

        mock_driver.session = _session_ctx

        with (
            patch("src.data.project_graph.AsyncGraphDatabase.driver", return_value=mock_driver),
            patch("src.data.project_graph._create_constraints", new=AsyncMock()),
            patch("src.data.project_graph._project_sources", new=AsyncMock()),
            patch("src.data.project_graph._project_signals", new=AsyncMock()),
            patch("src.data.project_graph._project_providers", new=AsyncMock(return_value=0)),
            patch(
                "src.data.project_graph._project_cases_and_signals",
                new=AsyncMock(return_value=0),
            ),
        ):
            await run_projection()

        mock_driver.close.assert_awaited_once()

    async def test_driver_closed_even_on_error(self):
        """run_projection closes the driver even if an inner step raises."""
        from src.data.project_graph import run_projection

        mock_driver = AsyncMock()
        mock_driver.verify_connectivity = AsyncMock()
        mock_driver.close = AsyncMock()

        with (
            patch("src.data.project_graph.AsyncGraphDatabase.driver", return_value=mock_driver),
            patch(
                "src.data.project_graph._create_constraints",
                new=AsyncMock(side_effect=RuntimeError("Neo4j boom")),
            ),
        ):
            with pytest.raises(RuntimeError, match="Neo4j boom"):
                await run_projection()

        mock_driver.close.assert_awaited_once()

    async def test_same_zip_and_same_org_rels_queried(self):
        """run_projection runs SAME_ZIP and SAME_ORG cypher inside the session."""
        from src.data.project_graph import (
            _CREATE_SAME_ORG_RELS,
            _CREATE_SAME_ZIP_RELS,
            run_projection,
        )

        mock_driver = AsyncMock()
        mock_driver.verify_connectivity = AsyncMock()
        mock_driver.close = AsyncMock()

        mock_result = AsyncMock()
        mock_summary = MagicMock()
        mock_summary.counters.relationships_created = 3
        mock_result.consume = AsyncMock(return_value=mock_summary)
        mock_session = AsyncMock()
        mock_session.run = AsyncMock(return_value=mock_result)

        @asynccontextmanager
        async def _session_ctx():
            yield mock_session

        mock_driver.session = _session_ctx

        with (
            patch("src.data.project_graph.AsyncGraphDatabase.driver", return_value=mock_driver),
            patch("src.data.project_graph._create_constraints", new=AsyncMock()),
            patch("src.data.project_graph._project_sources", new=AsyncMock()),
            patch("src.data.project_graph._project_signals", new=AsyncMock()),
            patch("src.data.project_graph._project_providers", new=AsyncMock(return_value=5)),
            patch(
                "src.data.project_graph._project_cases_and_signals",
                new=AsyncMock(return_value=5),
            ),
        ):
            await run_projection()

        run_cyphers = [c.args[0] for c in mock_session.run.call_args_list]
        assert _CREATE_SAME_ZIP_RELS in run_cyphers
        assert _CREATE_SAME_ORG_RELS in run_cyphers


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


class TestMain:
    def test_main_calls_asyncio_run(self):
        """main() calls asyncio.run(run_projection()) and does not raise."""
        from src.data.project_graph import main

        expected_counts = {"providers": 10, "cases": 20}

        with patch(
            "src.data.project_graph.asyncio.run",
            return_value=expected_counts,
        ) as mock_run:
            main()

        mock_run.assert_called_once()
        # The argument to asyncio.run is a coroutine — verify it's a coroutine object
        # from run_projection (we can't compare coroutine identity directly, but we
        # can check the coroutine's __qualname__).
        coro_arg = mock_run.call_args.args[0]
        assert hasattr(coro_arg, "cr_code") or hasattr(coro_arg, "__await__")
        coro_arg.close()  # clean up the unawaited coroutine
