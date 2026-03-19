# Argus — User Personas & Investigation Journeys

## The Problem

CMS processes **4.6 million Medicare claims per day**. Fewer than 1% of providers account for the majority of improper payments, but finding them in real-time — before payment — is like finding a needle in a haystack while the conveyor belt is running.

Argus sits at the payment gate. It scores every claim against peer baselines, flags anomalies, and explains its reasoning — so human reviewers can make fast, confident decisions.

---

## Personas

### 1. Claims Processing Analyst — "Sarah"

**Role**: GS-9 Program Analyst, CMS Center for Program Integrity

**Day-to-day**: Reviews 200+ claims per day from the flagged queue. Makes binary decisions: pay or flag for investigation. Works under time pressure — the payment cycle doesn't wait.

**Goals**:

- Process flagged claims quickly and accurately
- Minimize false positives (flagging legitimate providers wastes investigator time)
- Never miss a high-risk claim (false negatives cost taxpayers money)

**Pain points**:

- Current tools show raw data with no context — she has to manually compare charges against fee schedules
- No explanation of _why_ a claim is suspicious — just a number
- Switching between 4 different systems to get the full picture

**What Argus gives her**:

- Prioritized inbox sorted by risk score
- One-click verdict: APPROVE / REVIEW / DENY with confidence level
- Plain-English explanation: "This provider charges 4.2x the peer average for CPT 99215 in Florida"
- Peer comparison chart inline — no system-switching

**Success metric**: Processes 200+ claims/day with <5% false positive escalation rate

**Key screens**: Claims Inbox (`/inbox`), Claim Simulation (`/simulate`)

---

### 2. Special Investigations Unit (SIU) Investigator — "Marcus"

**Role**: GS-12 Fraud Investigator, Zone Program Integrity Contractor (ZPIC)

**Day-to-day**: Receives escalated cases from analysts. Builds evidence packages for administrative action or law enforcement referral. Each case takes 2-8 hours with current tools.

**Goals**:

- Build airtight evidence packages that hold up under appeal
- Identify connected providers (rings, shell companies, shared addresses)
- Understand the full scope of a provider's billing anomalies

**Pain points**:

- Evidence is scattered across multiple databases — Medicare claims, enrollment, revocation lists
- No way to visualize provider relationships without manual diagramming
- Writing case narratives from scratch every time

**What Argus gives him**:

- Unified investigation view: profile + peers + signals + graph + narrative on one screen
- Evidence graph showing provider connections (shared addresses, referral patterns, common billing codes)
- AI-generated case narrative as a starting point
- Natural language queries: "Show me all providers at this address billing J3490"

**Success metric**: Builds a complete evidence package in <30 minutes (vs. 4 hours today)

**Key screens**: Provider Detail (`/providers/[npi]`), Evidence Graph, AI Chat Sidebar

---

### 3. Program Integrity Director — "Director Chen"

**Role**: GS-15 Director, Division of Program Integrity

**Day-to-day**: Oversees the fraud prevention program for a CMS region. Reports to CMS leadership on program effectiveness. Allocates investigator resources.

**Goals**:

- Identify systemic fraud patterns (geographic hotspots, emerging scheme types)
- Ensure the algorithm flags fairly across demographics and specialties
- Demonstrate program ROI to CMS leadership

**Pain points**:

- No real-time visibility into what the team is catching
- Fairness is assessed retroactively, if at all
- Weekly reports are manually assembled from spreadsheets

**What Argus gives her**:

- Executive dashboard with real-time risk distribution
- Geographic heatmap showing where fraud concentrates
- Fairness dashboard with statistical parity and disparate impact metrics
- Trend lines showing program effectiveness over time

**Success metric**: Identifies systemic fraud patterns across states/specialties; maintains disparate impact ratio ≥ 0.8

**Key screens**: Dashboard (`/`), Heatmap (`/heatmap`), Fairness (`/fairness`)

---

### 4. Medical Director — "Dr. Patel"

**Role**: Clinical reviewer, contracted medical director for CMS MAC

**Day-to-day**: Reviews flagged cases for clinical validity. Determines whether billing patterns are medically justified or represent upcoding/unbundling/phantom billing.

**Goals**:

- Quickly assess whether a flagged billing pattern has clinical justification
- Identify upcoding (billing higher-level codes than warranted)
- Distinguish between high-volume legitimate practice and fraud

**Pain points**:

- Sees a risk score but doesn't understand the clinical context
- Has to look up HCPCS codes and fee schedules separately
- No peer comparison specific to the provider's specialty

**What Argus gives him**:

- Peer comparison by specialty: "This cardiologist bills 3x more 93306 (echocardiograms) than peers in the same state"
- HCPCS code descriptions and typical utilization patterns inline
- Signal explanations with clinical context
- Services-per-beneficiary metric: "47 services per patient vs. peer average of 12"

**Success metric**: Correctly validates or dismisses clinical flags with documented reasoning

**Key screens**: Provider Detail (`/providers/[npi]`), Peer Chart, Signals

---

## User Journeys

### Journey 1: Analyst Daily Triage (Primary Demo Flow)

This is the "hero" journey for the hackathon demo. It shows Argus's core value proposition: real-time claim scoring with explainable verdicts.

```
1. LOGIN
   Sarah opens Argus. Her inbox shows: "47 claims need review | 12 high risk | 35 review"

2. SCAN INBOX
   Claims sorted by risk score (descending). Top claim:
   NPI 1588440960 | GP Diagnostics | Miami, FL | $482K est. payment | Risk: 71 | HIGH RISK

3. CLICK TOP CLAIM → INVESTIGATION VIEW
   - Risk gauge: 71/100 (red zone)
   - Verdict: DENY — confidence HIGH
   - Signals:
     ⚠ Submitted charge 4.2x peer average (z-score: 3.8)
     ⚠ Single HCPCS code accounts for 100% of billing (HHI: 1.0)
     ⚠ Provider revoked from Medicare in 2026
     ✓ Enrolled in Medicare 2025

4. VIEW PEER COMPARISON
   Bar chart: GP Diagnostics bills $482K for J3490 vs peer average $45K
   "This provider is in the 99.8th percentile for this code in Florida"

5. TAKE ACTION
   Sarah clicks "Deny & Escalate" → adds note: "Single-code lab billing 10x peers, revoked provider"
   → Case moves to Marcus's SIU queue

6. NEXT CLAIM
   Sarah returns to inbox. 46 remaining. Time elapsed: 90 seconds.
```

### Journey 2: SIU Investigation Deep-Dive

```
1. RECEIVE ESCALATION
   Marcus sees Sarah's escalation in his queue with her note.

2. OPEN INVESTIGATION VIEW
   Full provider profile: GP Diagnostics, Clinical Laboratory, Miami FL
   - 1 HCPCS code (J3490), 8 service lines, $482K estimated payment
   - Revoked 2026, reason: "Pattern of abusive billing"

3. EXAMINE EVIDENCE GRAPH
   Neo4j visualization shows:
   - GP Diagnostics → 8 cases → all flagged high-risk
   - Connected to 2 other providers at same Miami address
   - All 3 providers bill the same code (J3490)

4. ASK AI (future — chat sidebar)
   "Show me all providers at 1234 Biscayne Blvd billing J3490"
   → AI returns 3 providers, all flagged, combined $1.2M

5. EXPORT CASE
   Marcus generates a case summary with all evidence for law enforcement referral.
```

### Journey 3: Director Weekly Review

```
1. OPEN DASHBOARD
   - 10,282 providers monitored
   - 153 high-risk (1.5%), 5,226 under review (50.8%), 4,903 stable
   - Top 10 highest-risk providers listed

2. CHECK HEATMAP
   Florida lights up red — 23 flagged providers, highest concentration
   Click FL → drills to provider list filtered by state

3. CHECK FAIRNESS
   - Statistical parity diff: 4.2% (PASS — below 10% threshold)
   - Disparate impact ratio: 0.87 (PASS — above 0.8 four-fifths rule)
   - No specialty cohort is an outlier

4. REVIEW TRENDS (future)
   Weekly trend line shows flagging rate stable at 1.5%
   No emerging fraud patterns detected this week

5. GENERATE REPORT
   Director exports weekly summary for CMS leadership briefing
```

---

## Screen-to-Persona Mapping

| Screen                               | Sarah (Analyst) | Marcus (SIU) | Director Chen |  Dr. Patel  |
| ------------------------------------ | :-------------: | :----------: | :-----------: | :---------: |
| Claims Inbox (`/inbox`)              |   **Primary**   |  Secondary   |       —       |      —      |
| Claim Simulation (`/simulate`)       |   **Primary**   |      —       |       —       |      —      |
| Provider Detail (`/providers/[npi]`) |    Secondary    | **Primary**  |       —       | **Primary** |
| Evidence Graph                       |        —        | **Primary**  |       —       |      —      |
| Peer Chart                           |    Reference    | **Primary**  |       —       | **Primary** |
| Dashboard (`/`)                      |        —        |      —       |  **Primary**  |      —      |
| Heatmap (`/heatmap`)                 |        —        |      —       |  **Primary**  |      —      |
| Fairness (`/fairness`)               |        —        |      —       |  **Primary**  |      —      |
| AI Chat (future)                     |        —        | **Primary**  |       —       |      —      |

---

## What Already Exists vs. What's Needed

| Feature                              | Status               | Serves                |
| ------------------------------------ | -------------------- | --------------------- |
| Dashboard with risk distribution     | ✅ Built             | Director              |
| Provider search + list               | ✅ Built             | All                   |
| Provider detail with signals         | ✅ Built             | SIU, Medical Director |
| Peer comparison chart                | ✅ Built             | SIU, Medical Director |
| Evidence graph (Neo4j)               | ✅ Built             | SIU                   |
| Risk gauge                           | ✅ Built             | All                   |
| Heatmap                              | ✅ Built             | Director              |
| Fairness dashboard                   | ✅ Built             | Director              |
| Scan button (provider scoring)       | ✅ Built             | Analyst               |
| **Claim simulation form**            | 🔨 Next              | **Analyst**           |
| **Scoring result with verdict**      | 🔨 Next              | **Analyst**           |
| **Claims inbox**                     | 🔨 Next              | **Analyst**           |
| **Case actions (approve/flag/deny)** | 🔨 Next              | **Analyst, SIU**      |
| **AI narrative**                     | 🔜 Blocked on Epic 4 | **SIU, Analyst**      |
| **AI chat sidebar**                  | 🔜 Blocked on Epic 4 | **SIU**               |
