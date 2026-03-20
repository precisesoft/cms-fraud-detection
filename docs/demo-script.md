# Demo Script — CMS Proactive Program Integrity

> 5-7 minute demo for judges. March 27, 2026 — Reston, Virginia.

## Opening (30s)

"CMS loses over $60 billion a year to improper payments, and most detection happens after the money is already out the door. We built a system that catches suspicious billing patterns before they scale — and we validated it: **our scoring detected 91% of eventually-revoked providers from billing patterns alone**, before CMS acted on revocation."

## 1. Dashboard Overview (60s)

**Show**: `https://argus.precise-lab.com`

- Point out the three risk bands: stable, review, high-risk
- Highlight total providers (10K+) and cases scored
- Show the geographic heatmap — clusters of high-risk activity in FL, TX, CA
- "Every number you see here traces back to specific public CMS data with full provenance"

## 2. Provider Deep-Dive — A High-Risk Case (90s)

**Navigate**: Click a high-risk provider from the dashboard

Walk through the provider detail page:

1. **Risk score gauge** — "This provider scores 78/100. Here's exactly why."
2. **Signals panel** — "We show both risk AND legitimacy signals. This provider has:"
   - Service volume 5.2 standard deviations above peers (risk)
   - Revocation on record (risk)
   - But also: currently enrolled, accepting Medicare assignment (legitimacy)
3. **Peer comparison chart** — "We don't just flag outliers — we show you exactly how far they deviate from specialty peers"
4. **Evidence graph** — "The Neo4j graph connects this provider to their cases, signals, peer groups, and data sources. Every edge is traceable."
5. **Network risk** — "This provider shares a zip code with 3 other flagged providers — a common pattern in fraud rings"

**Key line**: "An investigator sees the evidence, not a black box score. They decide what to do next."

## 3. Claims Simulator (60s)

**Navigate**: Simulate page

- Enter a hypothetical claim: NPI, procedure code, charge amount
- Submit and watch the real-time scoring response
- "This simulates what pre-payment screening would look like. Before the payment goes out, the system scores the claim, explains the risk, and generates an AI narrative."
- Show the AI-generated narrative — "Claude reads the structured signals and writes a plain-English investigation brief that a non-technical reviewer can understand"

## 4. AI Chat Interface (60s)

**Navigate**: Open the chat sidebar

Ask a few natural-language questions:

- "How many providers are high risk?" → Shows SQL + result
- "Which specialties have the most outlier billing?" → Table result
- "Show me revoked providers in Florida" → Specific data

"This is text-to-SQL powered by Claude. Analysts can ask questions in plain English instead of writing SQL. Every generated query is validated — no mutations, no injection, read-only."

## 5. Validation Story (60s)

**This is the closer. Deliver this with confidence.**

"We didn't just build a scoring system — we validated it. We took all 335 revoked providers in our dataset, removed the revocation flag, and re-scored them using only behavioral signals: peer z-scores, enrollment status, billing patterns."

"**91% were still flagged.** Billing abuse cases: 94%. Felony-related revocations: 100%. The baseline for non-revoked providers? Only 51%. Our behavioral signals have real discriminative power."

"The scoring engine uses 14 explainable signals across 4 categories. We also trained an isolation forest anomaly detection model that correlates with our rule-based scores and independently identifies the same high-risk providers."

## 6. Responsible AI (30s)

- "We built a fairness dashboard that measures statistical parity and disparate impact across states and specialties"
- "We also run the analysis in revocation-blind mode to ensure our behavioral signals alone don't create disparate impact"
- "All data is public CMS data — no PHI, no PII. AI tool usage is fully disclosed."

## 7. Path to CMS Pilot (30s)

"This system runs on AWS EKS with ArgoCD, Terraform, and a full CI/CD pipeline. It's cloud-native and production-ready. The path to pilot:"

1. **Phase 1**: Connect to CMS claims feeds instead of public aggregates
2. **Phase 2**: Add claim-line scoring for true pre-payment screening
3. **Phase 3**: Integrate with existing CMS investigation workflows

"The architecture, the validation, and the explainability are already here. What changes is the data resolution."

## Backup Slides (if asked)

- Architecture diagram: EKS deployment, CI/CD pipeline, data flow
- Signal taxonomy: all 14 signals with weights and thresholds
- Anomaly model: feature importance, correlation with rule scores
- Load test results: throughput under concurrent users
- Full retrospective validation breakdown by revocation reason

## Key Numbers to Remember

| Metric                        | Value                            |
| ----------------------------- | -------------------------------- |
| Detection rate (blind)        | 91.3%                            |
| Billing abuse detection       | 94%                              |
| Felony detection              | 100%                             |
| Non-revoked baseline flagging | 51.4%                            |
| Risk signals                  | 6 risk + 7 legitimacy = 14 total |
| Providers scored              | 10,282                           |
| Cases scored                  | 13,225                           |
| Public data sources           | 4 active + 2 reference           |

## Don'ts

- Don't say "AI" when describing the scoring engine — say "explainable risk scoring"
- Don't claim "national scale" — say "designed for scale, validated on 10K providers"
- Don't spend time on infrastructure — judges care about the insight, not the K8s cluster
- Don't rush the validation story — it's the strongest evidence you have
