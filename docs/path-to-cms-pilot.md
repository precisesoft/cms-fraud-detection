# Path to CMS Pilot

> 5-minute briefing for hackathon judges.

## The Problem (30 seconds)

CMS loses an estimated **$60 billion annually** to improper payments across Medicare and Medicaid. The current process is fundamentally reactive — suspicious billing patterns are identified only after money has gone out the door, forcing CMS into a costly "pay-and-chase" cycle.

Three operational gaps make this worse:

1. High-risk provider behavior continues too long before review
2. Investigators lack clear, evidence-backed explanations for why a pattern is suspicious
3. Context is fragmented across billing, enrollment, sanctions, and financial data

## Our Solution (60 seconds)

We built an **explainable, proactive provider risk detection system** that turns fragmented public CMS data into evidence-backed risk cases.

**What makes it different:**

- **Dual scoring** — Every provider-service case gets both a risk score and a legitimacy score. High volume alone doesn't trigger a flag if the provider has strong enrollment, participation, and peer-aligned indicators.
- **13 named signals** — Every point in every score traces to a specific signal with a name, a threshold, and a data source. No black boxes.
- **Peer comparison** — Providers are compared against their specialty peers (same provider type + HCPCS code, minimum 25 providers). A cardiologist is compared to cardiologists, not family practitioners.
- **Fairness monitoring** — Built-in analysis of flagging rates across geography and specialty, with statistical parity and disparate impact metrics.

## Live Demo Highlights (90 seconds)

1. **Dashboard** — Aggregate view: total providers scored, risk distribution, geographic heatmap showing state-level flagging patterns
2. **Provider drill-down** — Pick a flagged provider, see the signal breakdown: which signals fired, how many points each contributed, peer baseline comparisons
3. **On-the-fly scoring** — Submit a new claim, watch the scoring engine extract signals and compute risk + legitimacy in real time
4. **AI-assisted investigation** — Ask a natural language question ("Which providers in California have the highest charge ratios?"), get a data-backed answer with charts
5. **Fairness dashboard** — Show flagging rate parity across states and specialties

## Technical Architecture (60 seconds)

| Layer    | Technology                | Why                                         |
| -------- | ------------------------- | ------------------------------------------- |
| API      | FastAPI (Python 3.12)     | Async, auto-documented, 8 live endpoints    |
| Scoring  | Deterministic rule engine | Auditable, reproducible, no model drift     |
| Data     | PostgreSQL 16 + Neo4j 5   | Relational queries + relationship traversal |
| AI       | AWS Bedrock (Claude)      | **FedRAMP High authorized**, GovCloud-ready |
| Frontend | Next.js 15 + shadcn/ui    | Modern, accessible, responsive              |
| Infra    | Kubernetes (k3s)          | Container-native, horizontally scalable     |
| CI/CD    | GitHub Actions            | 7 automated checks on every PR              |

**Data sources** — 19GB of real, public CMS data:

- Medicare Physician & Other Practitioners (2022) — 9.66M service lines
- Medicare Fee-for-Service Public Provider Enrollment (2025)
- CMS Provider Revocation File (2026)

## What Changes for a CMS Pilot (60 seconds)

The system is designed so the **MVP maps directly to a pilot** with minimal rework:

### Already Production-Ready Today

- Cloud-native containerized architecture
- FedRAMP-authorized AI (Bedrock = FedRAMP High)
- Fully explainable — every score has complete provenance
- No PHI required — works on public data today

### Pilot Phase (6 months)

| Change                    | What It Takes                                                                                                       |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| **Connect real CMS data** | Replace public datasets with internal claim feeds. Same schema, same scoring engine — only the data source changes. |
| **FedRAMP compliance**    | Deploy to AWS GovCloud. Bedrock is already FedRAMP High. Standard ATO process for the application layer.            |
| **RBAC + audit trail**    | Add role-based access and action logging. Framework is ready (FastAPI middleware).                                  |
| **Reviewer workflow**     | Add case assignment, disposition tracking, and status management.                                                   |
| **Real-time scoring**     | Add SQS/Kafka pipeline for pre-payment claim scoring as claims arrive.                                              |
| **Feedback loop**         | Reviewer decisions (true positive, false positive) feed back into signal weight tuning.                             |

### Production Scale (12 months)

- **National scale** — All Medicare claims, multi-region high availability
- **Multi-program** — Extend to Medicaid, Part D, DME
- **ML enhancement** — Supervised models trained on reviewer feedback data
- **System integration** — Connect to UPIC systems, MPI, existing CMS tools
- **508 compliance** — Full accessibility audit

## The Ask (30 seconds)

We're not asking CMS to adopt a black-box model. We're offering a **transparent, auditable, FedRAMP-ready decision-support tool** that:

1. Works today on public data
2. Scales to internal data with no architecture changes
3. Explains every conclusion to the investigator
4. Monitors its own fairness continuously
5. Runs on infrastructure CMS already trusts (AWS GovCloud)

**The path from this hackathon to a CMS pilot is a data connection change, not a rebuild.**
