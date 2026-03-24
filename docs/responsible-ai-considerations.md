# Responsible AI Considerations

## Overview

The CMS Fraud Detection system is designed to assist human investigators — not replace them. Every design decision prioritizes explainability, fairness, and accountability over raw predictive power.

## 1. Dual Scoring: Risk and Legitimacy

Traditional fraud detection systems produce a single risk score. This creates a one-dimensional view that ignores evidence of legitimate practice.

Our system computes **two independent scores** for every provider-service case:

- **Risk Score**: Quantifies how anomalous the billing pattern is relative to peers
- **Legitimacy Score**: Quantifies how many trust-building indicators the provider exhibits

A provider with high volume (risk signal) who is enrolled, participating in Medicare, and within normal range on all other metrics (legitimacy signals) will show a high legitimacy score that contextualizes the risk. The case label rules require risk to exceed legitimacy by at least 5 points before a `high_risk` label is assigned.

This dual-score design reduces false positives and ensures providers aren't flagged solely on a single anomalous metric.

## 2. Fairness Monitoring

### Built-In Fairness Endpoint

The system includes a dedicated `/api/fairness` endpoint that computes flagging rate disparities across two protected dimensions:

- **Geography** (state): Ensures no state's providers are disproportionately flagged
- **Specialty** (provider_type): Ensures no medical specialty is disproportionately flagged

### Metrics Computed

| Metric                            | Definition                                         | Ideal Value          |
| --------------------------------- | -------------------------------------------------- | -------------------- |
| **Overall Flagging Rate**         | Fraction of providers with risk score >= threshold | N/A (descriptive)    |
| **Statistical Parity Difference** | max(cohort rate) - min(cohort rate)                | 0.0 (perfect parity) |
| **Disparate Impact Ratio**        | min(cohort rate) / max(cohort rate)                | 1.0 (perfect parity) |
| **Outlier Detection**             | Cohort rate > 2 standard deviations above mean     | Flags systemic bias  |

### Four-Fifths Rule

The disparate impact ratio maps directly to the EEOC's four-fifths (80%) rule used in employment discrimination analysis. A ratio below 0.80 warrants investigation into whether the scoring methodology introduces unintended bias against certain specialties or regions.

### Configurable Threshold

The fairness endpoint accepts a `threshold` parameter (default: 51), allowing analysts to evaluate fairness at different risk cutoffs without code changes.

## 3. Explainability

### Signal-Level Transparency

Every score decomposes into specific, named signals. A reviewer can see exactly which signals fired, what values triggered them, and how many points each contributed.

Example output for a flagged provider:

```
Risk Score: 67
  - revoked_provider:           25 pts  (appears in 2026 revocation file)
  - service_volume_outlier:     20 pts  (z = 5.3, tier 1: z >= 5.0)
  - service_intensity_outlier:  14 pts  (z = 3.8, tier 2: z >= 3.0)
  - charge_ratio_outlier:        8 pts  (z = 2.4, tier 3: z >= 2.0)

Legitimacy Score: 8
  - large_patient_panel:         8 pts  (serves 150 beneficiaries)
```

No score is a mystery — every point has a name, a source, and a reason.

### Peer Comparison Context

For peer-based signals, the system shows:

- The peer group scope (same specialty + HCPCS code)
- The peer group size (minimum 25 required)
- The peer average and the provider's observed value
- The z-score that quantifies the deviation

This allows reviewers to judge whether the peer comparison is meaningful for the specific case.

## 4. Human-in-the-Loop Design

### The System Does Not Make Decisions

The system produces scores, signals, and evidence packages. It does **not**:

- Automatically flag providers for enforcement action
- Generate formal accusations or referrals
- Remove providers from the Medicare program
- Deny or approve claims

All outputs are decision-support artifacts for trained investigators who apply domain expertise and additional context.

### Three-Tier Case Labels

Cases are labeled `high_risk`, `review`, or `stable` — not "fraudulent" or "legitimate." The language reflects that these are risk indicators requiring human evaluation, not conclusions.

### Investigator Workflow

1. Analysts review the provider list sorted by risk score
2. For flagged providers, they examine fired signals and peer comparisons
3. They assess whether the anomalies have legitimate explanations (e.g., specialty clinics naturally have higher volume for certain codes)
4. Only after human review does a case proceed to further investigation

## 5. Data Provenance and Transparency

### Public Data Only

All scoring inputs come from publicly available CMS datasets:

- **Medicare Fee-for-Service Public Provider Enrollment** (2025): Enrollment verification
- **CMS Provider Revocation File** (2026): Revocation status
- **Medicare Physician & Other Practitioners** (2022): Service volume, charges, payments

No proprietary data, patient records, or protected health information is used.

### No Demographic Data

The scoring engine does **not** use any demographic variables — no race, ethnicity, gender, age, or socioeconomic indicators. Scores are based entirely on:

- Enrollment/revocation status (administrative records)
- Billing volume compared to specialty-specific peers (statistical comparison)
- Charge ratios compared to peers (statistical comparison)

### Reproducibility

The scoring engine is deterministic: the same input always produces the same output. There is no randomness, no model re-training, and no stochastic inference. This means:

- Results can be independently verified
- Auditors can reproduce any score by running the same data through the same code
- Scoring behavior is predictable and testable

## 6. Limitations and Known Constraints

### What This System Cannot Detect

- **Collusion between providers**: Requires network analysis beyond peer comparison
- **Phantom patients**: Requires beneficiary-level validation not in the current dataset
- **Upcoding within normal ranges**: Providers billing at the high end of normal will not trigger z-score signals
- **New fraud schemes**: A rule-based system detects known anomaly patterns, not novel ones

### Peer Group Limitations

- Peer groups with fewer than 25 members are suppressed to avoid unreliable comparisons
- National specialties with few practitioners may have skewed baselines
- The 2022 billing data may not reflect current practice patterns

### Score Ceiling Effects

- The maximum legitimacy score (89) is lower than the theoretical risk maximum (100), which slightly favors risk in extreme cases
- This is an intentional design choice: a provider exhibiting extreme anomalies across all metrics should not be fully offset by standard legitimacy indicators

## 7. Temporal Analysis — Current Limitations

### Single-Year Cross-Sectional Data

The current system scores providers using **CMS Medicare Part B data from a single year (2022)**. This data is annual aggregated — there are no claim-level timestamps, no quarterly breakdowns, and no multi-year history.

This means the system **cannot currently detect**:

- **Abnormal billing growth** (e.g., a provider whose volume doubled year-over-year)
- **Seasonal anomalies** (e.g., unusually high billing in specific months)
- **Trending behavior** (e.g., a provider gradually shifting toward higher-cost codes)

The CMS challenge brief explicitly identifies "abnormal growth" and "time-series trends" as detection targets. We acknowledge this gap transparently.

### How the System Compensates

The current scoring engine uses **cross-sectional peer comparison** as a proxy for temporal analysis:

- A provider billing 5x the specialty peer average is statistically anomalous regardless of whether the volume grew gradually or appeared suddenly
- Z-score outlier detection identifies the same extreme providers that year-over-year growth analysis would flag
- Peer baselines represent normal practice patterns — providers far outside these norms warrant review

This approach catches the **outcome** of abnormal growth (the resulting anomalous volume) even without capturing the **trajectory**.

### Path to Full Temporal Analysis

With multi-year CMS Part B data (2020-2024), the system would add:

| Signal                  | Description                                                 | Data Required   |
| ----------------------- | ----------------------------------------------------------- | --------------- |
| `year_over_year_growth` | Services or charges grew > 2σ from prior year               | 2+ years Part B |
| `billing_acceleration`  | Growth rate itself is increasing                            | 3+ years Part B |
| `code_mix_shift`        | Provider's HCPCS code distribution changed significantly    | 2+ years Part B |
| `new_high_cost_codes`   | Provider began billing high-cost codes not in prior history | 2+ years Part B |

These signals integrate directly into the existing taxonomy — same tier-based scoring, same dual risk/legitimacy framework. Connecting multi-year data is a pilot phase enhancement (see [Path to CMS Pilot](./path-to-cms-pilot.md)).

## 8. AI Disclosure

### Scoring Remains Rule-Based

Risk and legitimacy scores are computed entirely by **deterministic, rule-based logic** — no machine learning models, no neural networks, no gradient-boosted trees. The same input always produces the same score. Scores are auditable, reproducible, and independent of any AI service.

Generative AI does **not**:

- Compute risk or legitimacy scores
- Assign case labels (`high_risk`, `review`, `stable`)
- Trigger or recommend enforcement actions
- Modify any data in the database

### Where Generative AI Is Used

AWS Bedrock Claude is live in three endpoints, each serving an **advisory and investigation-support** role only:

| Endpoint                    | Model                                                            | Purpose                                                                             |
| --------------------------- | ---------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `POST /api/chat`            | Claude Haiku 4.5 (`us.anthropic.claude-haiku-4-5-20251001-v1:0`) | Translates analyst natural-language questions into SQL and returns query results    |
| `POST /api/score`           | Claude Sonnet 4.6 (`us.anthropic.claude-sonnet-4-6`)             | Generates a plain-language narrative summarizing the scored provider's risk signals |
| `POST /api/claims/simulate` | Claude Sonnet 4.6 (`us.anthropic.claude-sonnet-4-6`)             | Generates a plain-language narrative for a simulated claims scenario                |

All AI-generated text is surfaced in the UI and clearly presented as supplementary context for human reviewers.

Model IDs are configurable via the `BEDROCK_CHAT_MODEL` and `BEDROCK_NARRATIVE_MODEL` environment variables.

### Safeguards for AI-Generated SQL

The text-to-SQL pipeline includes multiple layers of defense to prevent data exfiltration or unintended database mutations:

| Safeguard                        | Detail                                                                                                                                                                                                                 |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Read-only database user**      | The `/api/chat` endpoint connects through a dedicated read-only PostgreSQL user (`get_readonly_db` dependency); the DB user cannot execute DML or DDL regardless of the SQL generated                                  |
| **Regex keyword blocklist**      | Generated SQL is scanned for `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `GRANT`, `REVOKE`, `UNION`, `COPY`, `pg_sleep`, `dblink`, privilege-escalation patterns, and others before execution |
| **SQL comment rejection**        | `--` and `/* */` comment syntax is blocked to prevent keyword obfuscation                                                                                                                                              |
| **SELECT/WITH-only enforcement** | Any query that does not start with `SELECT` or `WITH` is rejected                                                                                                                                                      |
| **LIMIT 500 enforcement**        | A `LIMIT 500` clause is automatically appended if absent, capping data returned per query                                                                                                                              |
| **5-second statement timeout**   | `SET statement_timeout = 5000` is applied to every AI-generated query; long-running queries are cancelled                                                                                                              |
| **Conversation history cap**     | At most the last 3 turns (6 messages) of conversation history are sent to the model, limiting context accumulation                                                                                                     |

### Human-in-the-Loop

AI narratives are **advisory only**. They surface a plain-language summary of the data already visible in the scoring UI; they do not introduce new facts or conclusions.

The investigator workflow remains unchanged:

1. Analysts review provider risk scores and fired signals
2. AI narratives provide a readable summary to accelerate review — not to replace judgement
3. Analysts decide whether anomalies have legitimate explanations
4. Only a human decision advances a case to further investigation or enforcement

No automated action is taken based on AI output.

See also [AI & Open-Source Disclosure](./ai-oss-disclosure.md) for the full inventory of AI tools and open-source libraries used in this system.

## 9. Continuous Improvement

### Monitoring Plan

- Track fairness metrics at each scoring run via the `/api/fairness` endpoint
- Alert if any cohort's flagging rate exceeds 2 standard deviations from the mean
- Review disparate impact ratios quarterly

### Feedback Loop

- Investigators can provide feedback on flagged cases (true positive, false positive)
- This feedback informs threshold tuning and signal weight adjustments
- All changes to scoring logic are versioned in code and documented

### Audit Trail

- All scoring parameters (thresholds, weights, tier boundaries) are defined in `src/scoring/taxonomy.py`
- Changes to scoring logic go through code review and CI checks
- Historical scores are preserved in the database for comparison
