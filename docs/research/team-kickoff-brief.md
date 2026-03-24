# Team Kickoff Brief

> Working brief for the CMS Proactive Program Integrity hackathon team.

STATUS: active
created: 2026-03-12
updated: 2026-03-12

---

## Mission

Build an explainable, demo-ready system that helps CMS move from reactive pay-and-chase to
proactive provider-pattern review using only public data.

## Problem Statement

CMS processes massive payment volume across Medicare and Medicaid, but suspicious provider behavior
is often identified only after payments have already been made. That creates a costly pay-and-chase
cycle, slows intervention, and makes it harder for reviewers to understand why a billing pattern
looks suspicious or why it may still be legitimate.

Our opportunity is to build a transparent decision-support system that connects fragmented public
billing, enrollment, sanctions, and financial-relationship data into evidence-backed risk cases.

## What We Are Building

We are not claiming claim-line adjudication from public data. The public CMS files are aggregate
provider and provider-service datasets.

The core unit in the demo is:

- `ProviderServiceCase = NPI + HCPCS + place_of_service + year`

Each case answers one question:

`Should this provider-service payment pattern be reviewed more closely, and why?`

For each case, the system should show:

- a risk score
- a review band
- top signals contributing to suspicion
- top signals contributing to legitimacy
- peer comparison context
- source provenance

## Recommended MVP Scope

### Must-have data spine

- Medicare Part B provider and service
- Medicare Part B provider
- Public provider enrollment
- Revoked providers
- NPPES identity layer
- Geographic peer baselines

### Strong enrichment layers

- Medicare Part D provider and drug
- DME referring provider and service
- Open Payments physician profile and general payments

### Use with caution

- OIG LEIE as screening or retrospective validation, not the main label source

## Current Assets Ready Now

### Research and planning

- [Problem statement](/Users/jarvis_arunlab/research-lab/50_PROJECTS/_incubating/cms-fraud-detection/docs/problem-statement.md)
- [Demo data research and graph strategy](/Users/jarvis_arunlab/research-lab/50_PROJECTS/_incubating/cms-fraud-detection/docs/demo-data-research-plan.md)
- [Public dataset catalog](/Users/jarvis_arunlab/research-lab/50_PROJECTS/_incubating/cms-fraud-detection/docs/dataset-catalog.md)
- [Source register](/Users/jarvis_arunlab/research-lab/50_PROJECTS/_incubating/cms-fraud-detection/docs/source-register.md)

### Data staged locally

- CMS public sources under [data/raw/public_sources/cms](/Users/jarvis_arunlab/research-lab/50_PROJECTS/_incubating/cms-fraud-detection/data/raw/public_sources/cms)
- Open Payments under [data/raw/public_sources/openpayments](/Users/jarvis_arunlab/research-lab/50_PROJECTS/_incubating/cms-fraud-detection/data/raw/public_sources/openpayments)
- NPPES under [data/raw/public_sources/nppes](/Users/jarvis_arunlab/research-lab/50_PROJECTS/_incubating/cms-fraud-detection/data/raw/public_sources/nppes)
- OIG under [data/raw/public_sources/oig](/Users/jarvis_arunlab/research-lab/50_PROJECTS/_incubating/cms-fraud-detection/data/raw/public_sources/oig)

### Demo-ready CSV

- [provider_service_cases_demo.csv](/Users/jarvis_arunlab/research-lab/50_PROJECTS/_incubating/cms-fraud-detection/data/processed/demo/provider_service_cases_demo.csv)
- Built by [build_demo_case_csv.py](/Users/jarvis_arunlab/research-lab/50_PROJECTS/_incubating/cms-fraud-detection/src/data/build_demo_case_csv.py)

Current output profile:

- `13,225` rows
- `10,282` unique NPIs
- `225` `high_risk`
- `7,000` `review`
- `6,000` `stable`

## How We Win With Judges

The strongest position is not "we built a black-box fraud model."

The strongest position is:

- we used official public CMS and HHS data
- we connected behavior, identity, enrollment, and sanctions into one evidence model
- we show both suspicion and legitimacy signals
- we preserve explainability and provenance
- we provide a credible path from public-data MVP to future pre-payment screening

## Demo Storyline

![Demo User Journey](diagrams/07-demo-user-journey.png)

### Opening

Start with the operational pain:

- CMS has high volume
- reactive review is expensive
- analysts need faster, more transparent triage

### Product view

Show a ranked case list:

- high-risk provider-service cases
- review queue
- stable cases with supporting evidence

### Drill-down

Click into one case and show:

- provider identity
- service and place of service
- peer comparison
- risk reasons
- legitimacy reasons
- enrollment or revocation context
- optional graph of connected evidence

### Close

End with the differentiator:

- this is not just anomaly detection
- this is explainable provider evidence intelligence

## Architecture

> Full specification: [Architecture v3](architecture-v3.md) | All diagrams: [docs/diagrams/](diagrams/)

![System Architecture](diagrams/01-system-architecture.png)

### Data Pipeline

![Data Pipeline](diagrams/03-data-pipeline.png)

### Evidence Graph

![Evidence Graph](diagrams/05-evidence-graph.png)

## Example Signal Families

### Risk

- service volume outlier versus peers
- services-per-beneficiary outlier
- submitted-charge versus allowed-amount anomaly
- abnormal place-of-service behavior
- revocation match
- missing current enrollment match
- cross-program inconsistency

### Legitimacy

- present in current enrollment file
- no revocation match
- Medicare participating
- peer-aligned volume
- peer-aligned service intensity
- peer-aligned pricing

## Team Workstreams

### 1. Data and scoring

- stabilize the provider identity spine
- enrich the demo CSV with Part D and Open Payments
- formalize signal logic and scoring

### 2. Graph and backend

- define the case and signal schema
- load curated entities and edges into a graph store
- expose drill-down data for the UI

### 3. Frontend and demo

- ranked queue view
- case detail view
- graph and peer-comparison panels
- one polished end-to-end story

### 4. Deck and narrative

- final problem statement
- architecture diagram
- responsible AI positioning
- path-to-pilot slide

## Decisions Needed Today

1. Approve `ProviderServiceCase` as the main scored unit.
2. Approve `DuckDB + Parquet + graph projection` as the technical direction.
3. Decide whether Open Payments is phase 1 enrichment or phase 2 enrichment.
4. Decide whether the first demo should use only the generated CSV or also include live graph data.
5. Assign owners for data, UI, graph/backend, and deck/demo.

## Recommended Next 24 Hours

1. Lock the demo storyline around `high_risk`, `review`, and `stable` cases.
2. Add Part D and Open Payments enrichment to the demo case file.
3. Pick 10-15 showcase cases for the live demo.
4. Draft the UI wireframe and the architecture slide.
5. Split implementation ownership across the team.

## Bottom Line

We already have enough public data and one working demo dataset to start building immediately. The
highest-leverage path is to keep the system explainable, provider-centered, and evidence-backed,
then turn that into a visually strong case-review experience for judges.
