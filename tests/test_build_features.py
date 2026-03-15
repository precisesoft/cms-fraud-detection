"""Tests for the provider-level feature engineering pipeline."""

from __future__ import annotations

import io
from pathlib import Path

import polars as pl
import pytest

from src.pipeline.build_features import (
    build_charge_features,
    build_concentration_features,
    build_peer_z_features,
    build_provider_features,
    build_provider_metadata,
    build_risk_seed_features,
    build_volume_features,
    read_demo_csv,
)

DEMO_CSV = Path(__file__).resolve().parents[1] / "data" / "processed" / "demo" / "provider_service_cases_demo.csv"

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
