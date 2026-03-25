"""Load demo CSV and feature Parquet into PostgreSQL.

Reads provider_service_cases_demo.csv and provider_features.parquet,
then upserts them into the cms_fraud database using staging table + ON CONFLICT.
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[2]
DEMO_CSV = ROOT / "data" / "processed" / "demo" / "provider_service_cases_demo.csv"
FEATURES_PARQUET = ROOT / "data" / "features" / "provider_features.parquet"

# Default: forge k3s cluster via NodePort 30432
# Override with DATABASE_URL env var for local docker-compose (port 5432)
FORGE_HOST = "172.16.0.191"
DATABASE_URL = os.environ.get(
    "DATABASE_URL", f"postgresql://cms:cms_local_dev@{FORGE_HOST}:30432/cms_fraud"
)


@dataclass
class UpsertResult:
    """Delta counts returned by upsert operations."""

    rows_inserted: int
    rows_updated: int
    rows_unchanged: int

    @property
    def total(self) -> int:
        return self.rows_inserted + self.rows_updated + self.rows_unchanged


def get_connection() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL)


def load_service_cases(conn: psycopg.Connection, csv_path: Path = DEMO_CSV) -> UpsertResult:
    """Upsert service cases from CSV into provider_service_cases via staging table.

    Uses ``INSERT … ON CONFLICT (case_id) DO UPDATE`` so the operation is
    idempotent.  Returns delta counts for rows inserted, updated, and unchanged.
    """
    with open(csv_path) as f:
        header_line = f.readline().strip()
    csv_cols = header_line.split(",")
    cols = ", ".join(csv_cols)

    # Staging table — dropped automatically when the transaction commits
    conn.execute(
        "CREATE TEMP TABLE _load_staging_service_cases (LIKE provider_service_cases) ON COMMIT DROP"
    )

    copy_sql = f"COPY _load_staging_service_cases ({cols}) FROM STDIN WITH (FORMAT CSV)"
    with open(csv_path) as f:
        f.readline()  # skip header
        with conn.cursor().copy(copy_sql) as copy:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                copy.write(chunk)

    row = conn.execute("SELECT COUNT(*) FROM _load_staging_service_cases").fetchone()
    total_staging = row[0] if row else 0

    # Build the SET and IS-DISTINCT-FROM clauses dynamically
    update_cols = [c for c in csv_cols if c != "case_id"]
    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
    lhs = ", ".join(f"provider_service_cases.{c}" for c in update_cols)
    rhs = ", ".join(f"EXCLUDED.{c}" for c in update_cols)

    upsert_sql = (
        f"INSERT INTO provider_service_cases ({cols}) "
        f"SELECT {cols} FROM _load_staging_service_cases "
        f"ON CONFLICT (case_id) DO UPDATE SET {set_clause} "
        f"WHERE ROW({lhs}) IS DISTINCT FROM ROW({rhs}) "
        f"RETURNING (xmax = 0)"
    )
    returned = conn.execute(upsert_sql).fetchall()
    rows_inserted = sum(1 for r in returned if r[0])
    rows_updated = len(returned) - rows_inserted
    rows_unchanged = total_staging - len(returned)

    conn.commit()
    return UpsertResult(
        rows_inserted=rows_inserted,
        rows_updated=rows_updated,
        rows_unchanged=rows_unchanged,
    )


def load_features(conn: psycopg.Connection, parquet_path: Path = FEATURES_PARQUET) -> UpsertResult:
    """Upsert provider features from Parquet into provider_features via staging table.

    Uses ``INSERT … ON CONFLICT (npi) DO UPDATE`` so the operation is idempotent.
    Only the columns present in the Parquet file are updated; metadata columns
    (``last_scored_at``, ``pipeline_run_id``) are left untouched by this function.
    Returns delta counts for rows inserted, updated, and unchanged.
    """
    import polars as pl

    df = pl.read_parquet(parquet_path)
    csv_cols = df.columns
    cols = ", ".join(csv_cols)

    # Convert to CSV in memory for COPY
    csv_buffer = io.StringIO()
    df.write_csv(csv_buffer)
    csv_buffer.seek(0)
    csv_buffer.readline()  # skip header

    # Staging table — dropped automatically when the transaction commits
    conn.execute("CREATE TEMP TABLE _load_staging_features (LIKE provider_features) ON COMMIT DROP")

    copy_sql = f"COPY _load_staging_features ({cols}) FROM STDIN WITH (FORMAT CSV, NULL '')"
    with conn.cursor().copy(copy_sql) as copy:
        while True:
            chunk = csv_buffer.read(65536)
            if not chunk:
                break
            copy.write(chunk)

    row = conn.execute("SELECT COUNT(*) FROM _load_staging_features").fetchone()
    total_staging = row[0] if row else 0

    # Build the SET and IS-DISTINCT-FROM clauses for the columns we're loading
    update_cols = [c for c in csv_cols if c != "npi"]
    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
    lhs = ", ".join(f"provider_features.{c}" for c in update_cols)
    rhs = ", ".join(f"EXCLUDED.{c}" for c in update_cols)

    upsert_sql = (
        f"INSERT INTO provider_features ({cols}) "
        f"SELECT {cols} FROM _load_staging_features "
        f"ON CONFLICT (npi) DO UPDATE SET {set_clause} "
        f"WHERE ROW({lhs}) IS DISTINCT FROM ROW({rhs}) "
        f"RETURNING (xmax = 0)"
    )
    returned = conn.execute(upsert_sql).fetchall()
    rows_inserted = sum(1 for r in returned if r[0])
    rows_updated = len(returned) - rows_inserted
    rows_unchanged = total_staging - len(returned)

    conn.commit()
    return UpsertResult(
        rows_inserted=rows_inserted,
        rows_updated=rows_updated,
        rows_unchanged=rows_unchanged,
    )


def main() -> None:
    print(f"Connecting to: {DATABASE_URL}")
    conn = get_connection()

    if DEMO_CSV.exists():
        print(f"Loading service cases from {DEMO_CSV}...")
        result = load_service_cases(conn, DEMO_CSV)
        print(
            f"  inserted={result.rows_inserted:,} updated={result.rows_updated:,} unchanged={result.rows_unchanged:,}"
        )
    else:
        print(f"  SKIP: {DEMO_CSV} not found")

    if FEATURES_PARQUET.exists():
        print(f"Loading features from {FEATURES_PARQUET}...")
        result = load_features(conn, FEATURES_PARQUET)
        print(
            f"  inserted={result.rows_inserted:,} updated={result.rows_updated:,} unchanged={result.rows_unchanged:,}"
        )
    else:
        print(f"  SKIP: {FEATURES_PARQUET} not found (run build_features first)")

    # Quick validation
    print("\nValidation:")
    for table in ["provider_service_cases", "provider_features"]:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        count = row[0] if row else 0
        print(f"  {table}: {count:,} rows")

    row = conn.execute("SELECT COUNT(*) FROM provider_features").fetchone()
    if row and row[0] > 0:
        top5 = conn.execute("""
            SELECT npi, provider_name, provider_type, state,
                   max_seed_risk_score, risk_legitimacy_gap
            FROM provider_features
            ORDER BY max_seed_risk_score DESC
            LIMIT 5
        """).fetchall()
        print("\nTop 5 highest risk providers:")
        for row in top5:
            print(
                f"  NPI {row[0]} | {row[1]:<30} | {row[2]:<25} | {row[3]} | risk={row[4]} gap={row[5]}"
            )

    conn.close()


if __name__ == "__main__":
    main()
