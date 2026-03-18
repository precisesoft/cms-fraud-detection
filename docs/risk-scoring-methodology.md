# Risk Scoring Methodology

## Overview

The CMS Fraud Detection system uses a deterministic, explainable scoring engine to evaluate Medicare provider-service cases. Every score is traceable to specific signals, thresholds, and data sources — there are no black-box models.

Each provider-service case (one provider + one HCPCS code) receives two independent scores:

- **Risk Score** (0-100): How anomalous the billing pattern is compared to peers
- **Legitimacy Score** (0-100): How many trust-building indicators the provider exhibits

The dual-score design prevents false positives: a high risk score alone does not trigger a flag if legitimacy evidence is strong.

## Architecture

The scoring engine is a pure-function, three-layer stack:

```
taxonomy.py   →  Signal definitions, thresholds, point allocations
extract.py    →  Maps a case row to fired signals with points
score.py      →  Sums fired signals into scores and assigns a case label
```

All logic is database-free and fully unit-testable.

## Signal Taxonomy

### Risk Signals (6 signals)

| Signal                           | Category   | Trigger                                               | Points      |
| -------------------------------- | ---------- | ----------------------------------------------------- | ----------- |
| `revoked_provider`               | enrollment | Provider appears in 2026 CMS revocation file          | 25          |
| `not_in_current_enrollment_file` | enrollment | Provider absent from 2025 CMS enrollment file         | 8           |
| `service_volume_outlier`         | peer       | Total services z-score vs. peers (tiered)             | 8 / 14 / 20 |
| `service_intensity_outlier`      | peer       | Services-per-beneficiary z-score vs. peers (tiered)   | 7 / 12 / 18 |
| `charge_ratio_outlier`           | peer       | Submitted-to-allowed ratio z-score vs. peers (tiered) | 7 / 12 / 18 |
| `payment_outlier`                | peer       | Average payment z-score vs. peers (tiered)            | 5 / 8 / 12  |

### Legitimacy Signals (7 signals)

| Signal                               | Category   | Trigger                                                   | Points |
| ------------------------------------ | ---------- | --------------------------------------------------------- | ------ |
| `present_in_current_enrollment_file` | enrollment | Provider found in 2025 enrollment file                    | 20     |
| `no_revocation_match`                | enrollment | Provider has no revocation on record                      | 15     |
| `medicare_participating`             | enrollment | Provider accepts Medicare assignment                      | 10     |
| `peer_aligned_volume`                | peer       | Service volume within 1 std. dev. of peers (\|z\| < 1.0)  | 12     |
| `peer_aligned_intensity`             | peer       | Services per beneficiary within 1 std. dev. (\|z\| < 1.0) | 12     |
| `peer_aligned_pricing`               | peer       | Charge ratio within 1 std. dev. (\|z\| < 1.0)             | 12     |
| `large_patient_panel`                | volume     | Provider serves 100+ Medicare beneficiaries               | 8      |

## Z-Score Tier System

Peer-comparison risk signals use a graduated tier system rather than a binary threshold. This rewards proportional response — a provider 5 standard deviations above peers is scored more heavily than one at 2.

| Tier              | Z-Score  | Volume Points | Intensity Points | Charge Points | Payment Points |
| ----------------- | -------- | ------------- | ---------------- | ------------- | -------------- |
| Tier 1 (extreme)  | z >= 5.0 | 20            | 18               | 18            | 12             |
| Tier 2 (high)     | z >= 3.0 | 14            | 12               | 12            | 8              |
| Tier 3 (elevated) | z >= 2.0 | 8             | 7                | 7             | 5              |
| Below threshold   | z < 2.0  | 0             | 0                | 0             | 0              |

## Peer Baseline Construction

Z-scores are computed against peer groups defined by **provider specialty (provider_type) and HCPCS code**. A peer group must have at least **25 providers** (`MIN_PEER_COUNT`) to produce statistically meaningful comparisons.

Peer baselines are pre-computed in the `provider_service_cases` table:

- `peer_avg_tot_srvcs` — mean total services across peers
- `service_volume_peer_z` — (provider's total services - peer mean) / peer std dev
- `services_per_bene_peer_z` — same formula for services per beneficiary
- `submitted_to_allowed_peer_z` — same for charge ratio
- `payment_peer_z` — same for average Medicare payment

If the peer group has fewer than 25 members, all peer-based signals are suppressed for that case.

## Score Computation

```
risk_score      = min(sum(risk signal points), 100)
legitimacy_score = min(sum(legitimacy signal points), 100)
```

### Theoretical Maximums

- **Max risk score**: 101 points possible (capped at 100)
  - Revoked (25) + Not enrolled (8) + Volume tier 1 (20) + Intensity tier 1 (18) + Charge tier 1 (18) + Payment tier 1 (12)
- **Max legitimacy score**: 89 points possible
  - Enrolled (20) + No revocation (15) + Participating (10) + Volume aligned (12) + Intensity aligned (12) + Pricing aligned (12) + Large panel (8)

## Case Labeling

After scoring, each case receives a label based on decision rules:

| Label       | Criteria                                                |
| ----------- | ------------------------------------------------------- |
| `high_risk` | risk_score >= 50 AND risk_score >= legitimacy_score + 5 |
| `stable`    | legitimacy_score >= 70 AND risk_score < 30              |
| `review`    | All other cases                                         |

The gap requirement (`risk >= legitimacy + 5`) prevents flagging when a provider has strong legitimacy evidence counterbalancing moderate risk signals.

## Provider-Level Risk Bands

For the provider list view, the maximum `seed_risk_score` across all service lines determines the provider's display band:

| Band        | Score Range |
| ----------- | ----------- |
| `high_risk` | 51-100      |
| `review`    | 31-50       |
| `stable`    | 0-30        |

## Data Provenance

Every signal traces directly to a CMS public dataset:

| Data Source                       | Signal Category | CMS Dataset                                                |
| --------------------------------- | --------------- | ---------------------------------------------------------- |
| Enrollment status                 | enrollment      | Medicare Fee-for-Service Public Provider Enrollment (2025) |
| Revocation status                 | enrollment      | CMS Revocation File (2026)                                 |
| Service volume, charges, payments | peer            | Medicare Physician & Other Practitioners (2022)            |
| Beneficiary counts                | volume          | Same as above                                              |

All datasets are publicly available from [data.cms.gov](https://data.cms.gov).

## Explainability

Every scored case carries:

- The complete list of fired signals with their point contributions
- Human-readable reason strings for each signal
- The observed value (e.g., z-score of 4.2) and the threshold that triggered it
- The peer baseline value for context

This enables reviewers to understand exactly why a provider was flagged and trace every point back to a specific data source and comparison methodology.
