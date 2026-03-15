# CMS Proactive Program Integrity

> Detecting anomalous provider behavior to prevent fraud, waste, and abuse before improper payments occur.

**Hackathon**: Government AI Hackathon — 14-day sprint
**Challenge**: Proactive Program Integrity (CMS)
**Status**: Incubating
**Current Phase**: Solutioning sprint active; final artifacts due March 25, 2026

## Start Here

- [Hackathon kickoff brief](docs/hackathon-kickoff.md)
- [Orientation meeting notes](docs/orientation-meeting-notes.md)
- [Team kickoff brief](docs/team-kickoff-brief.md)
- [Problem statement](docs/problem-statement.md)
- [Demo data research and graph strategy](docs/demo-data-research-plan.md)
- [Open questions for the project lead](docs/open-questions.md)
- [Official source register](docs/source-register.md)
- [Challenge research brief](docs/challenge-research.md)
- [Public dataset catalog](docs/dataset-catalog.md)

## Hackathon Envelope

- Team formation, use-case, and environment lock: March 6-March 11, 2026
- Solutioning sprint: March 12-March 25, 2026
- Submission lock: Wednesday, March 25, 2026 at 5:00 PM
- Technical evaluation: Thursday, March 26, 2026 based on orientation Q&A
- Demo day and judging: Friday, March 27, 2026 in Reston, Virginia
- Team rules: 2-5 members with at least one designated team lead
- Submission access: code may stay private if judges and the AI working group can review it
- Submission materials: must include enough for evaluation, such as a demo, README, or presentation
- AI tool usage is allowed but must be disclosed
- Public datasets only; no PHI
- Only original work created during the hackathon is eligible
- Open-source tools and libraries must be disclosed
- Explainability is required, not optional
- Cloud-native architecture is encouraged
- Final package must include submitted solution artifacts by March 25 plus a working demo,
  architecture diagram, risk-scoring explanation, responsible AI considerations, and a 5-minute
  "Path to CMS Pilot" briefing

## Planning Focus

This repository is the planning and incubation home for the CMS challenge. The immediate job is to
lock scope, datasets, judging narrative, and demo flow before committing to implementation.

The current repo state is documentation-first with empty Python package scaffolding. The architecture,
project tree, and commands below describe the intended build-out once implementation begins.

## Problem Statement

CMS loses an estimated $60B+ annually to improper payments across Medicare and Medicaid. Current detection is largely reactive — fraud is identified after payments are made. This project builds an AI system that proactively identifies anomalous provider billing patterns, flags high-risk claims before payment, and provides explainable risk scores that human reviewers can act on.

## Key Principles

1. **Explainable AI** — Every risk score has a human-readable explanation
2. **Transparent Scoring** — Full traceability from raw data to risk flag
3. **Scalable Architecture** — Cloud-native, handles national-scale claims volume
4. **Mission-Ready** — Clear pathway from MVP to agency pilot

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CMS Fraud Detection                      │
├──────────┬──────────┬──────────────┬────────────┬───────────┤
│  Ingest  │ Feature  │    Model     │ Explainer  │    API    │
│ Pipeline │ Engineering │  Ensemble  │   (SHAP)   │ Dashboard │
├──────────┼──────────┼──────────────┼────────────┼───────────┤
│ CMS Open │ Provider │ Isolation    │ Per-claim  │ FastAPI   │
│ Data     │ Profiles │ Forest +     │ risk       │ + React   │
│ Download │ Peer     │ XGBoost +    │ factors    │ dashboard │
│ + Clean  │ Groups   │ Autoencoder  │ narratives │           │
└──────────┴──────────┴──────────────┴────────────┴───────────┘
```

### Data Flow

```
Raw CMS Data → Cleaned Parquet → Feature Store → Model Scoring → Risk API → Dashboard
                                                       ↓
                                              SHAP Explanations
                                                       ↓
                                              Human Review Queue
```

## Public Data Sources

| Dataset                                 | Source       | Use                                             |
| --------------------------------------- | ------------ | ----------------------------------------------- |
| Medicare Provider Utilization & Payment | data.cms.gov | Billing patterns, service volumes, charges      |
| Medicare Part D Prescriber              | data.cms.gov | Prescription patterns, opioid flags             |
| LEIE Exclusion List                     | oig.hhs.gov  | Labeled fraud positives for supervised learning |
| Medicare Provider Compare               | data.cms.gov | Provider metadata, specialties, locations       |
| HCPCS/CPT Code Reference                | cms.gov      | Service code descriptions for explainability    |

## Tech Stack

| Layer            | Technology                                   |
| ---------------- | -------------------------------------------- |
| Language         | Python 3.12+                                 |
| Data Processing  | Polars, DuckDB                               |
| ML Models        | scikit-learn, XGBoost, PyTorch (autoencoder) |
| Explainability   | SHAP, Alibi                                  |
| API              | FastAPI                                      |
| Frontend         | React + TypeScript                           |
| Containerization | Docker                                       |
| Orchestration    | Kubernetes (k3s)                             |
| Storage          | PostgreSQL + Parquet files                   |

## Target Project Structure

```
cms-fraud-detection/
├── src/
│   ├── data/           # Data ingestion and cleaning
│   ├── pipeline/        # Feature engineering pipeline
│   ├── models/          # Model training and inference
│   ├── explainability/  # SHAP explanations and narratives
│   └── api/             # FastAPI endpoints
├── tests/               # Unit and integration tests
├── notebooks/           # EDA and prototyping
├── data/
│   ├── raw/             # Downloaded CMS datasets
│   ├── processed/       # Cleaned data
│   └── features/        # Engineered feature store
├── docs/                # Architecture and design docs
├── manifests/           # K8s deployment manifests
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Planned Quickstart

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Download CMS data
python -m src.data.download

# Run feature pipeline
python -m src.pipeline.build_features

# Train models
python -m src.models.train

# Start API
uvicorn src.api.main:app --reload

# Run tests
pytest
```

## Team

- Arun Sanna — AI/ML Engineering, Architecture
