"""Provider-level feature engineering from demo case CSV or Postgres.

Reads per-service rows and aggregates to one row per NPI with features
designed for anomaly detection and supervised fraud classification.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

from src.data.load_postgres import UpsertResult

if TYPE_CHECKING:
    import psycopg

ROOT = Path(__file__).resolve().parents[2]
DEMO_CSV = ROOT / "data" / "processed" / "demo" / "provider_service_cases_demo.csv"
OUTPUT_DIR = ROOT / "data" / "features"
OUTPUT_PARQUET = OUTPUT_DIR / "provider_features.parquet"


def read_demo_csv(path: Path = DEMO_CSV) -> pl.LazyFrame:
    """Read the demo case CSV into a Polars LazyFrame."""
    return pl.scan_csv(
        path,
        infer_schema_length=5000,
        null_values=["", "NA", "NULL"],
    )


def build_volume_features(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Aggregate service volume and diversity per provider."""
    return lf.group_by("npi").agg(
        # Service diversity
        pl.col("hcpcs_cd").n_unique().alias("unique_hcpcs_codes"),
        pl.col("place_of_service").n_unique().alias("unique_place_of_service"),
        pl.len().alias("service_line_count"),
        # Volume
        pl.col("tot_benes").sum().alias("total_benes"),
        pl.col("tot_srvcs").sum().alias("total_services"),
        pl.col("tot_bene_day_srvcs").sum().alias("total_bene_day_services"),
        # Averages per service line
        pl.col("tot_benes").mean().alias("avg_benes_per_line"),
        pl.col("tot_srvcs").mean().alias("avg_services_per_line"),
        pl.col("services_per_bene").mean().alias("avg_services_per_bene"),
        pl.col("services_per_bene").max().alias("max_services_per_bene"),
        pl.col("services_per_bene").std().alias("std_services_per_bene"),
    )


def build_charge_features(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Aggregate charge and payment patterns per provider."""
    return lf.group_by("npi").agg(
        # Charges
        pl.col("avg_submitted_charge").mean().alias("mean_submitted_charge"),
        pl.col("avg_submitted_charge").max().alias("max_submitted_charge"),
        pl.col("avg_submitted_charge").std().alias("std_submitted_charge"),
        # Allowed amounts
        pl.col("avg_medicare_allowed_amt").mean().alias("mean_allowed_amt"),
        pl.col("avg_medicare_allowed_amt").max().alias("max_allowed_amt"),
        # Payment
        pl.col("avg_medicare_payment_amt").mean().alias("mean_payment_amt"),
        pl.col("avg_medicare_payment_amt").max().alias("max_payment_amt"),
        pl.col("avg_medicare_payment_amt").std().alias("std_payment_amt"),
        pl.col("estimated_case_payment_amt").sum().alias("total_estimated_payment"),
        # Ratios
        pl.col("submitted_to_allowed_ratio").mean().alias("mean_charge_ratio"),
        pl.col("submitted_to_allowed_ratio").max().alias("max_charge_ratio"),
        pl.col("submitted_to_allowed_ratio").std().alias("std_charge_ratio"),
        pl.col("payment_to_allowed_ratio").mean().alias("mean_payment_ratio"),
    )


def build_concentration_features(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Compute service concentration metrics (HHI, top-code share)."""
    # Compute each service's share of provider's total services
    with_share = lf.with_columns(
        (pl.col("tot_srvcs") / pl.col("tot_srvcs").sum().over("npi")).alias("service_share"),
    )

    return with_share.group_by("npi").agg(
        # Herfindahl-Hirschman Index: sum of squared shares (1/N = uniform, 1.0 = single code)
        (pl.col("service_share").pow(2).sum()).alias("service_hhi"),
        # Top code's share of total services
        pl.col("service_share").max().alias("top_code_share"),
        # Share of top 3 codes
        pl.col("service_share").sort(descending=True).head(3).sum().alias("top3_code_share"),
    )


def build_peer_z_features(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Aggregate peer-relative z-scores per provider."""
    return lf.group_by("npi").agg(
        # Volume z-scores across service lines
        pl.col("service_volume_peer_z").mean().alias("mean_volume_z"),
        pl.col("service_volume_peer_z").max().alias("max_volume_z"),
        # Intensity z-scores
        pl.col("services_per_bene_peer_z").mean().alias("mean_intensity_z"),
        pl.col("services_per_bene_peer_z").max().alias("max_intensity_z"),
        # Charge z-scores
        pl.col("submitted_to_allowed_peer_z").mean().alias("mean_charge_z"),
        pl.col("submitted_to_allowed_peer_z").max().alias("max_charge_z"),
        # Payment z-scores
        pl.col("payment_peer_z").mean().alias("mean_payment_z"),
        pl.col("payment_peer_z").max().alias("max_payment_z"),
        # Count of service lines with z > 2 (outlier lines)
        (pl.col("service_volume_peer_z") > 2.0).sum().alias("n_volume_outlier_lines"),
        (pl.col("services_per_bene_peer_z") > 2.0).sum().alias("n_intensity_outlier_lines"),
        (pl.col("submitted_to_allowed_peer_z") > 2.0).sum().alias("n_charge_outlier_lines"),
    )


def build_risk_seed_features(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Aggregate seed risk/legitimacy scores and signals per provider."""
    return lf.group_by("npi").agg(
        # Seed scores (take worst-case and average across service lines)
        pl.col("seed_risk_score").max().alias("max_seed_risk_score"),
        pl.col("seed_risk_score").mean().alias("avg_seed_risk_score"),
        pl.col("seed_legitimacy_score").min().alias("min_seed_legitimacy_score"),
        pl.col("seed_legitimacy_score").mean().alias("avg_seed_legitimacy_score"),
        # Count of high-risk service lines
        (pl.col("seed_case_label") == "high_risk").sum().alias("n_high_risk_lines"),
        # Peer scope: how many lines had state-specific vs national fallback
        (pl.col("peer_scope") == "state_specific").sum().alias("n_state_peer_lines"),
    )


def build_provider_metadata(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Extract provider-level metadata (first occurrence per NPI)."""
    return lf.group_by("npi").agg(
        pl.col("provider_last_org_name").first().alias("provider_name"),
        pl.col("provider_entity_code").first().alias("entity_code"),
        pl.col("provider_city").first().alias("city"),
        pl.col("provider_state").first().alias("state"),
        pl.col("provider_zip5").first().alias("zip5"),
        pl.col("provider_type").first().alias("provider_type"),
        pl.col("medicare_participating_ind").first().alias("medicare_participating"),
        # Provider-level totals (same across service lines for a given NPI)
        pl.col("provider_total_hcpcs_codes").first().alias("provider_total_hcpcs_codes"),
        pl.col("provider_total_benes").first().alias("provider_total_benes"),
        pl.col("provider_total_services").first().alias("provider_total_services"),
        pl.col("provider_total_payment_amt").first().alias("provider_total_payment_amt"),
        # Enrollment & revocation (same across service lines)
        pl.col("present_in_2025_enrollment_file").first().alias("enrolled_2025"),
        pl.col("enrollment_record_count").first().alias("enrollment_record_count"),
        pl.col("present_in_2026_revocation_file").first().alias("revoked_2026"),
        pl.col("revocation_reason_summary").first().alias("revocation_reason"),
    )


def _assemble_features(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Join all feature groups and compute derived columns.

    Shared by :func:`build_provider_features` and
    :func:`build_provider_features_from_db`.
    """
    metadata = build_provider_metadata(lf)
    volume = build_volume_features(lf)
    charges = build_charge_features(lf)
    concentration = build_concentration_features(lf)
    peer_z = build_peer_z_features(lf)
    risk_seed = build_risk_seed_features(lf)

    features = (
        metadata.join(volume, on="npi")
        .join(charges, on="npi")
        .join(concentration, on="npi")
        .join(peer_z, on="npi")
        .join(risk_seed, on="npi")
    )

    # Fill std-based nulls (single-line providers have no variance)
    std_cols = [
        "std_services_per_bene",
        "std_submitted_charge",
        "std_payment_amt",
        "std_charge_ratio",
    ]
    features = features.with_columns([pl.col(c).fill_null(0.0) for c in std_cols])

    # Compute derived features after join
    return features.with_columns(
        (pl.col("max_seed_risk_score") - pl.col("min_seed_legitimacy_score")).alias(
            "risk_legitimacy_gap"
        ),
        (
            pl.col("n_volume_outlier_lines").cast(pl.Float64)
            / pl.col("service_line_count").cast(pl.Float64)
        ).alias("frac_volume_outlier_lines"),
        (pl.col("std_submitted_charge") / pl.col("mean_submitted_charge")).alias("charge_cv"),
    )


def build_provider_features(csv_path: Path = DEMO_CSV) -> pl.DataFrame:
    """Build the full provider-level feature matrix.

    Joins volume, charge, concentration, peer z-score, risk seed,
    and metadata features into a single DataFrame — one row per NPI.
    """
    lf = read_demo_csv(csv_path)
    return _assemble_features(lf).collect()


def build_provider_features_from_db(conn: psycopg.Connection) -> pl.DataFrame:  # type: ignore[name-defined]
    """Build the provider-level feature matrix by reading from Postgres.

    Reads all rows from ``provider_service_cases`` via
    ``pl.read_database`` and applies the same aggregation logic as
    :func:`build_provider_features`.  Returns a DataFrame ready for upsert.
    """
    df = pl.read_database("SELECT * FROM provider_service_cases", conn)
    return _assemble_features(df.lazy()).collect()


def save_features(df: pl.DataFrame, output_path: Path = OUTPUT_PARQUET) -> Path:
    """Write the feature DataFrame to Parquet."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(output_path)
    return output_path


def upsert_provider_features(
    df: pl.DataFrame,
    conn: psycopg.Connection,  # type: ignore[name-defined]
    run_id: int | None = None,
) -> UpsertResult:
    """Upsert a provider feature DataFrame into ``provider_features``.

    Uses a staging-table pattern (``COPY`` → ``INSERT … ON CONFLICT (npi)
    DO UPDATE``) so the operation is idempotent.

    ``last_scored_at`` and ``pipeline_run_id`` are updated on every call;
    other columns are updated only when the feature data has changed.
    ``rows_unchanged`` counts NPIs whose feature data was identical to what
    is already stored (metadata timestamps are still refreshed for those rows).

    Args:
        df: Provider feature DataFrame (typically from
            :func:`build_provider_features` or
            :func:`build_provider_features_from_db`).
        conn: Open psycopg connection (not in autocommit mode).
        run_id: Optional ``pipeline_runs.id`` to record on each upserted row.

    Returns:
        :class:`UpsertResult` with delta counts.
    """
    feature_cols = df.columns  # columns produced by the feature pipeline
    cols = ", ".join(feature_cols)

    # Convert to CSV in memory for COPY
    csv_buffer = io.StringIO()
    df.write_csv(csv_buffer)
    csv_buffer.seek(0)
    csv_buffer.readline()  # skip header

    # Staging table — dropped on commit
    conn.execute(
        "CREATE TEMP TABLE _upsert_staging_features (LIKE provider_features) ON COMMIT DROP"
    )

    copy_sql = f"COPY _upsert_staging_features ({cols}) FROM STDIN WITH (FORMAT CSV, NULL '')"
    with conn.cursor().copy(copy_sql) as copy:
        while True:
            chunk = csv_buffer.read(65536)
            if not chunk:
                break
            copy.write(chunk)

    # Pre-count rows whose feature data is already identical (unchanged)
    # We compare only the feature columns (not metadata like last_scored_at).
    update_cols = [c for c in feature_cols if c != "npi"]
    lhs_feature = ", ".join(f"provider_features.{c}" for c in update_cols)
    rhs_feature = ", ".join(f"s.{c}" for c in update_cols)
    # Column names come from the trusted DataFrame schema, not external input — safe to interpolate.
    unchanged_row = conn.execute(
        f"SELECT COUNT(*) FROM _upsert_staging_features s "  # noqa: S608
        f"JOIN provider_features ON provider_features.npi = s.npi "
        f"WHERE ROW({lhs_feature}) IS NOT DISTINCT FROM ROW({rhs_feature})"
    ).fetchone()
    rows_unchanged = unchanged_row[0] if unchanged_row else 0

    # Always update last_scored_at and pipeline_run_id; update feature columns
    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
    set_clause += ", last_scored_at = NOW()"
    if run_id is not None:
        set_clause += f", pipeline_run_id = {run_id}"

    insert_cols = cols + ", last_scored_at" + (", pipeline_run_id" if run_id is not None else "")
    select_cols = cols + ", NOW()" + (f", {run_id}" if run_id is not None else "")

    upsert_sql = (
        f"INSERT INTO provider_features ({insert_cols}) "
        f"SELECT {select_cols} FROM _upsert_staging_features "
        f"ON CONFLICT (npi) DO UPDATE SET {set_clause} "
        f"RETURNING (xmax = 0)"
    )
    returned = conn.execute(upsert_sql).fetchall()
    rows_inserted = sum(1 for r in returned if r[0])
    rows_updated = len(returned) - rows_inserted - rows_unchanged

    conn.commit()
    return UpsertResult(
        rows_inserted=rows_inserted,
        rows_updated=rows_updated,
        rows_unchanged=rows_unchanged,
    )


def main() -> None:
    """Build and save the provider feature matrix."""
    print(f"Reading demo CSV: {DEMO_CSV}")
    df = build_provider_features()

    print(f"Feature matrix shape: {df.shape[0]} providers x {df.shape[1]} features")
    print(f"\nFeature columns ({df.shape[1]}):")
    for col in df.columns:
        print(f"  {col}: {df[col].dtype}")

    # Quick sanity stats
    print("\nSanity checks:")
    print(f"  Unique NPIs: {df['npi'].n_unique()}")
    print(f"  Revoked providers: {df.filter(pl.col('revoked_2026') == 1).shape[0]}")
    print(f"  High-risk lines > 0: {df.filter(pl.col('n_high_risk_lines') > 0).shape[0]}")
    print(f"  Mean service_hhi: {df['service_hhi'].mean()!r}")
    print("  Null counts:")
    for col in df.columns:
        null_count = df[col].null_count()
        if null_count > 0:
            print(f"    {col}: {null_count}")

    out = save_features(df)
    print(f"\nSaved to: {out}")


if __name__ == "__main__":
    main()
