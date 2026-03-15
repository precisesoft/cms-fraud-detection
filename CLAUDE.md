> **Context**: `50_PROJECTS/_incubating/cms-fraud-detection/` · CMS Fraud Detection
> **Pipeline**: Hackathon project — 14-day sprint
> **Parent**: [../../CLAUDE.md](../../CLAUDE.md)

# CMS Fraud Detection — Claude Context

## What This Is

AI system for proactive detection of anomalous Medicare provider billing behavior. Built for a government AI hackathon focused on mission-ready, deployable systems.

## Hackathon Judging Criteria

1. Explainable, Responsible AI
2. Transparent scoring and traceability
3. Scalable, cloud-native architecture
4. Clear pathway from MVP to agency pilot

## Architecture Decisions

- **Polars over Pandas**: Faster, lower memory for large CMS datasets (millions of claims)
- **Ensemble approach**: Isolation Forest (unsupervised) + XGBoost (supervised via LEIE labels) + Autoencoder (deep anomaly)
- **SHAP for explainability**: Industry standard, generates per-feature contribution scores
- **FastAPI**: Async, auto-docs, production-ready
- **DuckDB**: Analytical queries on Parquet without a full warehouse

## Key Concepts

### Provider Profiling

Each provider gets a behavioral profile built from:

- Service mix (what CPT codes they bill)
- Volume patterns (how many patients, services per patient)
- Charge patterns (average charge vs peer group)
- Geographic patterns (referral networks, patient travel distance)
- Temporal patterns (billing spikes, weekend/holiday billing)

### Peer Groups

Providers are compared against peers in the same:

- Specialty (e.g., cardiologist vs cardiologist)
- Geographic region (HRR or state)
- Practice size (solo vs group)

### Risk Score

Final output is a 0-100 risk score with:

- Component scores from each model
- Top contributing features (via SHAP)
- Natural language explanation
- Confidence interval

## Data Layout

- `data/raw/` — Downloaded CMS CSVs (gitignored)
- `data/processed/` — Cleaned Parquet files
- `data/features/` — Engineered feature store

## Dev Workflow

```bash
# All commands run inside Docker or venv
python -m src.data.download    # Fetch CMS open data
python -m src.pipeline.build_features  # Feature engineering
python -m src.models.train     # Train ensemble
uvicorn src.api.main:app       # Start API
pytest                         # Run tests
```

## When Helping Here

1. Prioritize explainability — every model output needs SHAP values
2. Use Polars for data processing, not Pandas
3. Keep the API response schema stable (dashboard depends on it)
4. All provider IDs are NPI (National Provider Identifier) — 10-digit numbers
5. Never store raw CMS data in git — only code and processed schemas
