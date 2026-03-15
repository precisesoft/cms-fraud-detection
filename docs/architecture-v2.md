# Architecture v2 — AI-Powered Provider Intelligence Platform

> Revised architecture for the CMS Proactive Program Integrity hackathon.
> Replaces the ML ensemble approach with an LLM-powered reasoning layer over a
> structured analytics engine and evidence graph.

STATUS: superseded
created: 2026-03-14
updated: 2026-03-15

> **Note**: This document is superseded by [Architecture v3](architecture-v3.md).
> Rendered diagrams for the current architecture are in [docs/diagrams/](diagrams/).

---

## Core Thesis

**Don't train models. Harvest signals. Let AI reason over them.**

The public CMS data already contains enough structured signal to identify anomalous
provider behavior. The AI layer's job is not to "detect fraud" — it's to:

1. Explain why a provider's billing pattern looks unusual
2. Answer investigator questions in plain English
3. Generate charts and evidence on demand
4. Make a business owner as capable as a data engineer

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Investigator Interface                         │
│           Streamlit: Chat + Risk Dashboard + Live Charts            │
│                                                                     │
│  "Show me cardiologists in FL billing above peer average"           │
│  "Why is NPI 1234567890 flagged?"                                   │
│  "What's the average charge for HCPCS 93306 nationally?"           │
├─────────────────────────────────────────────────────────────────────┤
│                      AI Reasoning Layer                              │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  Text-to-SQL │  │ Text-to-     │  │  Narrative Generator     │  │
│  │  (DuckDB)    │  │ Cypher       │  │  (Risk explanations,     │  │
│  │              │  │ (Neo4j)      │  │   investigation briefs)  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────────┘  │
│         │                 │                      │                  │
│         │    Claude API / LLM Backbone            │                  │
│         │    (with schema context + few-shot)     │                  │
├─────────┴─────────────────┴──────────────────────┴──────────────────┤
│                      Risk Scoring API (FastAPI)                      │
│                                                                     │
│  POST /score         — Score a provider or payment pattern          │
│  GET  /provider/{npi} — Full provider evidence profile              │
│  POST /chat          — Natural language query                       │
│  GET  /signals/{npi} — All signals for a provider                   │
│  GET  /peers/{npi}   — Peer group comparison                        │
├──────────┬──────────┬───────────────┬───────────────────────────────┤
│  Signal  │ Evidence │  Peer Group   │   Source Provenance           │
│  Engine  │  Graph   │  Baselines    │   Registry                   │
│          │          │               │                               │
│ Harvests │ Neo4j:   │ By specialty, │ Every signal traces back     │
│ signals  │ Provider │ geography,    │ to exact source table,       │
│ from all │ → Case   │ practice size │ column, and filter           │
│ datasets │ → Signal │               │                               │
│          │ → Source │               │                               │
│ (DuckDB) │          │ (DuckDB)      │ (Metadata layer)             │
├──────────┴──────────┴───────────────┴───────────────────────────────┤
│                      Data Foundation (19GB staged)                   │
│                                                                     │
│  Core:  Part B Provider & Service │ Enrollment │ Revocations        │
│  Enrich: Part D │ Open Payments │ NPPES │ Geographic Variation      │
│  Screen: OIG LEIE                                                   │
│                                                                     │
│  Raw CSV → DuckDB profiling → Canonical Parquet → Signal extraction │
│                                              └──→ Neo4j projection  │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
Phase 1: Ingest & Canonicalize
  Raw CSVs (19GB) → DuckDB → Canonical Parquet tables
  - Provider identity spine (Part B + Enrollment + NPPES)
  - Service behavior (Part B Provider-Service)
  - Prescribing behavior (Part D Provider-Drug)
  - Financial relationships (Open Payments General)
  - Sanctions (Revocations + LEIE)
  - Geo benchmarks (Geographic Variation PUF)

Phase 2: Signal Harvesting
  Canonical Parquet → DuckDB analytics → Signal Store (Parquet)
  For each ProviderServiceCase (NPI + HCPCS + Place of Service):
    - Peer group baselines (specialty × state, specialty × national)
    - Z-scores (volume, intensity, pricing, payment)
    - Cross-source flags (enrollment gaps, revocation matches)
    - Financial relationship signals (Open Payments concentration)
    - Temporal signals (year-over-year changes when multi-year available)

Phase 3: Evidence Graph Projection
  Signal Store → Neo4j
  Nodes: Provider, Case, Signal, PeerGroup, Source
  Edges: HAS_CASE, HAS_SIGNAL, IN_PEER_GROUP, SOURCED_FROM
  - Every signal node carries: value, z-score, peer baseline, source provenance
  - Graph enables relationship traversal and pattern queries

Phase 4: AI Reasoning (Runtime)
  User question or payment event
    → LLM determines intent (score, query, explain, compare)
    → LLM generates SQL (DuckDB) or Cypher (Neo4j) as needed
    → Execute query, get structured results
    → LLM generates natural language response + optional chart spec
    → Streamlit renders response with interactive visualization
```

## Signal Taxonomy

### Risk Signals (suspicion indicators)

| Signal                   | Source         | Metric                                          |
| ------------------------ | -------------- | ----------------------------------------------- |
| Volume outlier           | Part B Service | `service_volume_peer_z >= 3`                    |
| Intensity outlier        | Part B Service | `services_per_bene_peer_z >= 3`                 |
| Charge ratio outlier     | Part B Service | `submitted_to_allowed_peer_z >= 3`              |
| Payment outlier          | Part B Service | `payment_peer_z >= 3`                           |
| Enrollment gap           | Enrollment     | `NOT IN current enrollment file`                |
| Revocation match         | Revocations    | `present_in_2026_revocation_file = 1`           |
| Specialty mismatch       | Part B × NPPES | Billed HCPCS inconsistent with taxonomy         |
| Prescribing anomaly      | Part D         | Opioid flag, controlled substance concentration |
| DME concentration        | DME Referring  | Unusual RBCS category concentration             |
| Financial concentration  | Open Payments  | Payment concentration to single manufacturer    |
| Place-of-service anomaly | Part B Service | Facility/office mix vs peers                    |

### Legitimacy Signals (stabilization indicators)

| Signal                 | Source          | Metric                                 |
| ---------------------- | --------------- | -------------------------------------- |
| Active enrollment      | Enrollment      | Present in current enrollment file     |
| No revocation          | Revocations     | No match in revocation file            |
| Medicare participating | Part B          | `medicare_participating_ind = Y`       |
| Peer-aligned volume    | Part B Service  | `abs(service_volume_peer_z) < 1`       |
| Peer-aligned intensity | Part B Service  | `abs(services_per_bene_peer_z) < 1`    |
| Peer-aligned pricing   | Part B Service  | `abs(submitted_to_allowed_peer_z) < 1` |
| Specialty consistent   | NPPES × Part B  | Billing matches taxonomy               |
| Diverse relationships  | Open Payments   | Payments from multiple manufacturers   |
| Established practice   | Part B Provider | `total_benes >= 100`                   |

### Risk Score Computation

```
risk_score = weighted_sum(
    revocation_signal,        # 25 pts max — high confidence
    enrollment_gap_signal,    # 8 pts max
    volume_outlier_signal,    # 20 pts max (tiered by z-score)
    intensity_outlier_signal, # 18 pts max
    charge_ratio_signal,      # 18 pts max
    payment_outlier_signal,   # 12 pts max
    # Future enrichment signals add here
) capped at 100

legitimacy_score = weighted_sum(
    active_enrollment,        # 20 pts
    no_revocation,            # 15 pts
    medicare_participating,   # 10 pts
    peer_aligned_volume,      # 12 pts
    peer_aligned_intensity,   # 12 pts
    peer_aligned_pricing,     # 12 pts
    established_practice,     # 8 pts
) capped at 100

case_label =
  IF risk >= 50 AND risk >= legitimacy + 5 THEN 'high_risk'
  IF legitimacy >= 70 AND risk < 30 THEN 'stable'
  ELSE 'review'
```

This is deterministic, fully traceable, and every point has a source. The AI layer
doesn't compute the score — it explains it.

## AI Integration Points

### 1. Natural Language Query (Text-to-SQL + Text-to-Cypher)

User asks: "How much does the average cardiologist in Florida charge for echocardiograms?"

```
→ LLM receives: question + DuckDB schema + few-shot examples
→ LLM generates: SQL query against canonical Parquet
→ DuckDB executes: returns result set
→ LLM generates: natural language answer + chart specification
→ Streamlit renders: answer text + bar chart
```

User asks: "Show me all signals for NPI 1234567890"

```
→ LLM receives: question + Neo4j schema + few-shot examples
→ LLM generates: Cypher query against evidence graph
→ Neo4j executes: returns signal nodes with provenance
→ LLM generates: structured narrative with risk/legitimacy breakdown
→ Streamlit renders: signal cards + evidence trail
```

### 2. Risk Narrative Generation

When a provider is scored, the AI generates an investigation brief:

```
Input: Structured risk score + all signal values + peer baselines + source metadata
Output: Natural language narrative like:

"Dr. Jane Smith (NPI 1234567890) is a cardiologist in Miami, FL with a risk
score of 83/100. Three factors drive this score:

1. SERVICE VOLUME (z=4.2): She performed 847 echocardiograms (HCPCS 93306)
   compared to the Florida cardiology peer average of 201. This is 4.2 standard
   deviations above peers. [Source: Part B Provider-Service 2023]

2. CHARGE RATIO (z=3.1): Her average submitted charge of $892 against a Medicare
   allowed amount of $312 yields a ratio of 2.86, compared to the peer average
   of 1.74. [Source: Part B Provider-Service 2023]

3. ENROLLMENT GAP: She does not appear in the Q4 2025 public provider enrollment
   file. [Source: Public Provider Enrollment Q4 2025]

Stabilizing factors: She is Medicare-participating and has billed consistently
for 3+ years with no revocation history."
```

### 3. Interactive Investigation Chat

The chat interface supports follow-up questions:

```
User: "Why is this provider flagged?"
AI: [Generates narrative from signals]

User: "Compare her to other cardiologists in her ZIP code"
AI: [Generates SQL for peer comparison, returns chart]

User: "Are any of her referring providers also flagged?"
AI: [Generates Cypher to traverse referral graph, returns network view]

User: "Show me her billing trend for the last 3 years"
AI: [Generates SQL for temporal analysis, returns line chart]
```

### 4. Payment-Level Risk Assessment

When a new payment pattern comes in (simulated for demo):

```
Input: NPI + HCPCS + Place of Service + Charge Amount + Beneficiary Count
→ Look up provider profile from evidence graph
→ Compare against peer baselines
→ Compute signal values
→ Generate risk score
→ AI generates explanation
→ Return: score + signals + narrative + recommended action
```

## Tech Stack (Revised)

| Layer           | Technology            | Why                                                       |
| --------------- | --------------------- | --------------------------------------------------------- |
| Data Processing | DuckDB + Polars       | Fast analytical queries on 19GB of CSVs/Parquet           |
| Evidence Graph  | Neo4j                 | Relationship traversal, signal provenance, Cypher queries |
| AI Backbone     | Claude API (Sonnet 4) | Text-to-SQL, Text-to-Cypher, narrative generation         |
| API             | FastAPI               | Async, auto-docs, production-ready                        |
| UI              | Streamlit             | Chat interface + dashboards + charts in days not weeks    |
| Charts          | Plotly                | Interactive charts rendered by AI-generated specs         |
| Storage         | Parquet files + Neo4j | No heavyweight database setup                             |

### Removed from Stack

| Removed      | Why                                                                  |
| ------------ | -------------------------------------------------------------------- |
| scikit-learn | No ML model training needed                                          |
| XGBoost      | No supervised model needed                                           |
| PyTorch      | No autoencoder needed                                                |
| SHAP         | Explainability comes from signal provenance, not model introspection |

## Project Structure (Revised)

```
cms-fraud-detection/
├── src/
│   ├── data/               # Data ingestion, canonicalization, download
│   │   ├── download.py     # Fetch CMS open data
│   │   ├── canonicalize.py # Raw CSV → canonical Parquet
│   │   └── build_demo_case_csv.py  # Existing demo case builder
│   ├── signals/            # Signal harvesting engine
│   │   ├── harvester.py    # Extract signals from canonical data
│   │   ├── peer_groups.py  # Peer baseline computation
│   │   ├── risk_score.py   # Deterministic risk/legitimacy scoring
│   │   └── taxonomy.py     # Signal definitions and weights
│   ├── graph/              # Neo4j evidence graph
│   │   ├── schema.py       # Node and edge definitions
│   │   ├── project.py      # Parquet → Neo4j projection
│   │   └── queries.py      # Common Cypher query templates
│   ├── ai/                 # LLM reasoning layer
│   │   ├── llm.py          # Claude API client wrapper
│   │   ├── text_to_sql.py  # Natural language → DuckDB SQL
│   │   ├── text_to_cypher.py # Natural language → Neo4j Cypher
│   │   ├── narrator.py     # Risk narrative generation
│   │   └── prompts/        # System prompts and few-shot examples
│   │       ├── sql_schema.md
│   │       ├── cypher_schema.md
│   │       └── narrator.md
│   ├── api/                # FastAPI endpoints
│   │   ├── main.py
│   │   ├── routes/
│   │   │   ├── score.py
│   │   │   ├── provider.py
│   │   │   ├── chat.py
│   │   │   └── signals.py
│   │   └── schemas.py      # Pydantic response models
│   └── ui/                 # Streamlit application
│       ├── app.py           # Main Streamlit app
│       ├── pages/
│       │   ├── chat.py      # Conversational interface
│       │   ├── dashboard.py # Risk overview dashboard
│       │   └── provider.py  # Provider detail view
│       └── components/
│           ├── signal_card.py
│           ├── risk_gauge.py
│           └── chart_renderer.py
├── tests/
├── data/
│   ├── raw/                # Downloaded CMS datasets (gitignored)
│   ├── processed/          # Canonical Parquet (gitignored)
│   └── features/           # Signal store (gitignored)
├── docs/
├── docker-compose.yml      # App + Neo4j
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Sprint Plan (11 days remaining: March 14-25)

### Phase 1: Data Foundation (Days 1-2, March 14-15)

- [ ] Canonicalize Part B provider + service into Parquet
- [ ] Canonicalize enrollment + revocations
- [ ] Build provider identity spine
- [ ] Refactor `build_demo_case_csv.py` into modular signal harvester

### Phase 2: Signal Engine + Graph (Days 3-5, March 16-18)

- [ ] Implement peer group baseline computation
- [ ] Implement full signal taxonomy (risk + legitimacy)
- [ ] Compute risk scores for all providers
- [ ] Set up Neo4j (docker-compose)
- [ ] Project providers, cases, and signals into Neo4j
- [ ] Verify graph queries return correct signal chains

### Phase 3: AI Layer (Days 5-7, March 18-20)

- [ ] Claude API integration with schema context
- [ ] Text-to-SQL: natural language → DuckDB queries
- [ ] Text-to-Cypher: natural language → Neo4j queries
- [ ] Narrative generator: structured signals → investigation brief
- [ ] Build few-shot prompt library for SQL and Cypher
- [ ] Test with 20+ representative questions

### Phase 4: UI + API (Days 7-9, March 20-22)

- [ ] FastAPI: /score, /provider/{npi}, /chat, /signals endpoints
- [ ] Streamlit: chat interface with query execution
- [ ] Streamlit: risk dashboard with top flagged providers
- [ ] Streamlit: provider detail view with signal cards
- [ ] Chart rendering from AI-generated specs (Plotly)

### Phase 5: Polish + Deliverables (Days 9-11, March 22-25)

- [ ] Architecture diagram (required deliverable)
- [ ] Risk-scoring explanation document
- [ ] Responsible AI considerations document
- [ ] "Path to CMS Pilot" 5-minute briefing
- [ ] End-to-end demo script
- [ ] Docker-compose full stack deployment
- [ ] README update with final quickstart

## Deliverable Checklist (per hackathon rules)

- [ ] Working demo
- [ ] Architecture diagram
- [ ] Risk-scoring explanation
- [ ] Responsible AI considerations
- [ ] 5-minute "Path to CMS Pilot" briefing
- [ ] AI tool usage disclosure
- [ ] Open-source library disclosure

## What Makes This Win

1. **AI where it matters**: LLM reasoning over structured signals, not black-box ML
2. **Full transparency**: Every point in the risk score traces to a source record
3. **Business-user accessible**: Ask questions in English, get answers with charts
4. **Dual scoring**: Both risk AND legitimacy signals — judges see balanced, responsible AI
5. **Graph-powered investigation**: Traverse provider relationships, not just flat tables
6. **Scalable architecture**: DuckDB handles 19GB locally; same pattern works at CMS scale
7. **Honest framing**: We score ProviderServiceCases from public aggregates, not fake claims
