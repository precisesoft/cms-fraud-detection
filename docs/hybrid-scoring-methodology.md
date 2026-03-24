# Hybrid Scoring Methodology

## Overview

The hybrid scoring model extends the deterministic CMS fraud scoring engine with a weakly supervised machine learning layer. It is designed to preserve explainability while improving ranking power for provider-service observations that exhibit multiple moderate-risk patterns at once.

Like the base scoring system, the hybrid model operates at the **provider-service case** level (one provider + one HCPCS code). It does **not** replace the original explainable score. Instead, it adds two new outputs:

- **ML Predicted Probability** (0-100): Learned probability that an observation resembles historically suspicious patterns
- **Hybrid Composite Score** (0-100): A weighted score combining rules, anomaly evidence, provider context, and ML output

This produces a layered scoring stack:

1. **Explainable score** — deterministic, signal-based, judge- and analyst-friendly
2. **Anomaly score** — focused on peer deviations and unusual utilization/charge patterns
3. **Weakly supervised probability** — learned ranking signal from additive training data
4. **Hybrid composite score** — calibrated operational score for detail views and v2 endpoints

## Architecture

The hybrid model is an additive layer and does not modify the legacy scoring contract.

```text
provider_service_cases / provider_features
        ↓
bridge_* SQL views in db/init.sql
        ↓
weak label generation
        ↓
LogisticRegression training bundle
        ↓
score_observation(row) → ML Predicted Probability
        ↓
compute_composite_score(row, learned_score)
        ↓
Composite risk label: low / medium / high / critical
```

Runtime and storage components:

- `src/models/weak_supervised.py` — feature engineering, weak-supervision training, runtime scoring, composite scoring
- `db/init.sql` — additive bridge views, weak label rules, model registry, persisted scores
- `trained_models` — metadata for each trained model artifact
- `observation_model_scores` — persisted case-level probabilities and composite scores
- `/api/v2/score` — real-time hybrid scoring for on-the-fly scoring
- `/api/v2/claims/simulate` — real-time hybrid scoring for simulations

## Design Goals

The hybrid model was built to satisfy four constraints:

- **Preserve explainability** — the legacy explainable score remains the primary reasoned score
- **Improve ranking** — allow multiple weak signals to combine into a stronger suspicion estimate
- **Support additive rollout** — use new tables, views, and v2 APIs without breaking current flows
- **Keep analyst control** — convert model output into interpretable composite bands rather than opaque classifications

## Theory

### Why weak supervision

Ground-truth healthcare fraud labels are scarce, delayed, and often incomplete. Waiting for fully adjudicated fraud outcomes would create a tiny and biased training set.

Instead, the model uses **weak supervision**:

- high-confidence heuristic cases become positive labels
- high-confidence low-risk cases become negative labels
- ambiguous observations are excluded from training

This approach allows the system to learn from public CMS-derived structure without pretending that every observation has a definitive legal fraud label.

### Why logistic regression

The learned layer uses **logistic regression** because it offers a good trade-off between performance, simplicity, and interpretability:

- outputs calibrated probabilities rather than hard classes
- handles mixed numeric signals well after scaling
- is stable on moderate-sized tabular datasets
- supports inspection of coefficients if deeper model review is needed
- is easier to defend in a judging or audit context than more opaque ensemble models

The model is trained with:

- `class_weight="balanced"`
- `solver="lbfgs"`
- `max_iter=1000`
- standard feature scaling via `StandardScaler`
- stratified train/test split with `test_size = 0.2`

## Observation-Level Inputs

The hybrid model consumes 20 engineered numeric features:

| Feature | Meaning |
| ------- | ------- |
| `avg_submitted_charge` | Average submitted charge for the observation |
| `avg_allowed_amount` | Average Medicare allowed amount |
| `avg_payment_amount` | Average Medicare payment amount |
| `total_services` | Total services billed |
| `total_beneficiaries` | Total beneficiaries served |
| `rule_score` | Lightweight enrollment/revocation rule score |
| `anomaly_score` | Peer-deviation anomaly score |
| `provider_context_score` | Provider-scale/context indicator |
| `hybrid_risk_score` | Existing explainable risk score seed |
| `charge_delta_pct` | Charge anomaly proxy from peer z-score |
| `utilization_delta_pct` | Utilization anomaly proxy from peer z-score |
| `charge_per_service` | Charge intensity proxy |
| `services_per_bene` | Utilization intensity proxy |
| `payment_to_charge_ratio` | Payment efficiency / reimbursement ratio |
| `is_revoked` | Revocation indicator |
| `is_excluded` | Exclusion indicator |
| `graph_node_degree` | Simple network breadth proxy |
| `graph_hcpcs_count` | Number of HCPCS connections |
| `graph_drug_count` | Drug-related graph activity count |
| `graph_shared_specialty_count` | Shared specialty network count |

These inputs are assembled from additive bridge views over `provider_service_cases` and `provider_features`.

## Component Formulas

## Rule Score

The weak-supervision feature layer uses a compact rule score distinct from the full explainable risk score.

$$
\mathrm{rule\_score} = \min\left(35,\; 25 \cdot \mathbb{1}[\mathrm{revoked}] + 10 \cdot \mathbb{1}[\mathrm{not\ enrolled}]\right)
$$

Where:

- `revoked` means the provider appears in the 2026 revocation file
- `not enrolled` means the provider is absent from the 2025 enrollment file

This feature is intentionally narrow. It captures the strongest enrollment integrity evidence without duplicating the full legacy score taxonomy.

## Anomaly Score

The anomaly component measures deviation from peers using two signals:

1. charge abnormality vs. peers
2. services-per-beneficiary abnormality vs. peers

First define the services-per-beneficiary ratio:

$$
\mathrm{spb\_ratio} =
\begin{cases}
\mathrm{explicit\ value}, & \text{if present} \\
\dfrac{\mathrm{services\_per\_bene}}{\mathrm{peer\_avg\_spb}}, & \text{otherwise}
\end{cases}
$$

Then compute:

$$
\mathrm{charge\_component} = \mathrm{clip}(15 \cdot z_{charge},\; 0,\; 45)
$$

$$
\mathrm{spb\_component} = \mathrm{clip}(10 \cdot (\mathrm{spb\_ratio} - 1),\; 0,\; 20)
$$

$$
\mathrm{anomaly\_score} = \mathrm{clip}(\mathrm{charge\_component} + \mathrm{spb\_component},\; 0,\; 65)
$$

Where `clip(x, a, b)` truncates $x$ into the interval $[a,b]$.

Interpretation:

- charge deviations dominate the anomaly score
- utilization inflation contributes additional evidence
- the score is capped to prevent anomaly alone from overwhelming the full composite

## Provider Context Score

The provider context score captures scale and structural footprint. It is not a fraud score by itself; it gives the model context for how large and complex the provider appears.

$$
\mathrm{provider\_context\_score} = \mathrm{clip}\left(
\mathrm{clip}\left(\frac{\mathrm{total\_payment}}{100000}, 0, 5\right)
+ \mathrm{clip}\left(\frac{\mathrm{drug\_count}}{5}, 0, 5\right)
+ \mathrm{clip}\left(\frac{\mathrm{graph\_degree}}{10}, 0, 5\right),
0, 15
\right)
$$

This means the context layer rewards evidence of:

- larger payment footprint
- broader service or drug diversity
- larger graph/network neighborhood

In practice, this helps the model differentiate isolated anomalies from anomalies occurring in larger operational footprints.

## Weak Label Construction

Training labels are created in `bridge_observation_labels_v`.

### Positive weak labels

An observation receives `weak_label = 1` if **any** of the following hold:

- provider is revoked
- provider is excluded
- existing explainable score `hybrid_risk_score >= 92`
- `rule_score >= 35` **and** `anomaly_score >= 15`

Formally:

$$
\mathrm{weak\_label} = 1
$$

if

$$
\mathrm{revoked} \lor \mathrm{excluded} \lor (\mathrm{hybrid\_risk\_score} \ge 92) \lor ((\mathrm{rule\_score} \ge 35) \land (\mathrm{anomaly\_score} \ge 15))
$$

### Negative weak labels

An observation receives `weak_label = 0` if all of the following hold:

- `hybrid_risk_score <= 30`
- not revoked
- not excluded
- `rule_score <= 5`
- `anomaly_score <= 8`

Formally:

$$
\mathrm{weak\_label} = 0
$$

if

$$
(\mathrm{hybrid\_risk\_score} \le 30)
\land \neg\mathrm{revoked}
\land \neg\mathrm{excluded}
\land (\mathrm{rule\_score} \le 5)
\land (\mathrm{anomaly\_score} \le 8)
$$

### Ambiguous observations

All other observations receive `weak_label = NULL` and are excluded from training.

This is an important design choice: the model trains only on high-confidence positives and negatives, reducing label noise at the cost of smaller training coverage.

## Learned Probability

After feature scaling, the model learns coefficients $\beta$ for a logistic regression:

$$
P(y=1 \mid x) = \sigma(\beta_0 + \beta^\top x)
$$

where

$$
\sigma(t) = \frac{1}{1 + e^{-t}}
$$

At runtime, the returned ML score is:

$$
\mathrm{ml\_predicted\_probability} = 100 \cdot P(y=1 \mid x)
$$

This value is clipped into $[0,100]$ and rounded to one decimal place.

Interpretation:

- this is a **suspicion probability**, not a legal fraud probability
- it estimates similarity to the weakly labeled suspicious class
- it should be used as ranking support, not as a standalone enforcement decision

## Composite Score

The operational hybrid score combines four components:

- rule evidence
- anomaly evidence
- provider context
- learned probability

First, the model computes a stronger rule component for composite scoring:

$$
\mathrm{rule\_component} = \mathrm{clip}(40 \cdot \mathbb{1}[\mathrm{revoked}] + 30 \cdot \mathbb{1}[\mathrm{excluded}] + 20 \cdot \mathbb{1}[\mathrm{charge\ ratio} \ge 3] + 10 \cdot \mathbb{1}[\mathrm{spb\ ratio} \ge 3] + 10 \cdot \mathbb{1}[\mathrm{validation\ issues} > 0], 0, 100)
$$

Then the composite score is:

$$
\mathrm{composite} = \mathrm{clip}(0.45 \cdot \mathrm{rule\_component} + 0.30 \cdot \mathrm{anomaly\_score} + 0.10 \cdot \mathrm{provider\_context\_score} + 0.15 \cdot \mathrm{learned\_score}, 0, 100)
$$

### Safety floors

The composite score is then adjusted upward for high-confidence conditions:

- if revoked, `composite >= 92`
- else if excluded, `composite >= 82`
- if `charge_ratio >= 4` and `spb_ratio >= 3`, `composite >= 70`

These floors ensure the model cannot dilute severe compliance or extreme behavioral signals.

## Composite Risk Labels

The composite score maps to four hybrid labels:

| Hybrid Label | Composite Score |
| ------------ | --------------- |
| `critical` | 90-100 |
| `high` | 70-89.9 |
| `medium` | 40-69.9 |
| `low` | 0-39.9 |

These labels are intentionally separate from the legacy provider bands (`stable`, `review`, `high_risk`).

- legacy bands remain tied to the explainable score
- hybrid labels express the broader operational suspicion level from the combined model

## Training and Evaluation

Training uses a stratified 80/20 split and records:

- training row count
- test row count
- positive class rate in train/test
- ROC-AUC
- average precision

These metrics are saved to:

- local artifact metadata in `data/validation/weak_supervised_results.json`
- `trained_models.training_metrics` in Postgres when DB writeback is enabled

The scoring outputs are written to `observation_model_scores` with:

- `predicted_probability`
- `composite_score`
- `risk_label`
- `score_metadata`

## Runtime Usage

### Real-time scoring

The hybrid model is served in additive v2 endpoints:

- `/api/v2/score`
- `/api/v2/claims/simulate`

These endpoints preserve the existing explainable score while adding ML-assisted outputs.

### Persisted scoring

Offline training can also persist results into `observation_model_scores`, enabling:

- provider detail rollups
- claim/investigation detail views
- model version tracking
- re-scoring without modifying base claim/provider tables

## Interpretation Guidelines

The hybrid score should be interpreted as a **decision-support layer**, not as final truth.

Recommended usage:

- use the **explainable score** to answer *why* the observation is suspicious
- use the **ML predicted probability** to rank which borderline observations deserve attention first
- use the **composite score** to summarize total operational concern across rule, anomaly, context, and learned evidence

The hybrid score is most useful when:

- the explainable score is moderate but several signals align
- there is evidence spread across multiple weak dimensions
- investigators need a more nuanced priority ordering than deterministic thresholds alone provide

## Limitations

- weak labels are heuristic, not adjudicated fraud outcomes
- the model currently uses `is_excluded = 0` for runtime v2 scoring unless separate exclusion enrichment is loaded
- graph features are lightweight proxies, not full graph-model embeddings
- logistic regression captures additive relationships better than deep interactions
- the composite score is designed for prioritization, not automated denial or sanction decisions

## Relationship to the Base Methodology

The base methodology in [docs/risk-scoring-methodology.md](docs/risk-scoring-methodology.md) remains the foundation of the system.

The hybrid methodology differs in three ways:

1. it learns from weakly labeled examples rather than only applying deterministic thresholds
2. it combines multiple evidence layers into a single composite score
3. it introduces a second label system (`low` / `medium` / `high` / `critical`) for operational prioritization

In short:

- **Base score** = deterministic and fully reasoned
- **Hybrid score** = additive, probabilistic, and prioritization-oriented
