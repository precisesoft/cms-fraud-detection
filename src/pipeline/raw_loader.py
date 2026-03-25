"""Raw CMS CSV loader: validate → rename columns → COPY to raw_* tables.

Reads raw CMS CSV files with vendor column names, validates that all
required columns are present, renames them to our internal schema,
bulk-loads rows into the corresponding ``raw_*`` Postgres tables, upserts
a version record in ``data_source_versions``, and archives the original
file to ``data/raw/uploads/{source_type}/{version}/``.
"""

from __future__ import annotations

import hashlib
import io
import logging
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

from src.pipeline.column_maps import COLUMN_MAPS, RAW_TABLE_NAMES, REQUIRED_COLUMNS

if TYPE_CHECKING:
    import psycopg

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_DIR = ROOT / "data" / "raw" / "uploads"

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Outcome of CSV column validation."""

    valid: bool
    missing_required: list[str] = field(default_factory=list)
    extra_columns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class LoadResult:
    """Outcome of a successful raw CSV load."""

    row_count: int
    file_hash: str
    validation_warnings: list[str]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_csv(file_path: Path, source_type: str) -> ValidationResult:
    """Validate that *file_path* contains the expected columns for *source_type*.

    Checks that every required column is present. Extra columns are allowed
    and will be ignored during loading (a warning is recorded).

    Args:
        file_path: Path to the raw CMS CSV file.
        source_type: One of ``"part_b_service"``, ``"part_b_provider"``,
            ``"enrollment"``, or ``"revocations"``.

    Returns:
        :class:`ValidationResult` with ``valid=True`` when all required columns
        are present, ``False`` otherwise.

    Raises:
        ValueError: If *source_type* is not a recognised source type.
    """
    if source_type not in COLUMN_MAPS:
        raise ValueError(f"Unknown source_type {source_type!r}. Valid types: {sorted(COLUMN_MAPS)}")

    file_columns = set(pl.read_csv(file_path, n_rows=0, infer_schema_length=0).columns)
    required = REQUIRED_COLUMNS[source_type]
    known_columns = set(COLUMN_MAPS[source_type].keys())

    missing_required = [c for c in required if c not in file_columns]
    extra_columns = sorted(file_columns - known_columns)

    warnings: list[str] = []
    if extra_columns:
        warnings.append(f"Extra columns ignored: {extra_columns}")

    return ValidationResult(
        valid=len(missing_required) == 0,
        missing_required=missing_required,
        extra_columns=extra_columns,
        warnings=warnings,
    )


def load_raw_csv(
    file_path: Path,
    source_type: str,
    version: str,
    conn: psycopg.Connection,  # type: ignore[name-defined]
    uploaded_by: str,
) -> LoadResult:
    """Load a raw CMS CSV into the corresponding ``raw_*`` Postgres table.

    Processing steps:

    1. Validate columns — raise :exc:`ValueError` on missing required columns.
    2. Read with Polars, select only mapped columns, rename to internal schema.
    3. Append ``source_version`` and ``loaded_at`` metadata columns.
    4. Delete existing rows for *version* in the target table (idempotent).
    5. Bulk-load via ``COPY … FROM STDIN``.
    6. Upsert a row in ``data_source_versions``.
    7. Archive the original file to ``data/raw/uploads/{source_type}/{version}/``.
    8. Return :class:`LoadResult`.

    Args:
        file_path: Path to the raw CMS CSV file.
        source_type: One of the four supported source types.
        version: Caller-supplied version string (e.g. ``"2023"`` or ``"q4_2025"``).
        conn: An open **psycopg** connection (not async).
        uploaded_by: Username recorded in ``data_source_versions``.

    Returns:
        :class:`LoadResult` with row count, SHA-256 file hash, and any warnings.

    Raises:
        ValueError: If *source_type* is unknown or required columns are missing.
    """
    # Step 1 — validate
    validation = validate_csv(file_path, source_type)
    if not validation.valid:
        raise ValueError(
            f"CSV {file_path} is missing required columns for {source_type!r}: "
            f"{validation.missing_required}"
        )
    for warning in validation.warnings:
        logger.warning("[%s] %s", source_type, warning)

    # Step 2 — read only the columns that exist in both the file and the map
    col_map = COLUMN_MAPS[source_type]
    file_columns = set(pl.read_csv(file_path, n_rows=0, infer_schema_length=0).columns)
    cols_to_read = [c for c in col_map if c in file_columns]

    # Force all mapped columns to String to prevent Polars from
    # inferring numeric types on mixed-format columns like HCPCS_Cd
    # (e.g. "99213" looks like i64, but "G0439" is alphanumeric).
    str_overrides = {c: pl.Utf8 for c in cols_to_read}
    df = pl.read_csv(
        file_path,
        infer_schema_length=5000,
        null_values=["", "NA", "NULL"],
        columns=cols_to_read,
        schema_overrides=str_overrides,
    )
    rename_map = {src: dst for src, dst in col_map.items() if src in df.columns}
    df = df.rename(rename_map)

    # Step 3 — add versioning metadata
    loaded_at_ts = datetime.now(tz=UTC).isoformat()
    df = df.with_columns(
        [
            pl.lit(version).alias("source_version"),
            pl.lit(loaded_at_ts).alias("loaded_at"),
        ]
    )

    # Compute file hash before any file-system operations
    file_hash = _compute_file_hash(file_path)

    # Step 4 — delete previous data for this version (idempotent reload)
    table_name = _safe_identifier(RAW_TABLE_NAMES[source_type])
    conn.execute(
        f"DELETE FROM {table_name} WHERE source_version = %s",  # noqa: S608
        [version],
    )

    # Step 5 — COPY via psycopg
    csv_buffer = io.StringIO()
    df.write_csv(csv_buffer)
    csv_buffer.seek(0)

    header_line = csv_buffer.readline()
    raw_cols = header_line.strip().split(",")
    validated_cols = [_safe_identifier(c) for c in raw_cols]
    cols = ", ".join(validated_cols)
    copy_sql = f"COPY {table_name} ({cols}) FROM STDIN WITH (FORMAT CSV, NULL '')"  # noqa: S608
    with conn.cursor().copy(copy_sql) as copy:
        while True:
            chunk = csv_buffer.read(65536)
            if not chunk:
                break
            copy.write(chunk)

    # Step 6 — upsert data_source_versions
    row_count = df.shape[0]
    conn.execute(
        """
        INSERT INTO data_source_versions
            (source_type, current_version, file_path, file_hash,
             row_count, uploaded_at, uploaded_by)
        VALUES (%s, %s, %s, %s, %s, NOW(), %s)
        ON CONFLICT (source_type) DO UPDATE SET
            current_version = EXCLUDED.current_version,
            file_path       = EXCLUDED.file_path,
            file_hash       = EXCLUDED.file_hash,
            row_count       = EXCLUDED.row_count,
            uploaded_at     = NOW(),
            uploaded_by     = EXCLUDED.uploaded_by
        """,
        [source_type, version, str(file_path), file_hash, row_count, uploaded_by],
    )
    conn.commit()

    # Step 7 — archive original file (best-effort; may fail in read-only containers)
    try:
        archive_dir = ARCHIVE_DIR / source_type / version
        archive_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, archive_dir / file_path.name)
    except OSError:
        logger.debug("Skipping file archive (directory not writable): %s", ARCHIVE_DIR)

    return LoadResult(
        row_count=row_count,
        file_hash=file_hash,
        validation_warnings=validation.warnings,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_file_hash(file_path: Path) -> str:
    """Return the SHA-256 hex digest of *file_path*."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _safe_identifier(name: str) -> str:
    """Return *name* unchanged if it is a safe SQL identifier, else raise.

    Accepts only lowercase letters, digits, and underscores — the pattern
    used by all internal schema column names and raw table names.  This
    prevents SQL injection if ``RAW_TABLE_NAMES`` or ``COLUMN_MAPS`` values
    are ever modified to contain unexpected characters.
    """
    import re

    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        raise ValueError(f"Unsafe SQL identifier: {name!r}")
    return name
