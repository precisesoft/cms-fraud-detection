"""Generate synthetic CMS data to local CSV files.

Thin CLI wrapper around :mod:`src.pipeline.synthetic`.

Usage::

    uv run python scripts/generate_synthetic_data.py
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from src.pipeline.synthetic import (
    SEED,
    SPECIALTIES,
    Archetype,
    SyntheticDataset,
    generate_all,
)

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "synthetic"


def write_csv(rows: list[dict[str, str]], path: Path) -> int:
    if not rows:
        return 0
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def print_summary(ds: SyntheticDataset, counts: dict[str, int]) -> None:
    arch_counts = Counter(p.archetype for p in ds.providers)
    n = len(ds.providers)
    n_stable = arch_counts[Archetype.STABLE]
    n_review = (
        arch_counts[Archetype.REVIEW_MILD]
        + arch_counts[Archetype.REVIEW_MID]
        + arch_counts[Archetype.NOT_ENROLLED]
    )
    n_high = arch_counts[Archetype.HIGH_RISK_Z] + arch_counts[Archetype.HIGH_RISK_REVOKED]

    print("\n=== Synthetic CMS Data Generator ===")
    print(f"Seed: {SEED}")
    print(f"\nFiles written to {OUTPUT_DIR}/:")
    print(f"  part_b_service_synthetic.csv    {counts['service']:,} rows")
    print(f"  part_b_provider_synthetic.csv   {counts['provider']:,} rows")
    print(f"  enrollment_synthetic.csv        {counts['enrollment']:,} rows")
    print(f"  revocations_synthetic.csv       {counts['revocations']:,} rows")

    print("\nProvider distribution (predicted labels):")
    print(f"  stable      {n_stable:>3} providers  ({n_stable / n * 100:.1f}%)")
    print(f"  review      {n_review:>3} providers  ({n_review / n * 100:.1f}%)")
    print(f"  high_risk   {n_high:>3} providers  ({n_high / n * 100:.1f}%)")
    print(f"    z-score only:      {arch_counts[Archetype.HIGH_RISK_Z]}")
    print(f"    revoked/unenrolled: {arch_counts[Archetype.HIGH_RISK_REVOKED]}")

    print("\nPeer group coverage:")
    for spec in SPECIALTIES:
        print(f"  {spec['type']:<45} {len(spec['codes'])} codes x {spec['count']} providers")

    print("\nUpload commands:")
    print("  POST /api/ingest/upload  source_type=part_b_service   version=synthetic_2023")
    print("  POST /api/ingest/upload  source_type=part_b_provider  version=synthetic_2023")
    print("  POST /api/ingest/upload  source_type=enrollment       version=synthetic_q4_2025")
    print("  POST /api/ingest/upload  source_type=revocations      version=synthetic_q1_2026")
    print()


def main() -> None:
    ds = generate_all()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    counts = {
        "service": write_csv(ds.service_rows, OUTPUT_DIR / "part_b_service_synthetic.csv"),
        "provider": write_csv(ds.provider_rows, OUTPUT_DIR / "part_b_provider_synthetic.csv"),
        "enrollment": write_csv(ds.enrollment_rows, OUTPUT_DIR / "enrollment_synthetic.csv"),
        "revocations": write_csv(ds.revocation_rows, OUTPUT_DIR / "revocations_synthetic.csv"),
    }
    print_summary(ds, counts)


if __name__ == "__main__":
    main()
