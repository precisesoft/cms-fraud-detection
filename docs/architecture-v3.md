# Architecture v3 — CMS Provider Intelligence Platform

> Production-grade, containerized application deployed via CI/CD to EKS.
> Supersedes v2. This is the build plan.

STATUS: approved-draft
created: 2026-03-14
updated: 2026-03-14

---

## Core Thesis

**Harvest signals. Score claims. Let AI explain everything.**

This is a real application, not a demo script. It loads 19GB of public CMS data into
a database, builds a provider evidence graph, harvests signals, and provides two
interfaces:

1. **Claims Simulator** — Payments flow in, get scanned, risk-scored in real time
   with full transparency into every factor
2. **Investigation Chat** — Sidebar where anyone (not just data engineers) can ask
   plain English questions and get answers with charts

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js + TypeScript + shadcn/ui)         │
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
│  POST /api/score          — Score a claim against provider profile       │
│  GET  /api/providers      — List/search providers                       │
│  GET  /api/providers/{npi}— Full provider evidence profile              │
│  GET  /api/claims         — Paginated claims/cases queue                │
│  POST /api/chat           — Natural language query → answer + chart     │
│  GET  /api/signals/{npi}  — All signals for a provider                  │
│  GET  /api/peers/{npi}    — Peer group comparison data                  │
│  GET  /api/health         — Health check for k8s probes                 │
├──────────┬──────────┬──────────────────┬────────────────────────────────┤
│  Signal  │    AI    │  Scoring Engine  │  Data Access Layer             │
│ Harvester│ Reasoner │                  │                                │
│          │          │  Deterministic   │  SQLAlchemy (PostgreSQL)       │
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

## Two Interfaces, One Application

### Interface 1: Claims Simulator (Main View)

This is what judges see first. It simulates the real CMS workflow:

```
┌─────────────────────────────────────────────────────────────────────┐
│  CMS Provider Intelligence Platform                    [Chat ▸]    │
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
│                                            │ AI Narrative:        │ │
│                                            │ "This cardiologist   │ │
│                                            │  bills 4.2x the FL  │ │
│                                            │  peer average for    │ │
│                                            │  echocardiograms..." │ │
│                                            └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

**Flow**: Select a claim → Click "Scan" → Scoring engine runs → Risk score appears
with full signal breakdown and AI-generated narrative explaining every factor.

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
optional chart spec → Frontend renders Recharts visualization.

## Tech Stack

| Layer         | Technology               | Why                                                    |
| ------------- | ------------------------ | ------------------------------------------------------ |
| Frontend      | Next.js 15 + TypeScript  | SSR, app router, API routes as BFF                     |
| UI Components | shadcn/ui + Tailwind CSS | Polished, accessible, fast to build                    |
| Charts        | Recharts                 | React-native, composable, AI can specify chart configs |
| Backend       | Python 3.12 + FastAPI    | Async, auto-docs, scoring engine                       |
| Database      | PostgreSQL 16            | Operational store, SQL queries, production-grade       |
| Graph         | Neo4j 5                  | Relationship traversal, Cypher queries                 |
| ETL           | DuckDB + Polars          | One-time data processing (not runtime)                 |
| AI            | AWS Bedrock (Claude)     | FedRAMP authorized, GovCloud-ready, multi-model        |
| Containers    | Docker + docker-compose  | Local dev, multi-service                               |
| CI            | GitHub Actions           | Lint, test, build, coverage                            |
| CD            | ArgoCD                   | GitOps deployment to EKS                               |
| Registry      | Amazon ECR               | AWS-native container image store                       |

## Data Flow

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

Phase 3: Chat (on-demand)
  User types question in chat sidebar
    → POST /api/chat with message + conversation history
    → Claude API:
        1. Receives question + PostgreSQL schema + few-shot examples
        2. Generates SQL query
        3. Backend executes against PostgreSQL
        4. Claude formats natural language answer
        5. Optionally generates Recharts chart specification
    → Return: { answer, chart_spec?, data? }
    → Frontend renders text + optional chart
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
├── backend/                    # Python FastAPI application
│   ├── src/
│   │   ├── api/                # FastAPI routes
│   │   │   ├── main.py         # App factory, middleware, lifespan
│   │   │   ├── routes/
│   │   │   │   ├── score.py    # POST /api/score
│   │   │   │   ├── providers.py# GET /api/providers, /api/providers/{npi}
│   │   │   │   ├── claims.py   # GET /api/claims
│   │   │   │   ├── chat.py     # POST /api/chat
│   │   │   │   └── signals.py  # GET /api/signals/{npi}, /api/peers/{npi}
│   │   │   └── schemas.py      # Pydantic request/response models
│   │   ├── scoring/            # Scoring engine
│   │   │   ├── engine.py       # Risk + legitimacy score computation
│   │   │   ├── signals.py      # Signal extraction per case
│   │   │   └── taxonomy.py     # Signal definitions, weights, thresholds
│   │   ├── ai/                 # LLM reasoning layer
│   │   │   ├── client.py       # AWS Bedrock client wrapper
│   │   │   ├── text_to_sql.py  # NL → PostgreSQL SQL
│   │   │   ├── narrator.py     # Structured signals → narrative
│   │   │   └── prompts/        # System prompts + few-shot examples
│   │   ├── graph/              # Neo4j integration
│   │   │   ├── client.py       # Neo4j driver wrapper
│   │   │   ├── queries.py      # Cypher query templates
│   │   │   └── project.py      # Data → Neo4j projection
│   │   ├── db/                 # PostgreSQL integration
│   │   │   ├── engine.py       # SQLAlchemy engine + session
│   │   │   ├── models.py       # SQLAlchemy ORM models
│   │   │   └── seed.py         # Load processed data into PostgreSQL
│   │   └── etl/                # One-time data processing
│   │       ├── ingest.py       # Raw CSV → DuckDB → Parquet
│   │       ├── canonicalize.py # Build provider identity spine
│   │       ├── signals.py      # Harvest signals from all sources
│   │       ├── peers.py        # Compute peer baselines
│   │       └── load.py         # Parquet → PostgreSQL + Neo4j
│   ├── tests/
│   │   ├── test_scoring.py
│   │   ├── test_signals.py
│   │   ├── test_api.py
│   │   └── test_chat.py
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── alembic/                # DB migrations
│       └── versions/
├── frontend/                   # Next.js 15 application
│   ├── app/
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Claims simulator (main view)
│   │   ├── providers/
│   │   │   └── [npi]/
│   │   │       └── page.tsx    # Provider detail page
│   │   └── api/                # BFF routes (optional proxy)
│   ├── components/
│   │   ├── ui/                 # shadcn/ui components
│   │   ├── claims-table.tsx
│   │   ├── provider-detail.tsx
│   │   ├── signal-card.tsx
│   │   ├── risk-gauge.tsx
│   │   ├── peer-chart.tsx
│   │   ├── chat-sidebar.tsx
│   │   └── chart-renderer.tsx
│   ├── hooks/
│   │   ├── use-score.ts
│   │   ├── use-chat.ts
│   │   └── use-providers.ts
│   ├── lib/
│   │   ├── api.ts              # API client (fetch wrapper)
│   │   └── types.ts            # TypeScript interfaces
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   └── Dockerfile              # Multi-stage: build + standalone output
├── manifests/                  # Kubernetes deployment
│   ├── base/
│   │   ├── namespace.yaml
│   │   ├── backend-deployment.yaml
│   │   ├── backend-service.yaml
│   │   ├── frontend-deployment.yaml
│   │   ├── frontend-service.yaml
│   │   ├── postgres-statefulset.yaml
│   │   ├── neo4j-statefulset.yaml
│   │   ├── ingress.yaml
│   │   └── kustomization.yaml
│   └── overlays/
│       ├── dev/
│       │   └── kustomization.yaml
│       └── prod/
│           └── kustomization.yaml
├── .github/
│   └── workflows/
│       ├── ci.yaml             # Lint, test, build, coverage
│       └── cd.yaml             # Build images, push to registry
├── docker-compose.yml          # Local dev: backend + frontend + pg + neo4j
├── docs/
├── data/                       # gitignored — raw and processed data
└── README.md
```

## Deployment Architecture

```
Local Development:
  docker-compose up
  ├── backend    (FastAPI on :8000)
  ├── frontend   (Next.js on :3000, standalone output in prod)
  ├── postgres   (PostgreSQL 16 on :5432)
  └── neo4j      (Neo4j 5 on :7687 + :7474)

CI/CD Pipeline:
  Push to main
    → GitHub Actions:
        1. Lint (ruff + eslint)
        2. Test (pytest + vitest)
        3. Coverage check
        4. Build Docker images (backend + frontend)
        5. Push to container registry
        6. Update manifests with new image tags
    → ArgoCD detects manifest change
    → ArgoCD syncs to EKS cluster
    → Judges access via ingress URL

EKS Cluster:
  Namespace: cms-fraud-detection
  ├── backend (Deployment, 2 replicas)
  ├── frontend (Deployment, 2 replicas, Next.js standalone)
  ├── postgres (StatefulSet, PVC)
  ├── neo4j (StatefulSet, PVC)
  └── ingress (ALB or nginx-ingress)
```

## Docker Compose (Local Dev)

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql://cms:cms@postgres:5432/cms_fraud
      NEO4J_URI: bolt://neo4j:7687
      NEO4J_PASSWORD: changeme
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      AWS_REGION: ${AWS_REGION:-us-east-1}
      BEDROCK_MODEL_ID: ${BEDROCK_MODEL_ID:-anthropic.claude-sonnet-4-20250514}
    depends_on:
      postgres:
        condition: service_healthy
      neo4j:
        condition: service_healthy

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: cms_fraud
      POSTGRES_USER: cms
      POSTGRES_PASSWORD: cms
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cms"]
      interval: 5s
      retries: 5

  neo4j:
    image: neo4j:5-community
    environment:
      NEO4J_AUTH: neo4j/changeme
    volumes:
      - neo4jdata:/data
    ports:
      - "7474:7474"
      - "7687:7687"
    healthcheck:
      test: ["CMD", "neo4j", "status"]
      interval: 10s
      retries: 5

volumes:
  pgdata:
  neo4jdata:
```

---

# Epics

## Epic 1: Data Foundation

**Goal**: Build the ETL pipeline that transforms 19GB of raw CMS CSVs into a loaded
PostgreSQL database and Neo4j graph, ready for the application to query.

**Acceptance Criteria**:

- [ ] Raw CSVs are ingested via DuckDB into canonical Parquet tables
- [ ] Provider identity spine built from Part B + Enrollment + Revocations
- [ ] Peer baselines computed by (specialty × state × HCPCS × place_of_service)
- [ ] Signals harvested for every ProviderServiceCase
- [ ] Risk and legitimacy scores computed for all cases
- [ ] PostgreSQL schema created and loaded with all tables
- [ ] Neo4j graph projected with Provider → Case → Signal → Source relationships
- [ ] ETL is repeatable: `python -m backend.src.etl.load` runs end-to-end
- [ ] Data integrity verified: row counts match, no null NPIs in providers table

**Stories**:

1. Create PostgreSQL schema with Alembic migrations
2. Build DuckDB ingestion pipeline (raw CSV → Parquet)
3. Build provider identity spine (Part B + Enrollment + Revocations)
4. Compute peer baselines by specialty × geography
5. Harvest signals and compute risk/legitimacy scores
6. Bulk load Parquet into PostgreSQL
7. Project graph into Neo4j
8. Write ETL integration test

---

## Epic 2: Scoring Engine

**Goal**: Build a deterministic scoring engine that takes any claim (NPI + HCPCS +
place of service + charge + volume) and returns a risk score with full signal
breakdown and source provenance.

**Acceptance Criteria**:

- [ ] `score(npi, hcpcs, place_of_service, charge, volume)` returns a `ScoreResult`
- [ ] `ScoreResult` contains: risk_score, legitimacy_score, case_label, signals[],
      narrative, provenance[]
- [ ] Each signal includes: type, direction, value, z_score, peer_baseline,
      points_contributed, source_table
- [ ] Scoring is deterministic — same input always produces same output
- [ ] Scoring works for providers already in the database (lookup) and new patterns
      (compute against peer baselines on the fly)
- [ ] Scoring engine has >90% test coverage

**Stories**:

1. Define signal taxonomy and weights in `taxonomy.py`
2. Implement signal extraction for each signal type
3. Implement risk score computation (weighted sum with tiered thresholds)
4. Implement legitimacy score computation
5. Implement case labeling logic (high_risk / review / stable)
6. Implement on-the-fly scoring for new claim patterns
7. Write comprehensive scoring tests with known expected outputs

---

## Epic 3: Evidence Graph

**Goal**: Neo4j graph that enables relationship traversal and investigation queries.
Judges can see how providers, cases, signals, and sources connect.

**Acceptance Criteria**:

- [ ] Graph contains: Provider, Case, Signal, PeerGroup, Source nodes
- [ ] Relationships: HAS_CASE, HAS_SIGNAL, IN_PEER_GROUP, SOURCED_FROM
- [ ] Cypher query for "all signals for NPI X" returns correct results
- [ ] Cypher query for "high-risk providers in state Y" works
- [ ] Cypher query for "providers with similar signal patterns" works
- [ ] Graph data matches PostgreSQL data (consistency check)
- [ ] Neo4j client wrapper with connection pooling

**Stories**:

1. Define Neo4j node and relationship schema
2. Build projection pipeline (PostgreSQL → Neo4j)
3. Write Cypher query templates for common patterns
4. Build Neo4j client wrapper with health checks
5. Write graph consistency tests

---

## Epic 4: AI Reasoning Layer

**Goal**: Claude API integration that powers text-to-SQL queries, risk narratives,
and the chat interface. A business owner can ask questions and get answers without
knowing SQL.

**Acceptance Criteria**:

- [ ] Text-to-SQL: natural language → PostgreSQL SQL → execute → formatted answer
- [ ] Narrative generator: structured signals → human-readable investigation brief
- [ ] Chat endpoint handles multi-turn conversation with context
- [ ] Chart specification: AI can return Recharts-compatible chart configs
- [ ] Prompt library with few-shot examples for SQL generation
- [ ] SQL injection prevention: generated SQL is validated before execution
- [ ] Fallback: if AI generates invalid SQL, returns helpful error, not a crash
- [ ] Response latency < 5s for typical queries

**Stories**:

1. Build AWS Bedrock client wrapper with retry and error handling
2. Create PostgreSQL schema prompt with table descriptions and examples
3. Implement text-to-SQL with query validation and sandboxing
4. Implement narrative generator for risk score explanations
5. Implement chat endpoint with conversation history
6. Build chart specification generator (AI → Recharts config)
7. Write test suite with 20+ representative questions
8. Add SQL injection guards and query complexity limits

---

## Epic 5: API Layer

**Goal**: FastAPI backend that serves the frontend with all data, scoring, and chat
capabilities. Production-ready with proper error handling, CORS, health checks.

**Acceptance Criteria**:

- [ ] All endpoints from the architecture spec are implemented
- [ ] Pydantic schemas for all request/response models
- [ ] CORS configured for frontend origin
- [ ] Health check endpoint for k8s probes
- [ ] Structured logging (JSON)
- [ ] Error handling middleware (no stack traces in responses)
- [ ] API auto-docs at /docs (Swagger UI)
- [ ] Response times: < 200ms for data queries, < 5s for AI-powered endpoints

**Stories**:

1. FastAPI app factory with middleware and lifespan
2. Implement `/api/providers` and `/api/providers/{npi}` routes
3. Implement `/api/claims` route with pagination and filtering
4. Implement `/api/score` route (scoring engine integration)
5. Implement `/api/chat` route (AI layer integration)
6. Implement `/api/signals/{npi}` and `/api/peers/{npi}` routes
7. Add Pydantic schemas and response models
8. Add health check, CORS, error handling middleware

---

## Epic 6: Claims Simulator UI

**Goal**: React frontend that shows a claims queue, lets judges select and scan
claims through the scoring engine, and displays full risk breakdowns with
signal cards and peer comparison charts.

**Acceptance Criteria**:

- [ ] Claims data table with sortable columns (NPI, HCPCS, risk score, band)
- [ ] Click a row → Provider detail panel slides in
- [ ] "Scan" button pushes claim through scoring engine, shows result
- [ ] Risk gauge component (0-100 with color bands)
- [ ] Signal cards showing risk and legitimacy factors
- [ ] Peer comparison chart (provider vs peer average)
- [ ] AI narrative displayed in the detail panel
- [ ] Responsive layout, works on desktop and tablet
- [ ] Loading states and error handling

**Stories**:

1. Scaffold Next.js 15 + TypeScript + shadcn/ui project
2. Build API client and TypeScript types
3. Build claims data table component
4. Build provider detail panel with signal cards
5. Build risk gauge component
6. Build peer comparison chart (Recharts)
7. Integrate scoring engine — "Scan" button flow
8. Build responsive layout with slide-in detail panel
9. Add loading states, error boundaries, empty states

---

## Epic 7: Chat Sidebar

**Goal**: Sliding sidebar chat interface where users type plain English questions
and get answers with optional charts. No SQL knowledge needed.

**Acceptance Criteria**:

- [ ] Sidebar slides in/out from the right edge
- [ ] Text input with send button
- [ ] Messages render with markdown support
- [ ] AI responses can include inline charts (Recharts)
- [ ] AI responses can include data tables
- [ ] Conversation history maintained during session
- [ ] Suggested questions shown when chat is empty
- [ ] Loading indicator while AI is processing

**Stories**:

1. Build chat sidebar shell (slide in/out, responsive)
2. Build message list component (user + AI messages)
3. Build text input with send action
4. Integrate with `/api/chat` endpoint
5. Build chart renderer for AI-generated chart specs
6. Build data table renderer for query results
7. Add suggested questions component
8. Add streaming response support (SSE or chunked)

---

## Epic 8: CI/CD Pipeline

**Goal**: Automated pipeline from push to deployed application. GitHub Actions for
CI, ArgoCD for CD to EKS.

**Acceptance Criteria**:

- [ ] Push to any branch triggers CI (lint + test + build)
- [ ] Push to `main` triggers CD (build images + push + deploy)
- [ ] Backend CI: ruff lint, pytest, coverage report
- [ ] Frontend CI: eslint, tsc, vitest, build
- [ ] Docker images built and pushed to container registry
- [ ] Kustomize manifests for dev and prod overlays
- [ ] ArgoCD Application manifest for automated sync
- [ ] PR code review via GitHub Copilot (auto-review enabled)

**Stories**:

1. Create GitHub Actions CI workflow (backend)
2. Create GitHub Actions CI workflow (frontend)
3. Create GitHub Actions CD workflow (build + push images)
4. Write Dockerfiles for backend and frontend (multi-stage)
5. Create Kustomize base manifests (deployments, services, ingress)
6. Create Kustomize overlays (dev, prod)
7. Create ArgoCD Application manifest
8. Configure GitHub branch protection and Copilot review

---

## Epic 9: Documentation & Deliverables

**Goal**: All hackathon-required deliverables plus operational docs.

**Acceptance Criteria**:

- [ ] Architecture diagram (visual, not ASCII)
- [ ] Risk-scoring explanation document
- [ ] Responsible AI considerations document
- [ ] 5-minute "Path to CMS Pilot" briefing
- [ ] AI tool usage disclosure
- [ ] Open-source library disclosure
- [ ] README with quickstart (docker-compose up)
- [ ] End-to-end demo script for judges

**Stories**:

1. Generate architecture diagram
2. Write risk-scoring methodology document
3. Write responsible AI considerations
4. Draft "Path to CMS Pilot" briefing
5. Create AI tool usage and open-source disclosures
6. Update README with final quickstart
7. Write demo script with talking points

---

## Epic Execution Order

```
Epic 1: Data Foundation         ━━━━━━━━━━ (Days 1-3)
Epic 2: Scoring Engine          ━━━━━━━━ (Days 2-4, overlaps with E1)
Epic 3: Evidence Graph          ━━━━━━ (Days 3-5)
Epic 4: AI Reasoning Layer      ━━━━━━━━ (Days 4-6)
Epic 5: API Layer               ━━━━━━━━ (Days 4-7, parallel with E4)
Epic 6: Claims Simulator UI     ━━━━━━━━━━ (Days 5-9)
Epic 7: Chat Sidebar            ━━━━━━━━ (Days 7-9, after E6 shell exists)
Epic 8: CI/CD Pipeline          ━━━━ (Days 1-2, then maintenance)
Epic 9: Docs & Deliverables     ━━━━━━ (Days 9-11)
```

**Critical path**: E1 → E2 → E5 → E6 (data → scoring → API → UI)
**Parallel track**: E3 + E4 can build alongside E2 and E5
**Start early**: E8 (CI/CD) should be first so all subsequent work flows through it
