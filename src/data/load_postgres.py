"""Load demo CSV and feature Parquet into PostgreSQL.

Reads provider_service_cases_demo.csv and provider_features.parquet,
then bulk-loads them into the cms_fraud database using COPY.
"""

from __future__ import annotations

import io
import os
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


def get_connection() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL)


def load_service_cases(conn: psycopg.Connection, csv_path: Path = DEMO_CSV) -> int:
    """Bulk-load the demo service cases CSV into provider_service_cases."""
    conn.execute("TRUNCATE provider_service_cases")

    with open(csv_path) as f:
        header_line = f.readline().strip()
        cols = ", ".join(header_line.split(","))
        copy_sql = f"COPY provider_service_cases ({cols}) FROM STDIN WITH (FORMAT CSV)"

        with conn.cursor().copy(copy_sql) as copy:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                copy.write(chunk)

    conn.commit()
    row = conn.execute("SELECT COUNT(*) FROM provider_service_cases").fetchone()
    return row[0] if row else 0


def load_features(conn: psycopg.Connection, parquet_path: Path = FEATURES_PARQUET) -> int:
    """Load the feature Parquet into provider_features via CSV intermediary."""
    import polars as pl

    conn.execute("TRUNCATE provider_features")

    df = pl.read_parquet(parquet_path)

    # Convert to CSV in memory for COPY
    csv_buffer = io.StringIO()
    df.write_csv(csv_buffer)
    csv_buffer.seek(0)

    header_line = csv_buffer.readline()  # skip header
    cols = ", ".join(header_line.strip().split(","))

    copy_sql = f"COPY provider_features ({cols}) FROM STDIN WITH (FORMAT CSV, NULL '')"
    with conn.cursor().copy(copy_sql) as copy:
        while True:
            chunk = csv_buffer.read(65536)
            if not chunk:
                break
            copy.write(chunk)

    conn.commit()
    row = conn.execute("SELECT COUNT(*) FROM provider_features").fetchone()
    return row[0] if row else 0


def main() -> None:
    print(f"Connecting to: {DATABASE_URL}")
    conn = get_connection()

    if DEMO_CSV.exists():
        print(f"Loading service cases from {DEMO_CSV}...")
        n = load_service_cases(conn, DEMO_CSV)
        print(f"  Loaded {n:,} service case rows")
    else:
        print(f"  SKIP: {DEMO_CSV} not found")

    if FEATURES_PARQUET.exists():
        print(f"Loading features from {FEATURES_PARQUET}...")
        n = load_features(conn, FEATURES_PARQUET)
        print(f"  Loaded {n:,} provider feature rows")
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
