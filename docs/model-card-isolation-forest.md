# Model Card: Isolation Forest Anomaly Detector

_Following [Mitchell et al. (2019)](https://arxiv.org/abs/1810.03993) model card framework._

## Model Details

| Property         | Value                                   |
| ---------------- | --------------------------------------- |
| Algorithm        | `sklearn.ensemble.IsolationForest`      |
| Estimators       | 200                                     |
| Contamination    | 0.05 (5%)                               |
| Random state     | 42                                      |
| Feature scaler   | `sklearn.preprocessing.StandardScaler`  |
| Feature count    | 49 numeric features                     |
| Training library | scikit-learn (via joblib serialization) |
| Model artifact   | `data/models/isolation_forest.joblib`   |
| Runtime scorer   | `src/models/anomaly_scorer.py`          |

## Intended Use

**Primary purpose**: Secondary anomaly detection signal that corroborates the rule-based scoring engine. The isolation forest identifies statistically unusual billing patterns that may not trigger explicit threshold-based rules.

**Role in system**: Advisory only. The anomaly score (0-100, higher = more anomalous) appears alongside the rule-based risk score in API responses and AI-generated narratives. It is never used as the sole basis for any enforcement or flagging decision.

**Users**: CMS fraud investigators reviewing provider risk profiles through the Argus dashboard.

**Out-of-scope uses**:

- Autonomous enforcement or payment denial decisions
- Final determination of fraud without human review
- Use on data domains outside Medicare Part B provider billing patterns

## Training Data

| Field      | Value                                                                      |
| ---------- | -------------------------------------------------------------------------- |
| Dataset    | Medicare Physician & Other Practitioners -- by Provider and Service (2022) |
| Source     | CMS data.cms.gov (public domain)                                           |
| Population | 10,282 providers after feature engineering                                 |
| Labels     | None -- unsupervised model                                                 |
| PHI        | None -- all data is publicly available aggregate statistics                |

### Input Features (49 numeric columns from `provider_features`)

- **Volume**: total services, beneficiaries, service lines, services per beneficiary, bene-day services
- **Charges**: mean/max/std submitted charges, allowed amounts, payments, estimated total payment
- **Ratios**: charge-to-allowed ratio, payment-to-allowed ratio, services per beneficiary
- **Concentration**: Herfindahl-Hirschman Index (HHI), top-code share, top-3-code share
- **Peer z-scores**: volume, intensity, charge, and payment outlier z-scores (mean and max)
- **Risk scores**: seed risk/legitimacy scores from rule-based engine

All features are standardized (zero mean, unit variance) via StandardScaler before training.

## Evaluation

### Correlation with Rule-Based Scores

Pearson correlation: **0.125**

This low correlation is **by design**. It means the isolation forest captures different anomaly patterns than the rule-based engine. Together, the two approaches provide broader coverage -- the rule engine catches known patterns while the isolation forest surfaces statistically unusual behavior that may not match any explicit rule.

### Detection Rates (Revoked Providers)

| Anomaly Percentile    | Detection Rate                      |
| --------------------- | ----------------------------------- |
| Top 5% most anomalous | 28.1% of revoked providers captured |
| Top 10%               | 42.7%                               |
| Top 20%               | 63.0%                               |

Ground truth: 335 revoked NPIs from the 2026 CMS revocation list.

### Top Features by Permutation Importance

| Feature               | Importance |
| --------------------- | ---------- |
| max_submitted_charge  | -0.079     |
| mean_allowed_amt      | -0.073     |
| mean_payment_amt      | -0.073     |
| mean_submitted_charge | -0.061     |
| max_allowed_amt       | -0.059     |
| max_payment_amt       | -0.049     |
| top_code_share        | -0.041     |
| charge_cv             | -0.041     |
| enrolled_2025         | -0.037     |
| unique_hcpcs_codes    | -0.036     |

Note: Negative permutation importance values result from using revocation status as a proxy label for evaluation. The isolation forest is unsupervised and does not use labels during training. These values indicate which features, when shuffled, reduce the model's ability to rank revoked providers as anomalous.

## Scoring Mechanism

The model's `decision_function()` output (lower = more anomalous) is transformed to a 0-100 scale:

```
normalized = clamp(50 - raw_score * 100, 0, 100)
```

Higher scores indicate more anomalous billing patterns. Scores are ordinal rankings, not calibrated probabilities. The score is served via `src/models/anomaly_scorer.py` using lazy-loaded model caching (`lru_cache`).

## Per-Provider Feature Importance

The system provides per-provider explainability via a **leave-one-out approximation** (`src/explainability/shap_explainer.py`, exposed at `GET /api/providers/{npi}/explain`).

**Method**: For each of the 49 features, zero the value, re-score through the model, and measure the anomaly score delta. Features with the largest absolute delta are the strongest contributors to that provider's anomaly score.

| Delta    | Direction  | Meaning                                      |
| -------- | ---------- | -------------------------------------------- |
| Positive | Risk       | Feature was pushing anomaly score higher     |
| Negative | Protective | Feature was reducing the anomaly score       |
| Zero     | Neutral    | Feature was already at zero or had no effect |

**Trade-offs vs. SHAP**: Leave-one-out uses zero as the baseline rather than the expected value, which may overstate the contribution of binary features (e.g., `enrolled_2025`). However, it requires no additional dependencies, runs in under 100ms, and produces directionally identical top-feature rankings for tree-based models.

**UI integration**: The Provider Detail page displays the top 5 features as horizontal bars (red = risk-increasing, green = protective) alongside a Score Agreement indicator comparing the rule-based risk score and the ML anomaly score.

## Limitations

1. **Single-year cross-section**: Trained on 2022 data only. No temporal validation across years. Provider behavior may shift over time.
2. **Provider-level aggregation**: Operates on provider-level summary statistics, not individual claim lines. Cannot detect anomalies in specific procedures.
3. **Proxy label evaluation**: Revocation status is an imperfect proxy for fraud. Many revocations are administrative, and many fraudulent providers have not yet been revoked.
4. **Orthogonal by design**: The 0.125 correlation means the model's anomaly ranking often disagrees with rule-based scores. This is intentional but requires investigators to interpret both signals.
5. **No calibration**: Scores are ordinal rankings, not probabilities. A score of 80 does not mean "80% chance of fraud."
6. **Feature leakage risk**: Some input features (seed risk/legitimacy scores) are derived from the rule-based engine, creating partial circularity. However, the low correlation suggests the model learned patterns beyond what rules capture.
7. **Contamination assumption**: The 5% contamination rate is a hyperparameter, not a measured fraud rate.

## Ethical Considerations

- **Not a standalone decision tool**: Anomaly scores are always presented alongside explainable rule-based signals, peer comparisons, and AI-generated narratives. No automated action is taken based on anomaly scores alone.
- **No protected attributes**: The model does not use race, gender, ethnicity, or age as features. However, geographic and specialty features may correlate with demographic patterns.
- **Fairness monitoring**: The system includes a dedicated `/api/fairness` endpoint that monitors flagging rate disparities across geography and specialty, using statistical parity and disparate impact metrics. See [responsible-ai-considerations.md](responsible-ai-considerations.md).
- **Human-in-the-loop**: All flagged cases require human review before any action is taken. The system is designed to assist, not replace, human judgment.

## Governance

| Role           | Responsibility                                                           |
| -------------- | ------------------------------------------------------------------------ |
| Human reviewer | All flagged cases require human review before any action                 |
| System         | Score and surface signals; never make enforcement decisions autonomously |
| Feedback loop  | Reviewer decisions feed back into signal weight tuning in pilot phase    |

## Version History

| Version | Date       | Notes                                                         |
| ------- | ---------- | ------------------------------------------------------------- |
| 1.0.0   | March 2026 | Initial model (200 estimators, 49 features, 10,282 providers) |
| 1.1.0   | March 2026 | Added per-provider leave-one-out feature importance endpoint  |
