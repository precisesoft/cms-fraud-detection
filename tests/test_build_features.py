"""Tests for the provider-level feature engineering pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from src.pipeline.build_features import (
    UpsertResult,
    build_charge_features,
    build_concentration_features,
    build_peer_z_features,
    build_provider_features,
    build_provider_features_from_db,
    build_provider_metadata,
    build_risk_seed_features,
    build_volume_features,
    main,
    read_demo_csv,
    save_features,
    upsert_provider_features,
)

DEMO_CSV = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "processed"
    / "demo"
    / "provider_service_cases_demo.csv"
)

# Minimal synthetic CSV for unit tests
SYNTHETIC_CSV = """\
case_id,npi,provider_last_org_name,provider_first_name,provider_credentials,provider_entity_code,provider_city,provider_state,provider_zip5,provider_type,medicare_participating_ind,hcpcs_cd,hcpcs_desc,place_of_service,tot_benes,tot_srvcs,tot_bene_day_srvcs,avg_submitted_charge,avg_medicare_allowed_amt,avg_medicare_payment_amt,estimated_case_payment_amt,services_per_bene,submitted_to_allowed_ratio,payment_to_allowed_ratio,provider_total_hcpcs_codes,provider_total_benes,provider_total_services,provider_total_payment_amt,present_in_2025_enrollment_file,enrollment_record_count,enrollment_provider_type_desc,enrollment_state_cd,present_in_2026_revocation_file,revocation_reason_summary,peer_scope,peer_case_count,peer_avg_tot_srvcs,service_volume_peer_z,services_per_bene_peer_z,submitted_to_allowed_peer_z,payment_peer_z,seed_risk_score,seed_legitimacy_score,seed_case_label,seed_risk_reasons,seed_legitimacy_reasons
1111111111|99213|O,1111111111,Test Clinic A,,,O,Springfield,IL,62701,Internal Medicine,Y,99213,Office Visit,O,100,200,200,75.0,50.0,40.0,8000.0,2.0,1.5,0.8,10,500,1000,40000.0,1,2,Internal Medicine,IL,0,,state_specific,100,150.0,1.5,0.5,0.8,0.3,20,70,stable,,peer_aligned_volume|peer_aligned_intensity
1111111111|99214|O,1111111111,Test Clinic A,,,O,Springfield,IL,62701,Internal Medicine,Y,99214,Office Visit Extended,O,80,300,300,120.0,80.0,65.0,19500.0,3.75,1.5,0.8125,10,500,1000,40000.0,1,2,Internal Medicine,IL,0,,state_specific,80,100.0,3.2,2.5,1.2,1.0,40,55,review,service_volume_outlier,
2222222222|J0135|F,2222222222,Dr Fraud,MD,,I,Miami,FL,33101,Cardiology,N,J0135,Adalimumab Injection,F,20,500,500,2000.0,100.0,90.0,45000.0,25.0,20.0,0.9,2,20,500,45000.0,0,0,,FL,1,False claims,national_fallback,30,50.0,8.0,6.0,5.5,4.0,80,10,high_risk,revoked_provider|service_volume_outlier|charge_ratio_outlier,
"""


@pytest.fixture
def synthetic_csv(tmp_path: Path) -> Path:
    csv_path = tmp_path / "test_demo.csv"
    csv_path.write_text(SYNTHETIC_CSV)
    return csv_path


@pytest.fixture
def synthetic_lf(synthetic_csv: Path) -> pl.LazyFrame:
    return read_demo_csv(synthetic_csv)


class TestReadDemoCsv:
    def test_reads_synthetic(self, synthetic_csv: Path):
        lf = read_demo_csv(synthetic_csv)
        df = lf.collect()
        assert df.shape[0] == 3
        assert "npi" in df.columns

    @pytest.mark.skipif(not DEMO_CSV.exists(), reason="Demo CSV not available")
    def test_reads_real_data(self):
        lf = read_demo_csv(DEMO_CSV)
        df = lf.collect()
        assert df.shape[0] > 10000


class TestVolumeFeatures:
    def test_shape(self, synthetic_lf: pl.LazyFrame):
        df = build_volume_features(synthetic_lf).collect()
        # 2 unique NPIs → 2 rows
        assert df.shape[0] == 2

    def test_aggregation(self, synthetic_lf: pl.LazyFrame):
        df = build_volume_features(synthetic_lf).collect()
        clinic_a = df.filter(pl.col("npi") == 1111111111)
        assert clinic_a["unique_hcpcs_codes"][0] == 2
        assert clinic_a["service_line_count"][0] == 2
        assert clinic_a["total_services"][0] == 500  # 200 + 300


class TestChargeFeatures:
    def test_shape(self, synthetic_lf: pl.LazyFrame):
        df = build_charge_features(synthetic_lf).collect()
        assert df.shape[0] == 2

    def test_charge_values(self, synthetic_lf: pl.LazyFrame):
        df = build_charge_features(synthetic_lf).collect()
        dr_fraud = df.filter(pl.col("npi") == 2222222222)
        assert dr_fraud["mean_submitted_charge"][0] == 2000.0
        assert dr_fraud["total_estimated_payment"][0] == 45000.0


class TestConcentrationFeatures:
    def test_single_code_hhi(self, synthetic_lf: pl.LazyFrame):
        df = build_concentration_features(synthetic_lf).collect()
        # Dr Fraud has 1 code → HHI = 1.0
        dr_fraud = df.filter(pl.col("npi") == 2222222222)
        assert dr_fraud["service_hhi"][0] == pytest.approx(1.0)
        assert dr_fraud["top_code_share"][0] == pytest.approx(1.0)

    def test_multi_code_hhi(self, synthetic_lf: pl.LazyFrame):
        df = build_concentration_features(synthetic_lf).collect()
        # Clinic A has 2 codes: 200/500=0.4 and 300/500=0.6 → HHI = 0.16+0.36 = 0.52
        clinic_a = df.filter(pl.col("npi") == 1111111111)
        assert clinic_a["service_hhi"][0] == pytest.approx(0.52)
        assert clinic_a["top_code_share"][0] == pytest.approx(0.6)


class TestPeerZFeatures:
    def test_outlier_counts(self, synthetic_lf: pl.LazyFrame):
        df = build_peer_z_features(synthetic_lf).collect()
        # Dr Fraud: volume_z=8.0 > 2, intensity_z=6.0 > 2, charge_z=5.5 > 2
        dr_fraud = df.filter(pl.col("npi") == 2222222222)
        assert dr_fraud["n_volume_outlier_lines"][0] == 1
        assert dr_fraud["n_intensity_outlier_lines"][0] == 1
        assert dr_fraud["n_charge_outlier_lines"][0] == 1

    def test_max_z(self, synthetic_lf: pl.LazyFrame):
        df = build_peer_z_features(synthetic_lf).collect()
        # Clinic A: max volume_z = max(1.5, 3.2) = 3.2
        clinic_a = df.filter(pl.col("npi") == 1111111111)
        assert clinic_a["max_volume_z"][0] == pytest.approx(3.2)


class TestRiskSeedFeatures:
    def test_risk_scores(self, synthetic_lf: pl.LazyFrame):
        df = build_risk_seed_features(synthetic_lf).collect()
        dr_fraud = df.filter(pl.col("npi") == 2222222222)
        assert dr_fraud["max_seed_risk_score"][0] == 80
        assert dr_fraud["n_high_risk_lines"][0] == 1

    def test_stable_provider(self, synthetic_lf: pl.LazyFrame):
        df = build_risk_seed_features(synthetic_lf).collect()
        clinic_a = df.filter(pl.col("npi") == 1111111111)
        assert clinic_a["max_seed_risk_score"][0] == 40
        assert clinic_a["n_high_risk_lines"][0] == 0


class TestProviderMetadata:
    def test_metadata(self, synthetic_lf: pl.LazyFrame):
        df = build_provider_metadata(synthetic_lf).collect()
        dr_fraud = df.filter(pl.col("npi") == 2222222222)
        assert dr_fraud["revoked_2026"][0] == 1
        assert dr_fraud["enrolled_2025"][0] == 0

        clinic_a = df.filter(pl.col("npi") == 1111111111)
        assert clinic_a["enrolled_2025"][0] == 1
        assert clinic_a["revoked_2026"][0] == 0


class TestFullPipeline:
    def test_end_to_end(self, synthetic_csv: Path):
        df = build_provider_features(synthetic_csv)
        assert df.shape[0] == 2
        assert df.shape[1] == 63

    def test_no_std_nulls(self, synthetic_csv: Path):
        df = build_provider_features(synthetic_csv)
        for col in ["std_submitted_charge", "std_payment_amt", "std_charge_ratio"]:
            assert df[col].null_count() == 0, f"{col} has nulls after fill"

    def test_derived_features(self, synthetic_csv: Path):
        df = build_provider_features(synthetic_csv)
        dr_fraud = df.filter(pl.col("npi") == 2222222222)
        # risk_legitimacy_gap = 80 - 10 = 70
        assert dr_fraud["risk_legitimacy_gap"][0] == 70
        # frac_volume_outlier_lines = 1/1 = 1.0 (single line, it's an outlier)
        assert dr_fraud["frac_volume_outlier_lines"][0] == pytest.approx(1.0)

    @pytest.mark.skipif(not DEMO_CSV.exists(), reason="Demo CSV not available")
    def test_real_data(self):
        df = build_provider_features(DEMO_CSV)
        assert df.shape[0] > 10000
        assert df["npi"].n_unique() == df.shape[0]  # One row per NPI


# ---------------------------------------------------------------------------
# TestSaveFeatures
# ---------------------------------------------------------------------------


class TestSaveFeatures:
    def test_save_features_creates_parent_dir(self, tmp_path: Path):
        """save_features creates the parent directory before writing."""
        output_path = tmp_path / "nested" / "dir" / "features.parquet"
        df = pl.DataFrame({"npi": [1111111111], "value": [1.0]})

        result = save_features(df, output_path)

        assert output_path.parent.exists()
        assert result == output_path

    def test_save_features_writes_parquet(self, tmp_path: Path):
        """save_features writes a readable Parquet file with expected content."""
        output_path = tmp_path / "features.parquet"
        df = pl.DataFrame({"npi": [1111111111, 2222222222], "score": [10, 80]})

        save_features(df, output_path)

        assert output_path.exists()
        loaded = pl.read_parquet(output_path)
        assert loaded.shape == df.shape
        assert loaded["npi"].to_list() == df["npi"].to_list()

    def test_save_features_returns_path(self, tmp_path: Path):
        """save_features returns the output path it was given."""
        output_path = tmp_path / "out.parquet"
        df = pl.DataFrame({"npi": [1]})
        result = save_features(df, output_path)
        assert result == output_path

    def test_save_features_empty_dataframe(self, tmp_path: Path):
        """save_features handles an empty DataFrame without error."""
        output_path = tmp_path / "empty.parquet"
        df = pl.DataFrame({"npi": [], "score": []})
        result = save_features(df, output_path)
        assert result == output_path
        loaded = pl.read_parquet(output_path)
        assert loaded.shape[0] == 0

    def test_save_features_mocked_io(self):
        """save_features calls mkdir and write_parquet on the correct objects."""
        fake_df = MagicMock(spec=pl.DataFrame)
        fake_path = MagicMock(spec=Path)
        fake_parent = MagicMock(spec=Path)
        fake_path.parent = fake_parent

        save_features(fake_df, fake_path)

        fake_parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        fake_df.write_parquet.assert_called_once_with(fake_path)


# ---------------------------------------------------------------------------
# TestMain (build_features)
# ---------------------------------------------------------------------------


class TestBuildFeaturesMain:
    """Tests for main() in build_features — covers lines 207-234."""

    def _make_fake_df(self, n_providers: int = 2) -> pl.DataFrame:
        """Build a minimal DataFrame that satisfies all main() column accesses."""
        return pl.DataFrame(
            {
                "npi": list(range(1000000000, 1000000000 + n_providers)),
                "revoked_2026": [1, 0][:n_providers],
                "n_high_risk_lines": [1, 0][:n_providers],
                "service_hhi": [0.8, 0.5][:n_providers],
                "std_submitted_charge": [0.0] * n_providers,
                "mean_submitted_charge": [100.0] * n_providers,
                "max_submitted_charge": [200.0] * n_providers,
                "min_seed_legitimacy_score": [20] * n_providers,
                "n_volume_outlier_lines": [1, 0][:n_providers],
                "service_line_count": [2, 3][:n_providers],
            }
        )

    def test_main_calls_build_provider_features(self):
        """main() calls build_provider_features() and save_features()."""
        fake_df = self._make_fake_df()

        with (
            patch(
                "src.pipeline.build_features.build_provider_features",
                return_value=fake_df,
            ) as mock_build,
            patch(
                "src.pipeline.build_features.save_features",
                return_value=Path("/fake/provider_features.parquet"),
            ) as mock_save,
            patch("builtins.print"),
        ):
            main()

        mock_build.assert_called_once_with()
        mock_save.assert_called_once_with(fake_df)

    def test_main_prints_shape(self):
        """main() prints a line containing the provider count and feature count."""
        fake_df = self._make_fake_df(n_providers=2)
        printed: list[str] = []

        with (
            patch(
                "src.pipeline.build_features.build_provider_features",
                return_value=fake_df,
            ),
            patch(
                "src.pipeline.build_features.save_features",
                return_value=Path("/fake/out.parquet"),
            ),
            patch(
                "builtins.print",
                side_effect=lambda *a, **k: printed.append(str(a[0]) if a else ""),
            ),
        ):
            main()

        combined = "\n".join(printed)
        assert "2" in combined  # n_providers
        assert str(fake_df.shape[1]) in combined  # n_features

    def test_main_prints_unique_npis(self):
        """main() prints the unique NPI count in the sanity-check block."""
        fake_df = self._make_fake_df(n_providers=2)
        printed: list[str] = []

        with (
            patch(
                "src.pipeline.build_features.build_provider_features",
                return_value=fake_df,
            ),
            patch(
                "src.pipeline.build_features.save_features",
                return_value=Path("/fake/out.parquet"),
            ),
            patch(
                "builtins.print",
                side_effect=lambda *a, **k: printed.append(str(a[0]) if a else ""),
            ),
        ):
            main()

        combined = "\n".join(printed)
        assert "Unique NPIs" in combined

    def test_main_prints_revoked_count(self):
        """main() prints the revoked provider count."""
        fake_df = self._make_fake_df(n_providers=2)
        printed: list[str] = []

        with (
            patch(
                "src.pipeline.build_features.build_provider_features",
                return_value=fake_df,
            ),
            patch(
                "src.pipeline.build_features.save_features",
                return_value=Path("/fake/out.parquet"),
            ),
            patch(
                "builtins.print",
                side_effect=lambda *a, **k: printed.append(str(a[0]) if a else ""),
            ),
        ):
            main()

        combined = "\n".join(printed)
        assert "Revoked providers" in combined

    def test_main_prints_saved_path(self):
        """main() prints the path that save_features returned."""
        fake_df = self._make_fake_df()
        saved_path = Path("/fake/provider_features.parquet")
        printed: list[str] = []

        with (
            patch(
                "src.pipeline.build_features.build_provider_features",
                return_value=fake_df,
            ),
            patch(
                "src.pipeline.build_features.save_features",
                return_value=saved_path,
            ),
            patch(
                "builtins.print",
                side_effect=lambda *a, **k: printed.append(str(a[0]) if a else ""),
            ),
        ):
            main()

        combined = "\n".join(printed)
        assert str(saved_path) in combined

    def test_main_prints_null_counts_when_present(self):
        """main() prints null-column info when columns have nulls."""
        # Build a DataFrame with one null in 'service_hhi'
        fake_df = pl.DataFrame(
            {
                "npi": [1000000000, 2000000000],
                "revoked_2026": [1, 0],
                "n_high_risk_lines": [1, 0],
                "service_hhi": [None, 0.5],
                "std_submitted_charge": [0.0, 0.0],
                "mean_submitted_charge": [100.0, 100.0],
                "max_submitted_charge": [200.0, 200.0],
                "min_seed_legitimacy_score": [20, 20],
                "n_volume_outlier_lines": [1, 0],
                "service_line_count": [2, 3],
            }
        )
        printed: list[str] = []

        with (
            patch(
                "src.pipeline.build_features.build_provider_features",
                return_value=fake_df,
            ),
            patch(
                "src.pipeline.build_features.save_features",
                return_value=Path("/fake/out.parquet"),
            ),
            patch(
                "builtins.print",
                side_effect=lambda *a, **k: printed.append(str(a[0]) if a else ""),
            ),
        ):
            main()

        combined = "\n".join(printed)
        assert "service_hhi" in combined

    def test_main_no_null_counts_skipped_silently(self):
        """main() does not print null info when all columns are complete."""
        fake_df = self._make_fake_df()
        printed: list[str] = []

        with (
            patch(
                "src.pipeline.build_features.build_provider_features",
                return_value=fake_df,
            ),
            patch(
                "src.pipeline.build_features.save_features",
                return_value=Path("/fake/out.parquet"),
            ),
            patch(
                "builtins.print",
                side_effect=lambda *a, **k: printed.append(str(a[0]) if a else ""),
            ),
        ):
            main()

        # "Null counts:" header is printed but no column-specific null lines follow
        combined = "\n".join(printed)
        assert "Null counts" in combined


# ---------------------------------------------------------------------------
# TestBuildProviderFeaturesFromDb
# ---------------------------------------------------------------------------


class TestBuildProviderFeaturesFromDb:
    """Tests for build_provider_features_from_db()."""

    def test_calls_read_database(self, synthetic_csv: Path) -> None:
        """build_provider_features_from_db reads from provider_service_cases."""
        # Build the expected DataFrame from CSV so we can return it from the mock
        expected_df = pl.read_csv(
            synthetic_csv,
            infer_schema_length=5000,
            null_values=["", "NA", "NULL"],
        )

        mock_conn = MagicMock()
        with patch(
            "src.pipeline.build_features.pl.read_database",
            return_value=expected_df,
        ) as mock_read:
            df = build_provider_features_from_db(mock_conn)

        mock_read.assert_called_once_with("SELECT * FROM provider_service_cases", mock_conn)
        assert df.shape[0] == 2  # 2 unique NPIs in synthetic CSV

    def test_produces_same_columns_as_csv_version(self, synthetic_csv: Path) -> None:
        """build_provider_features_from_db returns the same columns as build_provider_features."""
        csv_df = pl.read_csv(
            synthetic_csv,
            infer_schema_length=5000,
            null_values=["", "NA", "NULL"],
        )

        mock_conn = MagicMock()
        with patch("src.pipeline.build_features.pl.read_database", return_value=csv_df):
            db_df = build_provider_features_from_db(mock_conn)

        csv_result = build_provider_features(synthetic_csv)
        assert sorted(db_df.columns) == sorted(csv_result.columns)

    def test_aggregation_matches_csv_version(self, synthetic_csv: Path) -> None:
        """Aggregated values are identical whether source is CSV or Postgres mock."""
        csv_df = pl.read_csv(
            synthetic_csv,
            infer_schema_length=5000,
            null_values=["", "NA", "NULL"],
        )

        mock_conn = MagicMock()
        with patch("src.pipeline.build_features.pl.read_database", return_value=csv_df):
            db_df = build_provider_features_from_db(mock_conn)

        csv_result = build_provider_features(synthetic_csv)

        # Sort both by npi for comparison
        db_sorted = db_df.sort("npi")
        csv_sorted = csv_result.sort("npi")

        # Compare a few key aggregated columns
        for col in ["max_seed_risk_score", "service_line_count", "service_hhi"]:
            assert db_sorted[col].to_list() == csv_sorted[col].to_list(), f"Mismatch in {col}"


# ---------------------------------------------------------------------------
# TestUpsertProviderFeatures
# ---------------------------------------------------------------------------


def _make_upsert_df(n_providers: int = 2) -> pl.DataFrame:
    """Build a minimal feature DataFrame for upsert tests."""
    return pl.DataFrame(
        {
            "npi": [str(1111111111 + i) for i in range(n_providers)],
            "provider_name": [f"Provider {i}" for i in range(n_providers)],
            "max_seed_risk_score": [20 + i * 10 for i in range(n_providers)],
        }
    )


def _make_upsert_copy_ctx(mock_conn: MagicMock) -> MagicMock:
    """Wire up cursor().copy() on a mock connection for upsert tests."""
    copy_ctx = MagicMock()
    copy_obj = MagicMock()
    copy_ctx.__enter__ = MagicMock(return_value=copy_obj)
    copy_ctx.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.copy.return_value = copy_ctx
    return copy_obj


def _upsert_execute_seq(
    staging_count: int = 2,
    unchanged_count: int = 0,
    returning_rows: list[tuple[bool]] | None = None,
) -> list[MagicMock]:
    """Build the ordered execute() return values for upsert_provider_features."""
    if returning_rows is None:
        returning_rows = [(True,)] * staging_count
    return [
        MagicMock(),  # CREATE TEMP TABLE
        MagicMock(fetchone=MagicMock(return_value=(unchanged_count,))),  # pre-count unchanged
        MagicMock(fetchall=MagicMock(return_value=returning_rows)),  # INSERT RETURNING
    ]


class TestUpsertProviderFeatures:
    """Tests for upsert_provider_features()."""

    def test_returns_upsert_result(self) -> None:
        """upsert_provider_features returns an UpsertResult."""
        df = _make_upsert_df()
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = _upsert_execute_seq()
        _make_upsert_copy_ctx(mock_conn)

        result = upsert_provider_features(df, mock_conn)

        assert isinstance(result, UpsertResult)

    def test_all_inserts(self) -> None:
        """New NPIs → rows_inserted equals staging count."""
        df = _make_upsert_df(n_providers=2)
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = _upsert_execute_seq(
            staging_count=2,
            unchanged_count=0,
            returning_rows=[(True,), (True,)],
        )
        _make_upsert_copy_ctx(mock_conn)

        result = upsert_provider_features(df, mock_conn)

        assert result.rows_inserted == 2
        assert result.rows_updated == 0
        assert result.rows_unchanged == 0
        assert result.total == 2

    def test_all_unchanged(self) -> None:
        """Existing NPIs with identical data → rows_unchanged equals staging count."""
        df = _make_upsert_df(n_providers=2)
        mock_conn = MagicMock()
        # Staging=2, pre-count unchanged=2, RETURNING returns 2 (existing rows, xmax!=0)
        mock_conn.execute.side_effect = _upsert_execute_seq(
            staging_count=2,
            unchanged_count=2,
            returning_rows=[(False,), (False,)],
        )
        _make_upsert_copy_ctx(mock_conn)

        result = upsert_provider_features(df, mock_conn)

        assert result.rows_inserted == 0
        assert result.rows_unchanged == 2
        assert result.rows_updated == 0

    def test_mixed_delta(self) -> None:
        """Mix of insert/update/unchanged is accounted for correctly."""
        df = _make_upsert_df(n_providers=3)
        mock_conn = MagicMock()
        # 3 staging rows: 1 insert (True), 2 existing (False), 1 of those unchanged
        mock_conn.execute.side_effect = _upsert_execute_seq(
            staging_count=3,
            unchanged_count=1,
            returning_rows=[(True,), (False,), (False,)],
        )
        _make_upsert_copy_ctx(mock_conn)

        result = upsert_provider_features(df, mock_conn)

        assert result.rows_inserted == 1
        assert result.rows_unchanged == 1
        assert result.rows_updated == 1
        assert result.total == 3

    def test_uses_staging_table(self) -> None:
        """A TEMP staging table is created (no TRUNCATE on provider_features)."""
        df = _make_upsert_df()
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = _upsert_execute_seq()
        _make_upsert_copy_ctx(mock_conn)

        upsert_provider_features(df, mock_conn)

        execute_sqls = [c.args[0] for c in mock_conn.execute.call_args_list]
        assert any("CREATE TEMP TABLE" in s for s in execute_sqls)
        assert not any("TRUNCATE" in s for s in execute_sqls)

    def test_upsert_sql_on_conflict_npi(self) -> None:
        """INSERT statement uses ON CONFLICT (npi) DO UPDATE."""
        df = _make_upsert_df()
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = _upsert_execute_seq()
        _make_upsert_copy_ctx(mock_conn)

        upsert_provider_features(df, mock_conn)

        execute_sqls = [c.args[0] for c in mock_conn.execute.call_args_list]
        upsert_sql = next(s for s in execute_sqls if "ON CONFLICT" in s)
        assert "ON CONFLICT (npi) DO UPDATE" in upsert_sql

    def test_sets_last_scored_at(self) -> None:
        """Upsert SQL always sets last_scored_at = NOW()."""
        df = _make_upsert_df()
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = _upsert_execute_seq()
        _make_upsert_copy_ctx(mock_conn)

        upsert_provider_features(df, mock_conn)

        execute_sqls = [c.args[0] for c in mock_conn.execute.call_args_list]
        upsert_sql = next(s for s in execute_sqls if "ON CONFLICT" in s)
        assert "last_scored_at = NOW()" in upsert_sql

    def test_sets_pipeline_run_id_when_provided(self) -> None:
        """pipeline_run_id is included in the upsert when run_id is given."""
        df = _make_upsert_df()
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = _upsert_execute_seq()
        _make_upsert_copy_ctx(mock_conn)

        upsert_provider_features(df, mock_conn, run_id=42)

        execute_sqls = [c.args[0] for c in mock_conn.execute.call_args_list]
        upsert_sql = next(s for s in execute_sqls if "ON CONFLICT" in s)
        assert "pipeline_run_id" in upsert_sql
        assert "42" in upsert_sql

    def test_no_pipeline_run_id_when_none(self) -> None:
        """pipeline_run_id is omitted from the upsert when run_id is None."""
        df = _make_upsert_df()
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = _upsert_execute_seq()
        _make_upsert_copy_ctx(mock_conn)

        upsert_provider_features(df, mock_conn, run_id=None)

        execute_sqls = [c.args[0] for c in mock_conn.execute.call_args_list]
        upsert_sql = next(s for s in execute_sqls if "ON CONFLICT" in s)
        # pipeline_run_id should not appear in the INSERT column list or SET clause
        # when run_id is None
        # (it may appear in other execute calls like unchanged pre-count)
        insert_part = upsert_sql.split("ON CONFLICT")[0]
        assert "pipeline_run_id" not in insert_part

    def test_commits(self) -> None:
        """upsert_provider_features calls conn.commit()."""
        df = _make_upsert_df()
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = _upsert_execute_seq()
        _make_upsert_copy_ctx(mock_conn)

        upsert_provider_features(df, mock_conn)

        mock_conn.commit.assert_called_once()
