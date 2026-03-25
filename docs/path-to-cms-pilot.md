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

1. **Live Payment Monitor** — Claims stream in via SSE, scored in real time (<50ms), displayed on a live US map with pulsing risk dots. Click a flagged claim to investigate.
2. **Dashboard** — Aggregate view: total providers scored, risk distribution, geographic heatmap showing state-level flagging patterns
3. **Provider drill-down** — Pick a flagged provider, see the signal breakdown: which signals fired, how many points each contributed, peer baseline comparisons
4. **On-the-fly scoring** — Submit a new claim, watch the scoring engine extract signals and compute risk + legitimacy in real time
5. **AI-assisted investigation** — Ask a natural language question ("Which providers in California have the highest charge ratios?"), get a data-backed answer with charts
6. **Fairness dashboard** — Show flagging rate parity across states and specialties

## Technical Architecture (60 seconds)

| Layer    | Technology                                   | Why                                               |
| -------- | -------------------------------------------- | ------------------------------------------------- |
| API      | FastAPI (Python 3.12)                        | Async, auto-documented, 20 route modules          |
| Scoring  | Deterministic rule engine + Isolation Forest | Auditable, reproducible, anomaly detection        |
| Data     | PostgreSQL 16 + Neo4j 5                      | Relational queries + relationship traversal       |
| AI       | AWS Bedrock (Claude Sonnet 4.6 + Haiku 4.5)  | **FedRAMP High authorized**, GovCloud-ready       |
| Frontend | Vite + React 19 + Tailwind v4                | 15-page SPA, responsive, modern React             |
| Infra    | AWS EKS + Istio + ArgoCD                     | Container-native, horizontally scalable           |
| CI/CD    | GitHub Actions (8-stage pipeline)            | Gate + security + quality + build + scan + deploy |

**Data sources** — 19GB of real, public CMS data:

- Medicare Physician & Other Practitioners (2022) — 9.66M service lines
- Medicare Fee-for-Service Public Provider Enrollment (2025)
- CMS Provider Revocation File (2026)

## What Changes for a CMS Pilot (60 seconds)

The system is designed so the **MVP maps directly to a pilot** with minimal rework:

### Already Production-Ready Today

- **Validated**: 91% of eventually-revoked providers detected from billing patterns alone (94% for billing abuse, 100% for felony-related revocations)
- Cloud-native containerized architecture (EKS + ArgoCD + Terraform)
- FedRAMP-authorized AI (Bedrock = FedRAMP High)
- Fully explainable — every score has complete provenance (13 named signals)
- 99% backend / 98% frontend test coverage
- 8-stage CI/CD pipeline with 6 security tools and CycloneDX SBOMs on every build
- No PHI required — works on public data today
- **RBAC + audit trail live** — JWT authentication, immutable `audit_log` recording every analyst action and AI query with timestamps and source IPs
- **Investigation workflow live** — case queue with approve/flag/deny/escalate actions, priority-based triage
- **Real-time scoring live** — SSE-streamed Live Payment Monitor scores claims in under 50ms
- **ML anomaly detection live** — Isolation Forest with per-provider feature importance (leave-one-out, <100ms)
- **Fraud ring clustering live** — recursive CTE detects connected provider networks via shared zip/org
- **Data management live** — upload CSVs, trigger recalibration, retrain ML models via admin endpoints

## Integration with Existing CMS Systems

CMS already operates the **Fraud Prevention System (FPS)**, a real-time pre-payment scoring engine that processes approximately 15 million Medicare Fee-for-Service claim lines per day (operated by Peraton under a CMS contract). FPS generates provider risk, priority, and actionability scores that feed investigation queues for **Unified Program Integrity Contractors (UPICs)** — the five regional contractors who replaced ZPICs in 2016–2019 and are required by CMS to derive 45% of new investigations from FPS leads. In 2025, CMS also launched the Fraud Detection Operation Center (FDOC) using FPS outputs.

Argus is designed to be **complementary to FPS, not a replacement**:

- **FPS** screens claims at the transaction level — it scores individual claim lines pre-payment.
- **Argus** profiles providers at the behavioral level — it builds an explainable evidence picture across a provider's full billing history, peer group, enrollment status, and sanctions record.

The integration point is straightforward: FPS-flagged NPIs become investigation triggers in Argus. A UPIC investigator receives an FPS lead (a risk score on a claim), then uses Argus to answer the harder question — _why does this provider's overall billing pattern look suspicious, and what evidence supports that conclusion?_

This directly addresses a documented gap. GAO Report GAO-17-710 criticized FPS for lacking defined effectiveness measures and transparency in how risk scores are generated. Argus addresses this with 13 named signals, each with a threshold, a weight, and a data-source citation — the kind of provenance that supports an administrative action or law enforcement referral.

### Pilot Phase (6 months)

Several capabilities that were originally scoped for pilot have already been built in the MVP (marked **Done**). The remaining pilot work focuses on connecting to real CMS data and integrating with existing systems.

| Change                           | Status   | What It Takes                                                                                                                                                          |
| -------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Connect real CMS data**        | Pilot    | Replace public datasets with internal claim feeds. Same schema, same scoring engine — only the data source changes.                                                    |
| **FedRAMP compliance**           | Pilot    | Deploy to AWS GovCloud. Bedrock is already FedRAMP High. Standard ATO process for the application layer.                                                               |
| **RBAC + audit trail**           | **Done** | JWT-backed RBAC is live. Immutable `audit_log` records every analyst action and AI query with timestamps and source IPs. `/api/audit` supports filtered retrieval.     |
| **Reviewer workflow**            | **Done** | Case queue with approve/flag/deny/escalate actions, priority-based triage, investigation detail with AI narratives — all live at `/investigations`.                    |
| **Real-time scoring**            | **Done** | SSE-streamed Live Payment Monitor scores claims in under 50ms. Connecting to a live CMS claims feed (SQS/Kafka) is a configuration change, not an architecture change. |
| **ML anomaly detection**         | **Done** | Isolation Forest (200 estimators, 49 features) with per-provider feature importance. Score Agreement indicator compares rule-based and ML scores.                      |
| **Data management pipeline**     | **Done** | Admin endpoints for CSV upload, recalibration, and ML model retraining. Source version tracking with freshness monitoring.                                             |
| **Multi-year temporal analysis** | Pilot    | Connect 3-5 years of Part B data to detect year-over-year growth, billing acceleration, and code-mix shifts. Signal taxonomy supports these additions.                 |
| **Feedback loop**                | Pilot    | Reviewer decisions (true positive, false positive) feed back into signal weight tuning. Audit trail already captures the data needed.                                  |
| **FPS lead ingestion**           | Pilot    | Ingest provider NPIs flagged by FPS as investigation triggers. Configuration change, not architecture change.                                                          |
| **UCM integration**              | Pilot    | Push Argus evidence packages to CMS Unified Case Management system for UPIC workflow.                                                                                  |

### Production Scale (12 months)

- **National scale** — All Medicare claims, multi-region high availability
- **Multi-program** — Extend to Medicaid, Part D, DME
- **ML enhancement** — Supervised models trained on reviewer feedback data
- **System integration** — Connect to UPIC systems, MPI, existing CMS tools
- **508 compliance** — Full accessibility audit ([see Accessibility Report](./accessibility-report.md))

### Audit & Accountability

Argus now captures a durable audit trail for the investigator workflow:

- **Case actions** — every approve, flag, deny, or escalate action is stored with the case ID, NPI, analyst username, notes, timestamp, and source IP.
- **AI query activity** — each natural-language text-to-SQL request is logged with the requesting analyst, generated SQL, timestamp, and source IP, without persisting result sets.
- **Review support** — `/api/audit` supports filtered retrieval by analyst, entity, and event type so supervisors can reconstruct what happened during an investigation.

This gives CMS a straightforward accountability layer for QA reviews, incident response, and downstream case-management integration.

## The Ask (30 seconds)

We're not asking CMS to adopt a black-box model. We're offering a **transparent, auditable, FedRAMP-ready decision-support tool** that:

1. Works today on public data
2. Scales to internal data with no architecture changes
3. Explains every conclusion to the investigator
4. Monitors its own fairness continuously
5. Runs on infrastructure CMS already trusts (AWS GovCloud)

**The path from this hackathon to a CMS pilot is a data connection change, not a rebuild.**
