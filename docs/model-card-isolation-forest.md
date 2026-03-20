# Model Card: Isolation Forest Anomaly Detection

> Model card for the unsupervised anomaly detection component used in provider risk scoring.

## Model Overview

| Field | Value |
|---|---|
| **Model Type** | Isolation Forest (unsupervised anomaly detection) |
| **Implementation** | scikit-learn `IsolationForest` |
| **Version** | scikit-learn 1.x |
| **Purpose** | Supplementary anomaly signal for provider-level billing pattern detection |
| **Role in System** | One signal among 14 in the deterministic scoring taxonomy |

## Intended Use

The Isolation Forest model generates a binary anomaly flag (`isolation_forest_flag`) for each provider. This flag contributes **up to 10 points** to a provider's risk score as part of the broader signal taxonomy.

**Intended users:** CMS program integrity investigators and fraud analysts using the Argus dashboard.

**Intended use cases:**
- Surfacing providers with statistically unusual billing patterns for human review
- Supplementing rule-based signals with a data-driven anomaly perspective
- Prioritizing investigator workload by flagging high-probability anomalies

**Out-of-scope uses:**
- Autonomous enforcement or payment denial decisions
- Final determination of fraud without human review
- Use on data domains outside Medicare Part B provider billing patterns

## Training Data

| Field | Value |
|---|---|
| **Dataset** | Medicare Physician & Other Practitioners — by Provider and Service (2022) |
| **Source** | CMS data.cms.gov (public domain) |
| **Size** | ~9.66M service lines, ~13K provider-service cases after filtering |
| **Features** | Provider-level aggregated billing metrics (charges, payments, service volumes) |
| **Labels** | None — unsupervised model |
| **PHI** | None — all data is publicly available aggregate statistics |

### Input Features

The model trains on a subset of normalized provider-level features:

| Feature | Description |
|---|---|
| `avg_submitted_charge_per_service` | Average charge submitted per service |
| `avg_medicare_payment` | Average Medicare allowed payment |
| `service_volume` | Total services billed |
| `beneficiary_count` | Distinct beneficiaries served |
| `charge_to_payment_ratio` | Ratio of submitted charges to Medicare payment |

Features are standardized (z-score normalized) before training.

## Model Architecture

- **Algorithm:** Isolation Forest
- **Contamination:** 0.05 (5% of providers expected to be anomalous)
- **n_estimators:** 100 isolation trees
- **random_state:** 42 (reproducible results)
- **Scoring:** Binary flag — providers in the most anomalous 5% receive `isolation_forest_flag = 1`

## Evaluation

### Retrospective Validation

The scoring system (including the Isolation Forest signal) was retrospectively validated against CMS provider revocation data:

- **Detection rate:** The full scoring system detected **91% of eventually-revoked providers** from billing patterns alone
- The Isolation Forest flag contributes to this result as one of 14 signals

### Limitations of Evaluation

- Revocation is an imperfect ground truth: not all revoked providers were revoked for billing fraud
- The model was trained and evaluated on 2022 data; performance on future years may differ
- No prospective validation has been performed

## Fairness Considerations

The model does not use protected attributes (race, gender, ethnicity) as features. However, indirect proxies may exist:

- **Geography:** Specialty distribution varies by state; geographic anomalies may correlate with regional practice norms
- **Specialty:** Different specialties have different billing patterns; per-specialty peer comparison mitigates but does not eliminate this

The system includes a dedicated **`/api/fairness` endpoint** that monitors flagging rate disparities across geography and specialty, using statistical parity and disparate impact metrics.

See [docs/responsible-ai-considerations.md](responsible-ai-considerations.md) for the full fairness framework.

## Transparency and Explainability

The Isolation Forest model produces a **binary flag**, not a score. The flag either fires (contributing 10 points) or does not. This makes the contribution to the final score fully auditable:

- If `isolation_forest_flag = 1`, 10 points are added to the risk score
- The flag is visible in the provider signal breakdown on the dashboard
- The signal source is labeled as `isolation_forest` in the signal taxonomy

See [docs/risk-scoring-methodology.md](risk-scoring-methodology.md) for the full signal taxonomy.

## Known Limitations

1. **Unsupervised:** The model has no labeled fraud examples to learn from — it identifies statistical outliers, which may or may not be fraudulent
2. **Static training:** The model is trained once on historical data; it does not update in real time
3. **Feature scope:** Only a subset of available features is used; richer feature engineering could improve detection
4. **Contamination assumption:** The 5% contamination rate is a hyperparameter, not a measured fraud rate

## Governance

| Role | Responsibility |
|---|---|
| **Human reviewer** | All flagged cases require human review before any action |
| **System** | Score and flag; never make enforcement decisions autonomously |
| **Feedback loop** | Reviewer decisions will feed back into signal weight tuning in the pilot phase |

## Version History

| Version | Date | Notes |
|---|---|---|
| 1.0.0 | March 2026 | Initial model — hackathon submission |
