# Architecture v3 — CMS Provider Intelligence Platform

> Production-grade, containerized application deployed via CI/CD to EKS.
> Supersedes v2. This is the production architecture.

STATUS: approved
created: 2026-03-14
updated: 2026-03-24

---

## Diagrams

All diagrams are in `docs/diagrams/` as rendered PNGs.

| #   | Diagram                                                            | File                         | Purpose                                                      |
| --- | ------------------------------------------------------------------ | ---------------------------- | ------------------------------------------------------------ |
| 1   | [System Architecture](diagrams/01-system-architecture.png)         | `01-system-architecture`     | Full-stack component map with all 14 API endpoints           |
| 2   | [Deployment Architecture](diagrams/02-deployment-architecture.png) | `02-deployment-architecture` | CI/CD pipeline: GitHub Actions → ECR → ArgoCD → EKS          |
| 3   | [Data Pipeline](diagrams/03-data-pipeline.png)                     | `03-data-pipeline`           | ETL flow: 19GB raw CMS CSVs → DuckDB → PostgreSQL + Neo4j    |
| 4   | [Scoring Engine](diagrams/04-scoring-engine.png)                   | `04-scoring-engine`          | Claim input → signal extraction → dual scoring → narrative   |
| 5   | [Evidence Graph](diagrams/05-evidence-graph.png)                   | `05-evidence-graph`          | Neo4j model: Provider → Case → Signal → Source               |
| 6   | [AI Reasoning](diagrams/06-ai-reasoning.png)                       | `06-ai-reasoning`            | Sequence: text-to-SQL chat flow + risk narrative generation  |
| 7   | [Demo User Journey](diagrams/07-demo-user-journey.png)             | `07-demo-user-journey`       | 6-section, 5-7 min demo script with timing                   |
| 8   | [Signal Taxonomy](diagrams/08-signal-taxonomy.png)                 | `08-signal-taxonomy`         | All risk + legitimacy signals with sources and point weights |
| 9   | [Fairness Evaluation](diagrams/09-fairness-evaluation.png)         | `09-fairness-evaluation`     | Cohort analysis → statistical tests → dashboard              |
| 10  | [Path to CMS Pilot](diagrams/10-path-to-pilot.png)                 | `10-path-to-pilot`           | MVP → Pilot (6mo) → Production (12mo) roadmap                |

---

## Core Thesis

**Harvest signals. Score claims. Let AI explain everything.**

This is a real application, not a demo script. It loads 19GB of public CMS data into
a database, builds a provider evidence graph, harvests signals, and provides two
interfaces:

1. **Live Payment Monitor** — Claims stream in via SSE, scored in real time (<50ms),
   displayed on a live US map with pulsing risk dots
2. **Claims Simulator** — Select a claim, push through scoring engine, see full signal breakdown
3. **Investigation Chat** — Sidebar where anyone (not just data engineers) can ask
   plain English questions and get answers with charts

All three are live at [argus.precise-lab.com](https://argus.precise-lab.com).

## System Architecture

![System Architecture](diagrams/01-system-architecture.png)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Frontend (Vite + React 19 + TypeScript + Tailwind v4) │
│                                                                         │
│  ┌─────────────────────────────────────┐  ┌──────────────────────────┐ │
│  │         Claims Simulator             │  │    Chat Sidebar          │ │
│  │                                      │  │                          │ │
│  │  Payment/claim queue (data table)    │  │  "What's the avg charge  │ │
│  │  → Select a claim                    │  │   for 93306 in FL?"      │ │
│  │  → Push through scoring engine       │  │                          │ │
│  │  → See risk score + signal breakdown │  │  → AI queries database   │ │
│  │  → Full transparency panel           │  │  → Returns answer +      │ │
│  │  → Provider profile deep dive        │  │    chart / table         │ │
│  │  → Peer comparison charts            │  │  → Follow-up context     │ │
│  └─────────────────────────────────────┘  └──────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│                        API Layer (FastAPI)                               │
│                                                                         │
│  GET  /api/dashboard       — Aggregate stats, risk distribution, top flags│
│  GET  /api/dashboard/heatmap — Risk scores aggregated by state           │
│  POST /api/score           — Score a claim against provider profile      │
│  GET  /api/providers       — List/search providers (?q= autocomplete)    │
│  GET  /api/providers/{npi} — Full provider evidence profile              │
│  GET  /api/providers/{npi}/trends — Time-series billing data             │
│  GET  /api/claims          — Paginated claims/cases queue                │
│  POST /api/chat            — NL query → streamed answer + chart (SSE)    │
│  GET  /api/signals/{npi}   — All signals for a provider                  │
│  GET  /api/peers/{npi}     — Peer group comparison data                  │
│  GET  /api/fairness        — Flagging rate by geography + specialty       │
│  GET  /api/graph/{npi}     — Evidence graph nodes + edges from Neo4j      │
│  GET  /api/live/stream     — SSE real-time scored claim stream            │
│  GET  /api/providers/{npi}/explain — Per-provider ML feature importance  │
│  GET  /api/health          — Health check for k8s probes                 │
├──────────┬──────────┬──────────────────┬────────────────────────────────┤
│  Signal  │    AI    │  Scoring Engine  │  Data Access Layer             │
│ Harvester│ Reasoner │                  │                                │
│          │          │  Deterministic   │  psycopg (PostgreSQL)          │
│ Extracts │ Claude   │  risk + legit    │  neo4j-driver (Neo4j)          │
│ signals  │ API:     │  scoring with    │  DuckDB (analytical queries)   │
│ from all │ text→SQL │  full provenance │                                │
│ sources  │ text→Cyp │  per signal      │                                │
│          │ narrate  │                  │                                │
├──────────┴──────────┴──────────────────┴────────────────────────────────┤
│                        Data Layer                                        │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │   PostgreSQL      │  │     Neo4j         │  │   DuckDB (ETL only) │  │
│  │                   │  │                   │  │                      │  │
│  │ providers         │  │ (:Provider)       │  │ Raw CSV ingestion    │  │
│  │ claims/cases      │  │ (:Case)           │  │ Parquet generation   │  │
│  │ signals           │  │ (:Signal)         │  │ Peer baseline calc   │  │
│  │ peer_baselines    │  │ (:PeerGroup)      │  │                      │  │
│  │ scores            │  │ (:Source)          │  │ Not used at runtime  │  │
│  │ source_provenance │  │                   │  │                      │  │
│  │                   │  │ -[:HAS_CASE]->    │  │                      │  │
│  │ (operational      │  │ -[:HAS_SIGNAL]->  │  │                      │  │
│  │  queries, CRUD)   │  │ -[:IN_PEER]->     │  │                      │  │
│  │                   │  │ -[:SOURCED_FROM]-> │  │                      │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Three Views, One Application

### View 1: Overview Dashboard (Landing Page)

This is what judges see first. Immediate visual impact with aggregate intelligence.

```
┌─────────────────────────────────────────────────────────────────────┐
│  CMS Provider Intelligence Platform    [🔍 Search NPI/name]  [Chat]│
├─────────────────────────────────────────────────────────────────────┤
│  Dashboard  │  Claims Simulator  │  Fairness                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐          │
│  │  42,186   │ │  1,247    │ │   2,891   │ │   38,048  │          │
│  │ Providers │ │ High Risk │ │  Review   │ │  Stable   │          │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘          │
│                                                                     │
│  Risk Heatmap (US States)            Top Flagged Providers          │
│  ┌─────────────────────────┐        ┌──────────────────────┐       │
│  │                         │        │ 1. NPI 1234  Risk:93 │       │
│  │    [US Choropleth Map]  │        │ 2. NPI 5678  Risk:89 │       │
│  │    Green → Yellow → Red │        │ 3. NPI 9012  Risk:87 │       │
│  │                         │        │ ...                   │       │
│  │  Click state to filter  │        │ [View All →]          │       │
│  └─────────────────────────┘        └──────────────────────┘       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Flow**: Open app → See aggregate stats + heatmap → Click a state or flagged provider
→ Navigate to Claims Simulator filtered by that selection.

### View 2: Claims Simulator

The core workflow. Simulates CMS payment scanning with full transparency.

```
┌─────────────────────────────────────────────────────────────────────┐
│  CMS Provider Intelligence Platform    [🔍 Search NPI/name]  [Chat]│
├─────────────────────────────────────────────────────────────────────┤
│  Dashboard  │  Claims Simulator  │  Fairness                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Claims Queue                              Provider Detail Panel    │
│  ┌──────────────────────────────────┐     ┌──────────────────────┐ │
│  │ NPI        │ HCPCS │ Risk │ Band │     │ Dr. Jane Smith       │ │
│  │ 1234567890 │ 93306 │  83  │ HIGH │ ◄── │ Cardiologist, FL     │ │
│  │ 9876543210 │ 99213 │  42  │ REV  │     │                      │ │
│  │ 5555555555 │ 27447 │  12  │ SAFE │     │ Risk: 83 / Legit: 31 │ │
│  │ ...        │       │      │      │     │                      │ │
│  └──────────────────────────────────┘     │ ┌── Signals ───────┐ │ │
│                                            │ │ ▲ Volume  z=4.2  │ │
│  [Scan Selected] [Scan Batch] [Filter ▼]  │ │ ▲ Charge  z=3.1  │ │
│                                            │ │ ▲ Enroll  gap    │ │
│                                            │ │ ▼ Partic  yes    │ │
│                                            │ │ ▼ Revoke  none   │ │
│                                            │ └──────────────────┘ │
│                                            │                      │ │
│                                            │ Peer Comparison:     │ │
│                                            │ [Bar Chart: vs FL    │ │
│                                            │  cardiologist avg]   │ │
│                                            │                      │ │
│                                            │ Billing Trends:      │ │
│                                            │ [Line Chart: volume  │ │
│                                            │  over time vs peers] │ │
│                                            │                      │ │
│                                            │ AI Narrative:        │ │
│                                            │ "This cardiologist   │ │
│                                            │  bills 4.2x the FL  │ │
│                                            │  peer average for    │ │
│                                            │  echocardiograms..." │ │
│                                            │                      │ │
│                                            │ [Evidence Graph ▸]   │ │
│                                            └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

**Flow**: Select a claim → Click "Scan" → Scoring engine runs → Risk score appears
with full signal breakdown, peer comparison, time-series trends, and AI narrative.

### Interface 2: Chat Sidebar

Slides in from the right. Anyone can ask plain English questions:

```
┌──────────────────────────┐
│  Investigation Assistant  │
├──────────────────────────┤
│                          │
│  You: What's the average │
│  charge for HCPCS 93306  │
│  in Florida?             │
│                          │
│  AI: The average Medicare│
│  allowed amount for      │
│  93306 in FL is $287.    │
│  The median submitted    │
│  charge is $412.         │
│                          │
│  ┌──────────────────┐   │
│  │  [Bar Chart]      │   │
│  │  FL vs National   │   │
│  │  by specialty     │   │
│  └──────────────────┘   │
│                          │
│  You: Compare this to TX │
│                          │
│  AI: TX averages $301... │
│                          │
│  ┌─────────────────────┐ │
│  │ [Type a question...] │ │
│  └─────────────────────┘ │
└──────────────────────────┘
```

**How it works**: User types question → API sends to Claude with DB schema context →
Claude generates SQL → Executes against PostgreSQL → Claude formats response +
optional chart spec → Frontend renders streamed text + Recharts visualization.

### View 4: Fairness Dashboard

Proves responsible AI compliance. Most teams write a paragraph — we show live metrics.

```
┌─────────────────────────────────────────────────────────────────────┐
│  CMS Provider Intelligence Platform    [🔍 Search NPI/name]  [Chat]│
├─────────────────────────────────────────────────────────────────────┤
│  Dashboard  │  Claims Simulator  │  Fairness                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Fairness Analysis                                                  │
│                                                                     │
│  Statistical Parity: ✅ PASS (0.03 difference)                      │
│  Disparate Impact:   ✅ PASS (0.92 ratio, threshold > 0.80)         │
│                                                                     │
│  Flagging Rate by Specialty              Flagging Rate by State     │
│  ┌────────────────────────┐             ┌────────────────────────┐  │
│  │ Cardiology     ██████ 8%│             │ FL  ██████ 4.1%       │  │
│  │ Orthopedics    █████ 6% │             │ TX  █████ 3.8%        │  │
│  │ Internal Med   ████ 4%  │             │ CA  █████ 3.6%        │  │
│  │ Family Med     ███ 3%   │             │ NY  ████ 3.2%         │  │
│  │ Radiology      ███ 3%   │             │ ...                   │  │
│  └────────────────────────┘             └────────────────────────┘  │
│                                                                     │
│  Note: Higher flagging rates for certain specialties reflect known   │
│  billing pattern variations, not systemic bias. See methodology.    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**How it works**: Pre-computed fairness metrics from batch analysis. Shows flagging
rate distribution across geography and specialty cohorts with statistical parity
and disparate impact measures.

## Tech Stack

| Layer      | Technology                        | Why                                                   |
| ---------- | --------------------------------- | ----------------------------------------------------- |
| Frontend   | Vite + React 19 + TypeScript      | Fast builds, SPA with React Router                    |
| UI         | Tailwind CSS v4 + Lucide + Motion | Utility-first CSS, icons, animations                  |
| Charts     | Recharts + react-simple-maps      | Composable charts, US choropleth heatmap              |
| Backend    | Python 3.12 + FastAPI             | Async, auto-docs, scoring engine                      |
| Database   | PostgreSQL 16                     | Operational store, SQL queries, production-grade      |
| Graph      | Neo4j 5                           | Relationship traversal, Cypher queries                |
| ETL        | DuckDB + Polars                   | One-time data processing (not runtime)                |
| AI         | AWS Bedrock (Claude)              | FedRAMP authorized, GovCloud-ready, multi-model       |
| Containers | Docker + docker-compose           | Local dev, multi-service                              |
| CI         | GitHub Actions                    | Unified pipeline: lint, test, build, security, deploy |
| CD         | ArgoCD                            | GitOps deployment to EKS                              |
| Registry   | Amazon ECR                        | AWS-native container image store                      |

## Data Flow

![Data Pipeline](diagrams/03-data-pipeline.png)

```
Phase 1: ETL (one-time, offline)
  Raw CSVs (19GB)
    → DuckDB profiling & validation
    → Canonical Parquet tables
    → PostgreSQL bulk load (providers, cases, signals, baselines)
    → Neo4j projection (graph relationships)

Phase 2: Runtime (application)
  User selects claim in UI
    → POST /api/score with claim data
    → Scoring engine:
        1. Look up provider profile from PostgreSQL
        2. Fetch peer baselines for specialty × geography
        3. Compute z-scores for volume, intensity, pricing, payment
        4. Check cross-source flags (enrollment, revocation)
        5. Apply deterministic scoring formula
        6. Generate signal list with provenance
        7. Call Claude API for narrative explanation
    → Return: { score, signals[], narrative, provenance[] }
    → Frontend renders risk breakdown

Phase 3: Chat (on-demand, streamed)
  User types question in chat sidebar
    → POST /api/chat with message + conversation history
    → Claude API (via AWS Bedrock):
        1. Receives question + PostgreSQL schema + few-shot examples
        2. Generates SQL query
        3. Backend executes against PostgreSQL
        4. Claude formats natural language answer
        5. Optionally generates Recharts chart specification
    → Return: SSE stream with tokens + chart_spec event at end
    → Frontend renders streamed text + optional chart

Phase 4: Fairness (batch, pre-computed)
  After ETL:
    → Group scores by provider_state and provider_type
    → Compute flagging rate (% above risk threshold) per cohort
    → Compute statistical parity difference and disparate impact ratio
    → Store in fairness_metrics table
    → GET /api/fairness serves pre-computed results
```

## PostgreSQL Schema

```sql
-- Provider identity spine
CREATE TABLE providers (
    npi VARCHAR(10) PRIMARY KEY,
    last_org_name TEXT,
    first_name TEXT,
    credentials TEXT,
    entity_code CHAR(1),        -- I=individual, O=organization
    city TEXT,
    state CHAR(2),
    zip5 CHAR(5),
    provider_type TEXT,          -- specialty
    medicare_participating BOOLEAN,
    total_hcpcs_codes INT,
    total_benes INT,
    total_services BIGINT,
    total_payment_amt NUMERIC(14,2),
    present_in_enrollment BOOLEAN,
    enrollment_record_count INT,
    present_in_revocation BOOLEAN,
    revocation_reasons TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Provider-service cases (primary scoring unit)
CREATE TABLE cases (
    case_id TEXT PRIMARY KEY,       -- NPI|HCPCS|place_of_service
    npi VARCHAR(10) REFERENCES providers(npi),
    hcpcs_cd VARCHAR(10),
    hcpcs_desc TEXT,
    place_of_service CHAR(1),
    tot_benes INT,
    tot_srvcs INT,
    avg_submitted_charge NUMERIC(10,2),
    avg_medicare_allowed_amt NUMERIC(10,2),
    avg_medicare_payment_amt NUMERIC(10,2),
    estimated_case_payment_amt NUMERIC(14,2),
    services_per_bene NUMERIC(8,4),
    submitted_to_allowed_ratio NUMERIC(8,4),
    payment_to_allowed_ratio NUMERIC(8,4),
    -- Scoring
    risk_score SMALLINT,
    legitimacy_score SMALLINT,
    case_label TEXT,                -- high_risk, review, stable
    risk_reasons TEXT,
    legitimacy_reasons TEXT,
    -- Peer context
    peer_scope TEXT,                -- state_specific or national_fallback
    peer_case_count INT,
    peer_avg_tot_srvcs NUMERIC(10,2),
    -- Z-scores
    service_volume_peer_z NUMERIC(8,4),
    services_per_bene_peer_z NUMERIC(8,4),
    submitted_to_allowed_peer_z NUMERIC(8,4),
    payment_peer_z NUMERIC(8,4),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Individual signals with provenance
CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    npi VARCHAR(10) REFERENCES providers(npi),
    case_id TEXT REFERENCES cases(case_id),
    signal_type TEXT,               -- volume_outlier, enrollment_gap, etc.
    signal_direction TEXT,          -- risk or legitimacy
    signal_value NUMERIC(10,4),
    z_score NUMERIC(8,4),
    peer_baseline NUMERIC(10,4),
    points_contributed SMALLINT,
    source_table TEXT,
    source_description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Peer group baselines
CREATE TABLE peer_baselines (
    id SERIAL PRIMARY KEY,
    provider_type TEXT,
    state CHAR(2),                  -- NULL for national
    hcpcs_cd VARCHAR(10),
    place_of_service CHAR(1),
    scope TEXT,                     -- state or national
    case_count INT,
    avg_tot_srvcs NUMERIC(10,2),
    std_tot_srvcs NUMERIC(10,4),
    avg_services_per_bene NUMERIC(8,4),
    std_services_per_bene NUMERIC(8,4),
    avg_charge_ratio NUMERIC(8,4),
    std_charge_ratio NUMERIC(8,4),
    avg_payment NUMERIC(10,2),
    std_payment NUMERIC(10,4),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Fairness metrics (pre-computed during ETL)
CREATE TABLE fairness_metrics (
    id SERIAL PRIMARY KEY,
    cohort_type TEXT,              -- 'state' or 'specialty'
    cohort_value TEXT,             -- e.g. 'FL' or 'Cardiology'
    total_providers INT,
    flagged_providers INT,
    flagging_rate NUMERIC(6,4),
    avg_risk_score NUMERIC(6,2),
    statistical_parity_diff NUMERIC(6,4),
    disparate_impact_ratio NUMERIC(6,4),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX idx_cases_npi ON cases(npi);
CREATE INDEX idx_cases_label ON cases(case_label);
CREATE INDEX idx_cases_risk_score ON cases(risk_score DESC);
CREATE INDEX idx_signals_npi ON signals(npi);
CREATE INDEX idx_signals_case ON signals(case_id);
CREATE INDEX idx_peer_baselines_lookup ON peer_baselines(provider_type, state, hcpcs_cd);
CREATE INDEX idx_providers_state ON providers(state);
CREATE INDEX idx_providers_type ON providers(provider_type);
```

## Neo4j Graph Model

![Evidence Graph](diagrams/05-evidence-graph.png)

```cypher
// Node types
(:Provider {npi, name, specialty, state, risk_score, legitimacy_score})
(:Case {case_id, hcpcs, risk_score, label})
(:Signal {type, direction, value, z_score, points, source})
(:PeerGroup {specialty, state, scope, case_count})
(:Source {table_name, description, year})

// Relationships
(:Provider)-[:HAS_CASE]->(:Case)
(:Case)-[:HAS_SIGNAL]->(:Signal)
(:Provider)-[:IN_PEER_GROUP]->(:PeerGroup)
(:Signal)-[:SOURCED_FROM]->(:Source)
(:Provider)-[:ENROLLED_IN {status}]->(:Enrollment)
(:Provider)-[:REVOKED {reason}]->(:Revocation)
```

## Project Structure

```
cms-fraud-detection/
├── src/                        # Python backend (FastAPI)
│   ├── api/                    # FastAPI app + routes
│   │   ├── app.py              # App factory with lifespan
│   │   ├── auth.py             # JWT authentication
│   │   ├── deps.py             # DB pool management, FastAPI deps
│   │   ├── graph_client.py     # Neo4j graph client
│   │   ├── schemas.py          # Pydantic request/response models
│   │   └── routes/
│   │       ├── auth.py         # POST /api/auth/login, /api/auth/register
│   │       ├── cases.py        # GET /api/cases
│   │       ├── chat.py         # POST /api/chat (SSE streaming)
│   │       ├── claims.py       # GET /api/claims
│   │       ├── dashboard.py    # GET /api/dashboard, /api/dashboard/heatmap
│   │       ├── fairness.py     # GET /api/fairness
│   │       ├── graph.py        # GET /api/graph/{npi}
│   │       ├── network.py      # GET /api/network/{npi}
│   │       ├── providers.py    # GET /api/providers, /api/providers/{npi}
│   │       ├── score.py        # POST /api/score
│   │       ├── signals.py      # GET /api/signals/{npi}
│   │       ├── simulate.py     # POST /api/simulate
│   │       └── validation.py   # GET /api/validation
│   ├── ai/                     # LLM reasoning layer
│   │   ├── bedrock.py          # AWS Bedrock client wrapper
│   │   ├── chart_spec.py       # AI → Recharts chart config
│   │   ├── narrative.py        # Structured signals → narrative
│   │   ├── prompts.py          # System prompts + few-shot examples
│   │   └── text_to_sql.py      # NL → PostgreSQL SQL
│   ├── scoring/                # Deterministic scoring engine
│   │   ├── extract.py          # Signal extraction per case
│   │   ├── score.py            # Risk + legitimacy score computation
│   │   └── taxonomy.py         # Signal definitions, weights, thresholds
│   ├── models/                 # ML models
│   │   ├── anomaly.py          # Isolation Forest training
│   │   └── anomaly_scorer.py   # Anomaly score inference
│   ├── validation/             # Retrospective validation
│   │   └── retrospective.py    # Scoring vs. revocation outcomes
│   ├── data/                   # Data loading utilities
│   │   ├── load_postgres.py    # Bulk data loader
│   │   ├── build_demo_case_csv.py
│   │   └── project_graph.py    # Neo4j graph projection
│   └── pipeline/               # Feature engineering
│       └── build_features.py   # Polars-based provider features
├── tests/                      # Backend test suite (30+ test files)
│   ├── test_extract.py, test_score.py, test_taxonomy.py  # Scoring
│   ├── test_text_to_sql.py, test_narrative.py, test_bedrock.py  # AI
│   ├── test_anomaly.py, test_anomaly_scorer.py  # ML models
│   ├── test_retrospective.py   # Validation
│   ├── test_dashboard.py, test_providers.py, ...  # API routes
│   └── load/                   # k6 load tests
├── frontend/                   # Vite + React 19 SPA
│   ├── src/
│   │   ├── App.tsx             # React Router route definitions
│   │   ├── main.tsx            # Entry point
│   │   ├── pages/              # Route pages
│   │   │   ├── Dashboard.tsx   # Landing page with stats + heatmap
│   │   │   ├── Providers.tsx   # Provider list + search
│   │   │   ├── ProviderDetail.tsx  # Provider deep-dive
│   │   │   ├── Claims.tsx      # Claims queue
│   │   │   ├── ClaimDetail.tsx # Individual claim view
│   │   │   ├── Simulate.tsx    # Claims simulator
│   │   │   ├── Fairness.tsx    # Fairness dashboard
│   │   │   ├── RiskMap.tsx     # Geographic risk heatmap
│   │   │   ├── Investigations.tsx / InvestigationDetail.tsx
│   │   │   ├── Analytics.tsx   # Analytics view
│   │   │   ├── Validation.tsx  # Retrospective validation results
│   │   │   └── Login.tsx       # Authentication
│   │   ├── components/         # Shared components
│   │   │   ├── Layout.tsx      # App shell with nav
│   │   │   ├── AssistantDrawer.tsx  # AI chat sidebar
│   │   │   ├── EvidenceGraph.tsx    # Neo4j graph visualization
│   │   │   ├── ProtectedRoute.tsx   # Auth guard
│   │   │   └── StatusBadge.tsx, PriorityBadge.tsx, Timeline.tsx
│   │   ├── contexts/           # React context providers
│   │   │   └── AuthContext.tsx
│   │   ├── lib/                # Utilities
│   │   │   ├── api.ts          # API client (fetch wrapper)
│   │   │   ├── helpers.ts      # Formatting utilities
│   │   │   └── utils.ts        # General utilities
│   │   └── mocks/              # MSW mock handlers for tests
│   ├── Dockerfile              # Multi-stage: build + nginx
│   ├── nginx.conf              # Production nginx config
│   ├── vite.config.ts
│   └── vitest.config.ts
├── db/
│   └── init.sql                # PostgreSQL schema (raw SQL, no Alembic)
├── k8s/                        # Kubernetes manifests (EKS)
│   ├── argocd-app.yaml         # ArgoCD Application
│   └── cms-fraud/              # Namespace resources
│       ├── namespace.yaml, secrets.yaml
│       ├── postgres.yaml, postgres-configmap.yaml
│       ├── neo4j.yaml
│       ├── api.yaml, frontend.yaml
├── terraform/                  # AWS infrastructure (ECR, IAM)
│   ├── ecr.tf, iam.tf, providers.tf, variables.tf
├── .github/
│   ├── workflows/
│   │   ├── pipeline.yml        # Unified: gate + security + quality + build + deploy
│   │   └── terraform.yml       # Plan on PR, apply on merge
│   ├── copilot-instructions.md
│   ├── copilot-setup-steps.yml
│   ├── agents/                 # 9 Copilot agent personas
│   └── pull_request_template.md
├── docker-compose.yml          # Local dev: db + neo4j + api + frontend
├── Dockerfile                  # Backend API image
├── pyproject.toml
├── docs/                       # All documentation + diagrams
├── data/                       # gitignored — raw, processed, models
└── README.md
```

## Deployment Architecture

![Deployment Architecture](diagrams/02-deployment-architecture.png)

```
Local Development:
  docker compose up -d
  ├── api        (FastAPI on :8000)
  ├── frontend   (Vite/nginx on :3000)
  ├── db         (PostgreSQL 16 on :5432)
  └── neo4j      (Neo4j 5 on :7687 + :7474)

CI/CD Pipeline (unified pipeline.yml):
  PR opened
    → Gate: conventional commit PR title check
    → Security (parallel): gitleaks + bandit + pip-audit + npm audit
    → Quality (parallel):
        Backend: ruff + mypy + pytest + coverage (95% threshold)
        Frontend: eslint + tsc + vitest (80% lines) + vite build
    → Build: Docker images (amd64) + CycloneDX SBOMs
    → Scan: Trivy on both images
  Merge to main (additional):
    → Release: push to ECR with :sha + :latest tags
    → Deploy: update precise-manifests with SHA tags → ArgoCD auto-syncs

EKS Cluster (508aas-platform-dev-cluster, us-east-1):
  Namespace: cms-fraud
  ├── api (Deployment, 2 replicas, LoadBalancer)
  ├── frontend (Deployment, nginx serving Vite build)
  ├── postgres (StatefulSet, 20Gi gp3 PVC)
  ├── neo4j (StatefulSet, 10Gi gp3 PVC)
  └── Istio VirtualService → https://argus.precise-lab.com
```

## Docker Compose (Local Dev)

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: cms_fraud
      POSTGRES_USER: cms
      POSTGRES_PASSWORD: cms_local_dev
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/01_init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cms -d cms_fraud"]
      interval: 5s

  neo4j:
    image: neo4j:5-community
    environment:
      NEO4J_AUTH: neo4j/cms_graph_dev
    ports: ["7474:7474", "7687:7687"]
    volumes:
      - neo4jdata:/data
    healthcheck:
      test: ["CMD-SHELL", "cypher-shell -u neo4j -p cms_graph_dev 'RETURN 1'"]
      interval: 10s

  api:
    build: .
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql://cms:cms_local_dev@db:5432/cms_fraud
      NEO4J_URI: bolt://neo4j:7687
      NEO4J_PASSWORD: cms_graph_dev
    depends_on:
      db: { condition: service_healthy }
      neo4j: { condition: service_healthy }

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [api]

volumes:
  pgdata:
  neo4jdata:
```

---

## Development Process

For the full development process — AI-assisted workflow, agile process, 19 epics delivered, and CI/CD pipeline details — see [development-process.md](development-process.md).
