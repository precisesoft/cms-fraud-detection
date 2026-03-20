"""Retrospective validation — prove behavioral scoring catches revoked providers.

Scores all revoked providers WITHOUT the revocation flag to demonstrate that
billing-pattern signals alone would have flagged them before CMS acted.

Usage:
    python -m src.validation.retrospective
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import polars as pl

from src.scoring.score import score_case

ROOT = Path(__file__).resolve().parents[2]
DEMO_CSV = ROOT / "data" / "processed" / "demo" / "provider_service_cases_demo.csv"
OUTPUT_DIR = ROOT / "data" / "validation"


def load_cases(path: Path = DEMO_CSV) -> pl.DataFrame:
    return pl.read_csv(path, infer_schema_length=5000, null_values=["", "NA", "NULL"])


def blind_score_row(row: dict) -> dict:
    """Score a case row as if the provider was NOT revoked."""
    blind = dict(row)
    blind["present_in_2026_revocation_file"] = 0
    card = score_case(blind)
    return {
        "blind_risk": card.risk_score,
        "blind_legitimacy": card.legitimacy_score,
        "blind_label": card.case_label.value,
    }


def original_score_row(row: dict) -> dict:
    """Score a case row with original data (revocation flag intact)."""
    card = score_case(row)
    return {
        "original_risk": card.risk_score,
        "original_legitimacy": card.legitimacy_score,
        "original_label": card.case_label.value,
    }


def run_validation(csv_path: Path = DEMO_CSV) -> dict:
    """Run full retrospective validation and return results dict."""
    df = load_cases(csv_path)

    revoked = df.filter(pl.col("present_in_2026_revocation_file") == 1)
    non_revoked = df.filter(pl.col("present_in_2026_revocation_file") == 0)

    revoked_rows = revoked.to_dicts()
    non_revoked_rows = non_revoked.to_dicts()

    # --- Score revoked providers blind (without revocation flag) ---
    blind_results = []
    for row in revoked_rows:
        blind = blind_score_row(row)
        original = original_score_row(row)
        blind_results.append(
            {
                "npi": row["npi"],
                "hcpcs_cd": row.get("hcpcs_cd"),
                "revocation_reason": row.get("revocation_reason_summary", ""),
                **original,
                **blind,
            }
        )

    # --- Score non-revoked providers (baseline) ---
    non_revoked_labels: Counter[str] = Counter()
    for row in non_revoked_rows:
        card = score_case(row)
        non_revoked_labels[card.case_label.value] += 1

    # --- Aggregate blind results ---
    blind_labels = Counter(r["blind_label"] for r in blind_results)
    original_labels = Counter(r["original_label"] for r in blind_results)

    # Case-level detection rates
    total_cases = len(blind_results)
    detected_high = blind_labels.get("high_risk", 0)
    detected_review = blind_labels.get("review", 0)
    detection_rate = (detected_high + detected_review) / total_cases if total_cases else 0

    # Provider-level: aggregate to worst case per NPI
    npi_worst_blind: dict[str, str] = {}
    for r in blind_results:
        npi = r["npi"]
        label = r["blind_label"]
        priority = {"high_risk": 2, "review": 1, "stable": 0}
        if npi not in npi_worst_blind or priority[label] > priority[npi_worst_blind[npi]]:
            npi_worst_blind[npi] = label

    npi_labels = Counter(npi_worst_blind.values())
    total_npis = len(npi_worst_blind)
    npi_detection = (
        (npi_labels.get("high_risk", 0) + npi_labels.get("review", 0)) / total_npis
        if total_npis
        else 0
    )

    # --- Stratify by revocation reason ---
    reason_stats: dict[str, dict] = {}
    for r in blind_results:
        reason = (r.get("revocation_reason") or "unknown")[:80]
        if reason not in reason_stats:
            reason_stats[reason] = {"total": 0, "high_risk": 0, "review": 0, "stable": 0}
        reason_stats[reason]["total"] += 1
        reason_stats[reason][r["blind_label"]] += 1

    for reason, stats in reason_stats.items():
        total = stats["total"]
        stats["detection_rate"] = (stats["high_risk"] + stats["review"]) / total if total else 0

    # --- Blind risk score distribution ---
    blind_risk_scores = [r["blind_risk"] for r in blind_results]
    avg_blind_risk = sum(blind_risk_scores) / len(blind_risk_scores) if blind_risk_scores else 0

    # Non-revoked baseline risk (for comparison)
    non_revoked_risk = []
    for row in non_revoked_rows[:2000]:  # sample for speed
        card = score_case(row)
        non_revoked_risk.append(card.risk_score)
    avg_non_revoked_risk = sum(non_revoked_risk) / len(non_revoked_risk) if non_revoked_risk else 0

    results = {
        "summary": {
            "total_revoked_cases": total_cases,
            "total_revoked_npis": total_npis,
            "case_detection_rate": round(detection_rate, 4),
            "npi_detection_rate": round(npi_detection, 4),
            "avg_blind_risk_score_revoked": round(avg_blind_risk, 1),
            "avg_risk_score_non_revoked": round(avg_non_revoked_risk, 1),
            "risk_score_lift": round(avg_blind_risk - avg_non_revoked_risk, 1),
        },
        "case_level": {
            "original_labels": dict(original_labels),
            "blind_labels": dict(blind_labels),
        },
        "provider_level": {
            "blind_labels": dict(npi_labels),
        },
        "non_revoked_baseline": dict(non_revoked_labels),
        "by_revocation_reason": {
            reason: stats
            for reason, stats in sorted(
                reason_stats.items(), key=lambda x: x[1]["total"], reverse=True
            )[:15]
        },
    }

    return results


def main() -> None:
    print("Running retrospective validation...")
    print(f"Data source: {DEMO_CSV}\n")

    results = run_validation()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "retrospective_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {output_path}\n")

    s = results["summary"]
    print("=" * 60)
    print("RETROSPECTIVE VALIDATION RESULTS")
    print("=" * 60)
    print("\nRevoked providers scored WITHOUT revocation flag:")
    print(f"  Cases:     {s['total_revoked_cases']}")
    print(f"  Providers: {s['total_revoked_npis']}")
    print()
    print(f"CASE-LEVEL DETECTION RATE:     {s['case_detection_rate']:.1%}")
    print(f"PROVIDER-LEVEL DETECTION RATE: {s['npi_detection_rate']:.1%}")
    print()
    print(f"Avg blind risk score (revoked):     {s['avg_blind_risk_score_revoked']}")
    print(f"Avg risk score (non-revoked):        {s['avg_risk_score_non_revoked']}")
    print(f"Risk score lift:                     +{s['risk_score_lift']}")
    print()

    print("Case labels (blind scoring):")
    for label, count in sorted(results["case_level"]["blind_labels"].items()):
        pct = count / s["total_revoked_cases"]
        print(f"  {label:12s}: {count:>5d} ({pct:.1%})")

    print("\nProvider labels (worst case per NPI, blind):")
    for label, count in sorted(results["provider_level"]["blind_labels"].items()):
        pct = count / s["total_revoked_npis"]
        print(f"  {label:12s}: {count:>5d} ({pct:.1%})")

    print("\nNon-revoked baseline:")
    for label, count in sorted(results["non_revoked_baseline"].items()):
        total = sum(results["non_revoked_baseline"].values())
        pct = count / total
        print(f"  {label:12s}: {count:>5d} ({pct:.1%})")

    print("\nTop revocation reasons (blind detection rates):")
    for reason, stats in results["by_revocation_reason"].items():
        rate = stats["detection_rate"]
        print(f"  {rate:.0%} ({stats['total']:>3d} cases) — {reason[:65]}")


if __name__ == "__main__":
    main()
