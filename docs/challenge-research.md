# CMS Proactive Program Integrity — Challenge Research Brief

> Comprehensive background for the government AI hackathon challenge: shifting Medicare/Medicaid
> fraud detection from reactive "pay-and-chase" to proactive pre-payment interception.

tags: #research #cms #fraud-detection #healthcare #ai #hackathon
STATUS: active
created: 2026-03-11
updated: 2026-03-12
origin: Government AI Hackathon — CMS Proactive Program Integrity Challenge

---

## Overview

This document provides the deep background needed to build a competitive hackathon submission for the
CMS Proactive Program Integrity challenge. It covers the problem domain, fraud typology, existing
detection infrastructure, AI/ML approaches from academic literature, judging criteria interpretation,
and the shape of a winning submission. Read this before writing a single line of code.

## Official Hackathon Envelope (March 2026)

The public hackathon materials and the March 11 orientation recap tighten the scope beyond a generic
fraud-detection project. The team needs a demo-ready MVP that:

- Follows the organizer timeline: team, use-case, and environment lock by March 11, 2026,
  solutioning sprint from March 12-March 25, likely technical review on March 26, and demo day on
  March 27
- Uses teams of 2-5 members with at least one designated team lead
- Uses public datasets only and does not use PHI
- Detects anomalous provider behavior and produces an explainable provider risk score
- Groups providers by specialty, geography, and service category for peer comparison
- Shows why a provider was flagged, including top contributing factors
- Includes a fairness review across geography or specialty
- Provides a simple UI with risk heatmap, drill-down metrics, peer comparison, and time-series views

The orientation recap also clarified the operating rules:

- Only original work created during the hackathon is eligible
- Teams retain ownership of their work
- Open-source tools and libraries must be disclosed
- AI tools must be disclosed and their output reviewed by the team

The official deliverables also matter as much as the model:

- Working prototype, live or recorded
- Architecture diagram
- Risk-scoring methodology explanation
- Responsible AI considerations
- 5-minute "Path to CMS Pilot" briefing

This means the winning strategy is not "best fraud model in the abstract." The winning strategy is a
mission-ready decision-support story that a CMS reviewer could trust, understand, and plausibly pilot.

---

## 1. Problem Domain

### 1.1 What is CMS?

The Centers for Medicare & Medicaid Services (CMS) is a federal agency within the U.S. Department of
Health and Human Services (HHS). It is the single largest health insurer in the United States and one
of the largest purchasers of goods and services in the world. CMS administers:

- **Medicare**: Federal health insurance for people 65 and older, certain younger people with
  disabilities, and people with End-Stage Renal Disease (ESRD). Structured in four parts:
  - Part A — Hospital insurance (inpatient, skilled nursing, hospice)
  - Part B — Medical insurance (outpatient services, physician visits, durable medical equipment)
  - Part C — Medicare Advantage (private plan alternative to A+B)
  - Part D — Prescription drug coverage
- **Medicaid**: Joint federal-state program providing health coverage to low-income individuals,
  families, children, pregnant women, elderly, and people with disabilities. Each state administers
  its own Medicaid program within federal guidelines.
- **CHIP (Children's Health Insurance Program)**: Low-cost health coverage for children in families
  that earn too much to qualify for Medicaid.
- **Marketplace**: Health insurance exchanges created by the Affordable Care Act.

Together, these programs cover approximately 150 million Americans — nearly half the country.

### 1.2 Scale of Spending

CMS total expenditure exceeds **$1 trillion annually** and is growing:

| Program  | Approximate Annual Spend | Beneficiaries |
| -------- | ------------------------ | ------------- |
| Medicare | ~$900B (2023)            | ~67 million   |
| Medicaid | ~$616B (2023, fed+state) | ~94 million   |
| CHIP     | ~$21B                    | ~7 million    |

Medicare alone processes approximately **1.3 billion claims per year** from over 1.5 million enrolled
providers. This volume makes manual review impossible at scale.

### 1.3 The Improper Payment Problem

The HHS Office of Inspector General (OIG) estimates that CMS makes **$60–100 billion in improper
payments annually**. The official HHS Improper Payments report (published each year) tracks this as
an "improper payment rate" — for Medicare Fee-for-Service it has historically ranged from 6–8% of
total outlays. Not all improper payments are fraud; they include:

- **Fraud**: Intentional deceptive acts to obtain payment (criminal)
- **Waste**: Overutilization or misuse of resources without criminal intent
- **Abuse**: Practices that are inconsistent with sound fiscal, business, or medical practices
- **Errors**: Clerical mistakes, documentation gaps, billing coding errors

True fraud (intentional) is estimated to represent 3–10% of total spending. Even at the low end,
this represents tens of billions of dollars per year.

### 1.4 The "Pay-and-Chase" Problem

The current dominant model is **reactive**: CMS pays claims first, then investigates suspicious
patterns after money has left the agency. This approach has several structural weaknesses:

1. **Recovery is difficult**: Once paid, clawbacks require administrative proceedings, litigation,
   or OIG enforcement actions. Recovery rates on identified fraud are often below 20 cents on the
   dollar.
2. **Detection lag**: Sophisticated fraud schemes often operate for months or years before detection.
   Systematic billing fraud by organized crime rings has run for 2–5 years before interception.
3. **Volume mismatch**: CMS processes millions of claims per week. Human investigators cannot keep
   pace without algorithmic assistance.
4. **Medicare Trust Fund pressure**: Medicare Part A is projected to face insolvency within a decade
   if spending trajectories do not change. Improper payments directly accelerate that timeline.

The hackathon challenge is to shift the paradigm to **pre-payment interception**: identify suspicious
claims before the payment check is cut, route them for human review, and prevent the loss rather than
chasing it after the fact.

---

## 2. Types of Medicare/Medicaid Fraud

### 2.1 Upcoding

**Definition**: Billing for a more expensive service code than was actually provided.

**Mechanics**: The Evaluation and Management (E&M) coding system for physician visits uses CPT codes
that reflect complexity:

- 99213: Established patient, low-moderate complexity, ~15–20 minutes
- 99214: Established patient, moderate complexity, ~25–30 minutes
- 99215: Established patient, high complexity, ~40–55 minutes

A provider seeing routine follow-up patients but billing all visits as 99215 is upcoding. The
overpayment per claim may be $50–150, but multiplied across thousands of claims it becomes
significant.

**Detection signal**: When a provider's distribution of E&M codes is heavily skewed toward high-level
codes (e.g., 95%+ 99215) compared to peers in the same specialty and geography, that is a statistical
anomaly warranting review.

**Real-world example**: A cardiologist in South Florida was found to have billed 99215 for 98% of
visits over three years. Peer average was ~30%. Recovery: $1.2M.

### 2.2 Phantom Billing

**Definition**: Billing for services, procedures, or supplies that were never provided to the patient.

**Mechanics**: The simplest form of fraud — claim submission for something that did not happen. Can
be perpetrated by:

- A provider billing for patient appointments that never occurred
- A home health agency billing for visits to patients who were actually hospitalized or deceased
- A DME company billing for equipment that was never ordered, delivered, or received

**Detection signal**:

- Billing on dates when the patient was known to be elsewhere (e.g., inpatient at a hospital)
- Billing for deceased patients (date of death cross-reference)
- Volume of services exceeding physically possible hours in a day (e.g., a solo practitioner
  billing for 30 one-hour therapy sessions in a single day)
- Patient-denied services when surveyed (beneficiary complaints)

**Real-world example**: A Houston-based home health agency billed $26M for skilled nursing visits
that home health aides (not nurses) or no one at all performed. The physical impossibility of the
visit volume was the detection trigger.

### 2.3 Unbundling

**Definition**: Billing separately for component services that are defined and reimbursed as a single
bundled procedure.

**Mechanics**: CMS uses the National Correct Coding Initiative (NCCI) to define Procedure-to-Procedure
(PTP) edits — pairs of codes that cannot be billed together. Unbundling violates these edits.

**Examples**:

- Billing separately for each component of a surgical procedure that has a single comprehensive code
- Billing 36415 (routine venipuncture) separately when it is already included in the lab panel code
- A hospital billing room-and-board, nursing, and pharmacy separately when all are bundled into a
  DRG (Diagnosis-Related Group) payment

**Detection signal**: Frequent billing of NCCI-paired codes from the same provider on the same date
of service for the same patient — especially when a single bundled code would cover both.

### 2.4 Duplicate Billing

**Definition**: Submitting the same claim more than once for the same service.

**Mechanics**: May be intentional fraud or unintentional error. Forms include:

- Submitting an identical claim twice (exact duplicate)
- Submitting the same service with minor variations (different date, modifier) to evade duplicate
  detection filters
- Billing both Medicare and Medicaid for the same service (cross-program billing)
- Billing both Medicare and a secondary insurer for the same service, collecting full reimbursement
  from both (coordination of benefits fraud)

**Detection signal**: Hash-based exact duplicate detection is straightforward. Fuzzy duplicate
detection (same provider, patient, code, similar date) requires more nuanced analysis.

### 2.5 Kickbacks

**Definition**: Payments made in exchange for patient referrals. Violates the Anti-Kickback Statute
(42 U.S.C. § 1320a-7b(b)) and the Stark Law.

**Mechanics**: Kickback schemes take many forms:

- A physician receives cash, gifts, or "consulting fees" from a lab in exchange for sending all
  bloodwork to that lab
- A home health agency pays physicians a per-referral fee (often disguised as marketing payments)
  for recommending their services
- A pharmaceutical company provides lavish meals, travel, or speaker fees to physicians who prescribe
  their drugs
- A DME company pays marketers per-beneficiary for obtaining physician orders

**Detection signal**: Kickbacks manifest as statistical patterns in referral networks:

- A physician who refers 90%+ of their home health patients to a single agency (vs. peers who
  distribute referrals)
- A single provider generating an anomalously high percentage of a specialty lab's revenue
- Graph-based analysis of referral relationships identifies clusters of tightly linked providers
  whose referral patterns deviate from geographic or specialty norms

**Real-world example**: The "One Stop Medical" scheme in Detroit — a network of physicians, DME
suppliers, and recruiters (beneficiary recruiters were paid per Medicare ID obtained) resulted in
$164M in fraudulent billing. The referral graph was a near-complete bipartite cluster.

### 2.6 Identity Theft / Beneficiary ID Theft

**Definition**: Using a Medicare beneficiary's identity without their knowledge to submit fraudulent
claims.

**Mechanics**: Organized fraud rings obtain Medicare beneficiary IDs (previously Social Security
Numbers, now Medicare Beneficiary Identifiers — MBIs, introduced 2018–2019 to reduce SSN exposure)
through:

- Data breaches (healthcare records)
- Phishing and social engineering of elderly beneficiaries
- Corrupt insiders at healthcare facilities
- Criminal marketplaces selling stolen health credentials

With a valid MBI, fraudsters can establish shell clinics, enroll as providers, and bill for services
never rendered to patients who may never know their identity was compromised.

**Detection signal**:

- A beneficiary's MBI appearing at geographically impossible locations within short time windows
- Services billed using an MBI for a deceased beneficiary
- A beneficiary's claims suddenly appearing from a new provider with no prior relationship
- High-volume billing by a newly enrolled provider concentrated on a small set of beneficiaries

### 2.7 Unnecessary Services (Over-Utilization)

**Definition**: Ordering or performing services that are not medically necessary.

**Mechanics**: Unlike phantom billing (service never happened), here the service genuinely occurred
but was clinically unjustified. Examples:

- A cardiologist who orders echocardiograms on every patient regardless of cardiac symptoms
- A pain management clinic that requires all patients to undergo urine drug testing at every visit
  (at $300–1,500 per test) regardless of clinical indication
- A home health agency certifying patients as homebound and requiring skilled services when they
  do not meet the clinical criteria
- Ordering genetic testing panels ($3,000–10,000 per panel) for patients with no personal or family
  history indicating risk

**Detection signal**: Services-per-patient ratios significantly above specialty peers; specific
procedure codes (like urine drug screens or genetic panels) comprising an anomalously high share
of a provider's billing mix.

### 2.8 Durable Medical Equipment (DME) Fraud

**Definition**: Billing for DME that was not delivered, not medically necessary, of a lower grade
than billed, or was supplied using fraudulent physician orders.

**Mechanics**: DME fraud is disproportionately represented in healthcare fraud enforcement because:

- DME suppliers are not required to be licensed clinicians (lower barrier to entry)
- Physician orders can be forged or obtained through kickbacks
- Patients may accept "free" equipment without realizing Medicare is being billed
- Certain DME categories (power wheelchairs, back braces, diabetic supplies) have historically been
  high-fraud areas

Common schemes:

- Billing for motorized wheelchairs for patients who are ambulatory
- "Rolling labs" — mobile units that visit senior centers offering "free" screenings, billing Medicare
  for medical equipment residents did not need
- Billing for diabetic testing supplies for non-diabetic patients
- Billing for CPAP machines without documented sleep studies

**Detection signal**: DME suppliers with geographic concentration of patients far from their physical
location; physician-to-DME referral relationships that are anomalously concentrated; billing for
high-value items (power chairs, orthotic braces) at rates far above peers in similar markets.

---

## 3. Existing CMS Fraud Detection Infrastructure

Understanding what already exists is essential — the hackathon solution must complement, not
duplicate, existing systems.

### 3.1 Fraud Prevention System (FPS)

**Introduced**: 2011, mandated by the Small Business Jobs Act of 2010.

**What it does**: The FPS is CMS's pre-payment automated screening system. It applies predictive
analytics and machine learning to Medicare fee-for-service claims before they are paid. The system
assigns risk scores to claims and providers, and can:

- **Deny claims** automatically (for known high-risk billing patterns)
- **Pay and review** (pay the claim, flag for post-payment audit)
- **Prepay review** (hold the claim pending additional documentation)

**Vendor**: Originally built by Northrop Grumman; the data analytics are supported by contractors
including IBM and Cotiviti.

**Track record**: By 2020, CMS reported the FPS had prevented, identified, or recovered over $5.7
billion in improper payments since inception.

**Limitations**:

- The FPS is primarily rules-based and statistical; it does not use deep learning
- It has been criticized for high false-positive rates that burden legitimate small practices
- The predictive models are not publicly documented (black box for external researchers)
- It focuses on individual claim anomalies; sophisticated network-based fraud can evade it

### 3.2 Unified Program Integrity Contractors (UPIC)

**What they are**: Regional contractors that CMS hires to investigate potential fraud, waste, and
abuse. As of the 2018 transition from ZPICs (Zone Program Integrity Contractors), there are five
UPICs covering different regions of the United States.

**What they do**:

- Conduct data analysis to identify aberrant billing patterns
- Perform site visits and medical record reviews
- Refer cases to law enforcement (OIG, DOJ, FBI)
- Issue payment suspensions and overpayment demands
- Coordinate with MACs (Medicare Administrative Contractors) on provider enrollment

**Limitations**: UPICs are the human investigation layer. They depend on algorithmic referrals from
FPS and other data systems to prioritize their workload. They are reactive by nature — they
investigate providers already flagged, rather than scanning the full provider universe proactively.

### 3.3 Medicare Administrative Contractors (MACs)

**What they are**: Private health insurers who process Medicare claims for specific geographic
jurisdictions. There are 12 MACs covering different regions.

**Relevance**: MACs are the first line of claims processing. They apply NCCI edits (for unbundling),
local coverage determinations (LCDs), and basic validity checks before passing claims to FPS.
They also handle provider enrollment and can flag enrollment anomalies.

### 3.4 Health Care Fraud Prevention and Enforcement Action Team (HEAT)

**Established**: 2009, joint initiative between HHS and DOJ.

**What it does**: HEAT coordinates enforcement actions across agencies (FBI, OIG, DEA, CMS, DOJ
Fraud Section). It created Medicare Fraud Strike Force units in high-fraud cities:

- Miami, FL
- Detroit, MI
- Los Angeles, CA
- Chicago, IL
- Dallas/Houston, TX
- Tampa, FL
- Baton Rouge, LA
- Brooklyn, NY
- New Orleans, LA

**Track record**: HEAT Strike Forces have charged thousands of individuals and recovered billions
of dollars since 2007. The geographic concentration is itself a signal — certain metropolitan areas
have systemic fraud ecosystems.

### 3.5 Senior Medicare Patrol (SMP)

**What it is**: A community-based education program that trains Medicare and Medicaid beneficiaries
to detect, report, and prevent fraud. Operated through Administracion for Community Living grants.

**Relevance to AI systems**: SMP generates beneficiary complaints and tip data, which represents
a valuable labeled signal for supervised learning. A patient reporting "I never received that
wheelchair" is a ground-truth fraud label.

### 3.6 List of Excluded Individuals and Entities (LEIE)

**What it is**: OIG's database of individuals and organizations excluded from participation in
federal health care programs due to fraud convictions, license revocations, or other integrity
violations. Updated monthly.

**Relevance for AI**: The LEIE is the primary source of **labeled fraud positives** for supervised
learning. Providers on the LEIE have been adjudicated as fraud — their historical claims represent
confirmed fraudulent billing patterns. This is the key training signal for supervised models.

**Limitation**: The LEIE represents only _caught_ fraud. Fraud not yet detected is by definition
absent from the label set — a fundamental challenge for any supervised approach.

---

## 4. AI/ML Approaches for Healthcare Fraud Detection

### 4.1 Supervised Learning Approaches

Supervised methods require labeled examples of fraud (positive class) and legitimate billing
(negative class). The LEIE and prior enforcement actions provide the positive labels.

**4.1.1 Gradient Boosted Trees (XGBoost / LightGBM)**

The workhorse of tabular fraud detection. Key properties:

- Handles mixed feature types (categorical CPT codes, numerical charge amounts, boolean flags)
- Built-in feature importance
- Robust to outliers and missing values
- Fast inference on CPU — critical for pre-payment latency requirements
- Directly compatible with SHAP for post-hoc explanation

Typical feature engineering for provider-level XGBoost:

- Service mix percentages by CPT category
- Charge-to-allowed ratio (provider's charges vs. Medicare allowed amount)
- Services per unique patient per year
- Percent of services on weekends/holidays
- Geographic distance from provider address to patient addresses (median, max)
- Provider tenure (months since enrollment)
- Peer-relative features: z-score of key metrics vs. specialty+geography peers

**4.1.2 Random Forest**

An ensemble of decision trees with good baseline performance and natural feature importance ranking.
Less accurate than XGBoost on tabular data in practice, but useful as a diversity signal in an
ensemble and more interpretable at the tree level.

**4.1.3 Neural Networks (Feedforward / Tabular Nets)**

TabNet (Arik & Pfister, 2021) is specifically designed for tabular data and provides instance-level
feature attribution through its sequential attention mechanism. For healthcare fraud:

- Can learn non-linear interactions that tree models miss
- Requires more labeled data to generalize well
- Attention weights provide a form of built-in explainability

**4.1.4 Key Challenge: Class Imbalance**

Fraud represents perhaps 1–5% of providers. Training a classifier on raw data produces models that
predict "legitimate" for everything and achieve 95%+ accuracy while catching nothing. Mitigation:

- SMOTE (Synthetic Minority Over-sampling Technique) for the training set
- Class-weight adjustment in the loss function
- Threshold tuning: optimize for precision-recall tradeoff, not accuracy
- Cost-sensitive learning: assign asymmetric misclassification costs

### 4.2 Unsupervised Anomaly Detection

When labels are sparse or unreliable, unsupervised methods detect providers whose behavior deviates
from the overall population without requiring prior fraud knowledge.

**4.2.1 Isolation Forest**

An ensemble of random trees that isolate anomalous points by requiring fewer splits than normal
points. Well-suited for healthcare fraud because:

- Efficient on high-dimensional provider feature vectors
- No assumption about the shape of the "normal" distribution
- Anomaly scores are continuous (0–1), enabling risk ranking rather than binary classification
- Fast training and inference even on millions of providers

In practice: build a feature vector for each provider (service mix, volume metrics, charge ratios)
and use Isolation Forest to score how anomalous that provider's profile is relative to the full
provider population.

**4.2.2 Local Outlier Factor (LOF)**

Identifies anomalies by comparing the local density of a point to its neighbors. Useful for
detecting providers who are unusual within their specialty peer group (local anomaly) even if
their absolute numbers look normal when compared to all providers.

**4.2.3 Autoencoders (Neural Network)**

A neural network trained to reconstruct its own input. The reconstruction error for each provider
becomes the anomaly score — a provider whose billing pattern is difficult to reconstruct (high
error) is anomalous.

Advantages:

- Can learn complex non-linear feature interactions
- Latent space representation can be visualized (dimensionality reduction)
- Well-suited for detecting novel fraud patterns not seen in training data

Disadvantages:

- Harder to explain: "high reconstruction error" is not interpretable to a human reviewer
- Requires careful architecture tuning and validation
- Can overfit on the dominant legitimate provider patterns

**4.2.4 DBSCAN for Cluster-Based Anomaly Detection**

Density-Based Spatial Clustering of Applications with Noise. Points that do not belong to any
cluster are labeled as noise — these are the anomalies. Useful for:

- Geographic clustering of patient addresses to detect patient-sharing rings
- Billing pattern clustering to identify groups of providers with suspiciously similar behavior
  (a marker of coordinated fraud rings)

### 4.3 Network / Graph Analysis

Healthcare fraud is often a **network phenomenon** — fraud rings involve multiple coordinated
actors. Graph-based analysis is uniquely suited to this:

**4.3.1 Provider Referral Networks**

Build a directed graph where:

- Nodes = providers (physicians, facilities, DME suppliers)
- Edges = referral relationships (provider A sends patients to provider B)
- Edge weights = volume of shared patients

Fraud signals from this graph:

- **High clustering coefficient**: A group of providers all refer to each other at high rates
  (closed referral loop, suggesting kickback arrangements)
- **Star topology**: A single physician or recruiter funneling patients to one DME supplier or
  clinic (concentration signal)
- **Short path length within a suspect cluster**: All members of a fraud ring are within 1–2 hops
  of each other in the referral graph

**4.3.2 Community Detection**

Algorithms like Louvain, Label Propagation, or Girvan-Newman can identify tightly knit provider
communities in the referral graph. Communities that are also geographic outliers (patients travel
long distances to reach providers within the community) warrant investigation.

**4.3.3 Graph Neural Networks (GNNs)**

GraphSAGE, Graph Attention Networks (GAT), and related architectures can learn node embeddings
that incorporate neighborhood structure. A provider node's embedding reflects not just its own
billing behavior, but the behavior of its referral partners — allowing detection of guilt-by-
association patterns that purely tabular models miss.

**Practical note**: GNNs are complex to implement and explain. For a hackathon with a 14-day
timeline, simpler graph metrics (degree centrality, clustering coefficient, referral concentration)
computed with NetworkX or igraph and fed into the XGBoost feature set is more tractable than
training a full GNN.

### 4.4 NLP on Clinical Notes and Claim Descriptions

**4.4.1 Claim Narrative Analysis**

Free-text fields in claims (procedure descriptions, diagnosis narratives) can be analyzed for:

- Templated/copy-paste language (identical notes across thousands of patients — a red flag for
  documentation fraud)
- Mismatch between diagnosis codes and procedure descriptions
- Absence of expected clinical detail for high-complexity billing codes

**4.4.2 Prior Authorization Notes**

When prior authorization is required (e.g., for advanced imaging, specialty drugs), the clinical
justification text can be scored for adequacy and consistency with the billed diagnosis.

**4.4.3 Practical Constraint**

CMS open datasets do not include unstructured clinical notes (protected by HIPAA). NLP approaches
require access to electronic health record data or claims attachments, which are available to MACs
and UPICs in an adjudicated context but not to hackathon teams using public data. For the
hackathon, NLP can be applied to code descriptions (HCPCS/CPT long descriptions) and provider
enrollment information, not clinical text.

### 4.5 Peer Comparison (Statistical Deviation)

One of the most defensible and explainable approaches:

**4.5.1 Peer Group Construction**

Define a peer group for each provider using:

- Primary taxonomy code (NPI registry taxonomy = specialty)
- Geographic region (HRR — Hospital Referral Region, or state)
- Practice size (solo, small group <5, medium 5–25, large 25+)

**4.5.2 Metrics and Z-Scores**

For each metric of interest, compute the z-score of a target provider relative to their peer group:

```
z = (provider_metric - peer_mean) / peer_stddev
```

Metrics of interest:

- Average charge per service (by CPT category)
- Services per unique patient per year
- Unique patients per year
- Percentage of high-complexity E&M codes (99214/99215 as share of all E&M)
- Percentage of services on weekends/holidays
- Median patient distance from provider address
- Drug prescription rates (Part D)

A provider with |z| > 3 on multiple metrics simultaneously is a strong anomaly candidate.

**4.5.3 Percentile Ranking**

Simpler and more interpretable: rank the provider at the Nth percentile for each metric within
their peer group. A provider in the 99th percentile for charge-per-service AND the 99th percentile
for services-per-patient is more likely anomalous than one with a single outlier metric.

### 4.6 Temporal Pattern Analysis

**4.6.1 Billing Ramp Detection**

Fraud schemes often start small and scale up rapidly once a scheme is operational. A provider
who increases billing volume by 400% over 6 months (without a corresponding increase in practice
size) is anomalous.

**4.6.2 Seasonal Anomalies**

Some fraud patterns are seasonal — billing concentrated during holiday periods when oversight is
reduced, or sudden spikes in specific service codes that coincide with Medicare Advantage plan
year resets.

**4.6.3 Time-to-Enrollment Correlation**

Fraudulent providers (especially shell clinics) often bill at very high volumes immediately
after enrollment. Legitimate providers tend to ramp up slowly. The billing-volume-in-first-year
metric is a useful signal for newly enrolled providers.

**4.6.4 Changepoint Detection**

Statistical methods (PELT, BOCPD) can identify when a provider's billing pattern undergoes
a structural shift — a potential indicator that a new scheme has been initiated.

---

## 5. Hackathon Judging Criteria Analysis

Understanding what judges are evaluating — and how to demonstrate each criterion — is as important
as the technical quality of the solution.

### 5.1 Explainable AI

**What judges want**: Not just a score, but a clear, human-readable explanation of _why_ a provider
received that score. A fraud investigator who gets a "risk: 87/100" with no explanation cannot
act on it. A fraud investigator who gets "risk: 87/100 — this provider bills 99215 at 4.2x the
peer rate, has patients located an average of 68 miles away vs. peer average of 8 miles, and
began billing 6 months ago with no prior enrollment history" can open an investigation.

**How to demonstrate**:

- SHAP (SHapley Additive exPlanations): industry standard. Generate SHAP waterfall plots showing
  the contribution of each feature to a provider's risk score. The `shap` Python library integrates
  directly with XGBoost, LightGBM, and scikit-learn models.
- LIME (Local Interpretable Model-agnostic Explanations): alternative to SHAP, generates
  human-readable "if-then" rules for individual predictions.
- Attention maps: for neural network components, visualize which features the model attended to.
- Natural language generation: convert SHAP values into sentence-level explanations
  ("This provider's high risk score is primarily driven by...").

**Anti-pattern to avoid**: Using only a black-box model (e.g., a deep neural network with no
explanation layer) and reporting only the final score. Judges with program integrity background
will immediately ask "but why?" — you need an answer.

### 5.2 Transparent Scoring

**What judges want**: Full audit traceability from raw data to final risk score. A CMS compliance
officer must be able to reconstruct the exact calculation that produced any specific risk score for
any specific provider on any specific date. This is a legal requirement for government action —
decisions affecting providers must be explainable and reproducible.

**How to demonstrate**:

- Log every transformation: raw data → cleaned data → feature values → model input → model output
- Version control models and data: record which model version (with hash) and which data snapshot
  produced each score
- Store intermediate outputs: feature vector for each provider stored alongside the risk score
- API response schema should include: risk score, feature contributions, data sources used, model
  version, data timestamp
- "Score report" PDF or structured JSON that could be handed to a provider challenging their score

### 5.3 Responsible AI

**What judges want**: Evidence that the team has considered and mitigated algorithmic bias. A
system that disproportionately flags rural providers, minority-serving providers, or providers
of certain specialties due to model artifacts (rather than actual fraud) would cause serious harm
and would not be deployed.

**How to demonstrate**:

- **Bias testing**: Run the model separately on provider subgroups (by state, urban/rural, specialty,
  patient demographic mix) and compare false positive rates and score distributions across groups.
- **Peer group fairness**: Ensure that peer comparison groups are defined at sufficient granularity
  that legitimate specialty differences are not flagged as anomalies (e.g., an oncologist's high
  procedure volume compared to internists is not fraud).
- **Model card**: Document the model's intended use, training data, performance metrics,
  limitations, and known biases in a structured model card format (Mitchell et al., 2019).
- **Threshold calibration**: Show that different threshold choices produce different
  precision-recall curves and document the policy implications of different operating points.
- **LEIE label caution**: Acknowledge that LEIE labels are imperfect ground truth (only caught
  fraud) and that the model trained on them may miss novel fraud patterns while over-indexing
  on the profiles of previously caught fraudsters.

### 5.4 Scalable Architecture

**What judges want**: A design that could realistically be deployed by CMS at national scale —
not a Jupyter notebook that processes 1,000 providers on a laptop, but a production-ready
architecture that handles 1.5 million providers and 1.3 billion claims per year.

**How to demonstrate**:

- Cloud-native design: container-based (Docker + Kubernetes), not tied to specific hardware
- Async claim processing pipeline: Apache Kafka or similar for claims ingestion at high throughput
- Feature store: pre-computed provider features updated incrementally, not recomputed from scratch
  on each query
- Horizontal scalability: model serving behind a load balancer, stateless workers
- Database: PostgreSQL for structured provider profiles, Parquet/object storage for historical
  claims data — not SQLite or in-memory data structures
- Latency estimate: show that pre-payment claim scoring can be completed within the adjudication
  window (typically minutes to hours for MAC processing)

**For a hackathon**: You do not need to deploy at actual national scale — but your architecture
diagram, API design, and infrastructure-as-code (docker-compose, Kubernetes manifests) should
demonstrate that you've thought through the scaling requirements.

### 5.5 MVP to Pilot Pathway

**What judges want**: A realistic plan for how this solution could be adopted by CMS. Government
technology procurement and deployment are slow, risk-averse processes. A solution that requires
a 5-year deployment timeline has no value as a hackathon win.

**How to demonstrate**:

- Start with CMS open data (no HIPAA issues, no procurement needed for data access)
- Identify a specific CMS organizational owner (Office of Program Integrity, or a specific UPIC)
- Define a pilot scope: "Phase 1 would score providers in 3 high-fraud geographies using Medicare
  Part B data, producing a weekly risk report for UPIC investigators"
- Show integration path: how does the output feed into existing UPIC workflows?
- Define success metrics: what would demonstrate pilot success? (e.g., precision/recall on
  retrospective LEIE cases, investigator time saved per case)
- Acknowledge ATOs: CMS requires an Authority to Operate for any deployed system. Show you
  understand this exists and outline the FedRAMP/ATO path.

---

## 6. What a Winning Solution Looks Like

Based on the judging criteria and the problem domain, a winning submission has the following
components. This is the architecture this project should target.

### 6.1 Provider Risk Profiling Engine

For each NPI in the CMS dataset:

- Build a multi-dimensional behavioral profile across 20–40 features
- Assign to a peer group (specialty + geography + size)
- Compute peer-relative z-scores for key metrics
- Store as a feature vector in a queryable feature store

This is the data foundation. Everything else depends on it.

### 6.2 Ensemble Anomaly Detection

Three model layers, each contributing to a final ensemble score:

| Layer | Model                     | What It Catches                                 |
| ----- | ------------------------- | ----------------------------------------------- |
| 1     | Isolation Forest          | Population-level statistical anomalies          |
| 2     | XGBoost (LEIE-supervised) | Profiles matching known fraud patterns          |
| 3     | Autoencoder               | Novel patterns that don't match normal behavior |

Final risk score: weighted ensemble of three component scores + peer percentile flags.

**Do not rely on a single model.** Judges understand that no single algorithm dominates;
an ensemble demonstrates both technical sophistication and robustness.

### 6.3 Explainability Layer

For every provider risk score:

- SHAP waterfall chart: top 5–10 contributing features, with direction (this factor increased
  risk / this factor decreased risk)
- Peer comparison table: show the provider's value vs. peer median and peer 95th percentile
  for each top SHAP feature
- Natural language summary: 2–3 sentence human-readable explanation of why this provider is flagged
- Confidence interval: the model's uncertainty in the score (especially important for newly enrolled
  providers with limited billing history)

### 6.4 Human Review Dashboard

A functional UI (React + TypeScript per the project stack) that shows:

- **Risk queue**: providers ranked by risk score, with filter by specialty, geography, score range
- **Provider detail page**: full risk profile, SHAP chart, peer comparison, billing history
  visualizations (temporal trends, service mix charts)
- **Action log**: reviewer notes, disposition (referred to UPIC, cleared, escalated)
- **False positive feedback loop**: reviewer decisions feed back into model retraining data

The dashboard is the "wow factor" for demo — judges need to _see_ the system working, not just
read about it.

### 6.5 API

RESTful FastAPI endpoints:

- `GET /providers/{npi}/risk` — risk score + SHAP explanation for a single provider
- `GET /providers/top-risk?specialty=&state=&limit=` — ranked risk list with filters
- `POST /providers/batch-score` — async batch scoring for a list of NPIs
- `GET /providers/{npi}/peer-comparison` — detailed peer group analysis
- `GET /health` — service health check

Auto-generated OpenAPI docs (FastAPI provides this out of the box). A live API demo during the
presentation is significantly more compelling than screenshots.

### 6.6 Responsible AI Documentation

- **Model card**: training data, performance metrics by subgroup, known limitations
- **Bias analysis report**: false positive rates by geography, specialty, and practice size
- **Data lineage diagram**: from CMS raw data to final score, every transformation documented
- **Threshold policy guide**: what operating point to use for different use cases (pre-payment
  hold vs. post-payment audit vs. UPIC referral)

### 6.7 Architecture Diagram

Produce a clear system architecture diagram showing:

- Data sources (CMS open data, LEIE, NPI registry)
- Ingestion pipeline (batch ETL + optional streaming)
- Feature store
- Model training pipeline
- Inference / scoring service
- API layer
- Dashboard
- Feedback loop (reviewer actions → retraining data)

This should be a polished diagram that could appear in a government briefing document.

---

## 7. Key Risks and Considerations

Every serious team must be able to articulate the limitations of their system. Judges who have
program integrity backgrounds will probe these — acknowledging them preemptively is a sign of
maturity.

### 7.1 False Positive Risk

**The problem**: Every false positive is a legitimate provider who gets flagged, may have payments
held, and potentially faces reputational harm and administrative burden. For small practices,
a payment hold of even a few weeks can threaten practice viability. CMS has faced Congressional
criticism for overly aggressive prepayment review programs.

**Mitigation**:

- Set conservative thresholds: prefer high precision (low false positive rate) over high recall
  at the system's initial operating point
- Require multiple corroborating signals before escalating to a payment hold (single-signal flags
  go to a monitoring queue, not an immediate hold)
- Build in a rapid appeal/clearance path that a provider can use to explain anomalous patterns
  (e.g., a rural provider serving a large catchment area will have higher patient travel distances
  than urban peers — not fraud)
- Monitor the false positive rate in production and build in automatic model audits

### 7.2 Specialty and Geography Bias

**The problem**: Rural providers legitimately look anomalous compared to national averages:

- A rural family physician may be the only provider for 100 miles, resulting in very high patient
  volumes and high geographic dispersion of patients
- A rural hospital may bill a wider mix of services than urban specialists because they provide
  primary, emergency, and specialist care in one facility
- Solo rural practitioners cannot be compared fairly to large urban group practices

**Mitigation**:

- Peer group granularity: use HRR (Hospital Referral Region) rather than state as the geographic
  unit, and separate rural/urban categories
- Domain expert review: work with clinical advisors to define specialty-specific features
  (what is normal for a pain management clinic differs dramatically from what is normal for
  a primary care physician)
- Explicit rural flag: add rural designation (RUCA codes) as a feature so the model can learn
  that rural providers have systematically different patterns

### 7.3 LEIE Label Imperfection

**The problem**: Using LEIE as positive labels for supervised learning creates a biased training set:

- LEIE only contains fraud that was _caught_ — novel schemes are absent from the label set
- The LEIE reflects historical enforcement priorities (certain specialties, geographies are
  over-investigated)
- A model trained purely on LEIE patterns will be good at catching yesterday's fraud,
  not tomorrow's novel schemes

**Mitigation**:

- Use LEIE labels for the supervised component (XGBoost) but give significant weight to
  unsupervised components (Isolation Forest, Autoencoder) that don't require labels
- Acknowledge in the model card that the model's recall on novel fraud schemes is unknown
- Build in human-in-the-loop: the model is a triage tool, not an autonomous enforcement system

### 7.4 Privacy and Data Handling

**The problem**: Even public CMS data contains sensitive provider information, and any system
that processes claims data must comply with the Privacy Act, HIPAA (for non-public data), and
CMS data use agreements.

**Mitigation**:

- Use only CMS open data (data.cms.gov) with appropriate data use agreements
- Do not store individual beneficiary information — work at the provider level
- Implement data minimization: only collect and store features necessary for the model
- Document data retention policies
- Note that a production deployment would require a Privacy Impact Assessment (PIA) and
  System of Records Notice (SORN) under the Privacy Act

### 7.5 Temporal Validity

**The problem**: Healthcare billing patterns change over time. Codes are added, retired, or
repriced. New fraud schemes emerge. A model trained on 2017–2020 data may not generalize to 2025
billing patterns.

**Mitigation**:

- Use the most recent CMS data available (CMS typically releases the prior year's data ~18
  months after year-end, so 2022 data is likely the most recent available)
- Build in model retraining cadence: quarterly or annual retraining on fresh data
- Monitor score distribution drift over time — if the population of "high-risk" providers
  changes dramatically quarter-to-quarter without corresponding enforcement actions, the model
  may be experiencing distribution shift
- Version models explicitly so that past scores can be reproduced and audited

### 7.6 Adversarial Adaptation

**The problem**: Sophisticated fraud rings may adapt their behavior once a detection system is
deployed. If fraudsters know that 99215 billing above the 95th percentile triggers a flag,
they will calibrate to the 92nd percentile.

**Mitigation**:

- Keep model features partially confidential (the FPS does this — specific thresholds and
  features are not public)
- Use a diverse ensemble: harder to evade multiple independent detection approaches simultaneously
- Incorporate investigator feedback: as enforcement actions produce new case intelligence,
  update the model to detect the next generation of schemes
- Network-based features are harder to game than individual billing metrics — a fraud ring
  cannot easily dissolve and reform its referral network to evade graph-based detection

---

## Literature and Key Sources

| Source                                                                                                  | Type       | Key Takeaway                                                                              |
| ------------------------------------------------------------------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------- |
| OIG Semiannual Reports to Congress                                                                      | Government | Ground truth on enforcement actions, scheme types, dollar recoveries                      |
| CMS Improper Payments Report (annual)                                                                   | Government | Official improper payment rate by program and service type                                |
| CMS Fraud Prevention System Impact Report                                                               | Government | FPS performance metrics, dollars protected                                                |
| Bauder et al. (2017), "A Survey on Healthcare Fraud Detection"                                          | Academic   | Comprehensive taxonomy of approaches; supervised, unsupervised, hybrid                    |
| Thornton et al. (2013), "Healthcare Fraud and Abuse Detection Using Machine Learning"                   | Academic   | XGBoost and RF on Medicare claims; LEIE labels for supervised training                    |
| Johnson et al. (2019), "Graph Neural Networks for Healthcare Fraud"                                     | Academic   | GNN approach to provider referral networks; superior to tabular methods for network fraud |
| CMS Medicare Provider Utilization and Payment Data                                                      | Dataset    | Primary public dataset for this project; provider-level aggregated claims                 |
| CMS Part D Prescriber Data                                                                              | Dataset    | Drug prescription patterns; critical for opioid fraud signals                             |
| OIG LEIE Database                                                                                       | Dataset    | Fraud-positive labels for supervised learning                                             |
| NUCC Provider Taxonomy Codes                                                                            | Reference  | Specialty classification for peer group construction                                      |
| RUCA (Rural-Urban Commuting Area) Codes                                                                 | Reference  | Rural/urban classification for bias analysis                                              |
| Mitchell et al. (2019), "Model Cards for Model Reporting"                                               | Academic   | Framework for responsible AI documentation                                                |
| Lundberg & Lee (2017), "A Unified Approach to Interpreting Model Predictions"                           | Academic   | SHAP theoretical foundation                                                               |
| Ribeiro et al. (2016), "Why Should I Trust You? LIME"                                                   | Academic   | LIME theoretical foundation                                                               |
| Lundberg et al. (2020), "From local explanations to global understanding with explainable AI for trees" | Academic   | Tree SHAP for ensemble models                                                             |

---

## Conclusions

The CMS Proactive Program Integrity challenge is a well-scoped hackathon problem with:

1. **Available public data**: CMS releases provider-level Medicare utilization data that is
   sufficient to build a meaningful prototype without any special data access.

2. **Clear technical approach**: The ensemble of Isolation Forest + XGBoost (LEIE-supervised) +
   peer comparison is well-validated in the literature and tractable in a 14-day sprint.

3. **Strong explainability story**: SHAP is the right tool. It integrates with the chosen stack,
   produces human-readable outputs, and is the standard CMS would expect in production.

4. **Defensible responsible AI posture**: Rural vs. urban bias is the most important fairness
   concern; peer group granularity is the primary mitigation.

5. **Clear pilot pathway**: Start with public Part B data, target UPIC referrals as the output
   workflow, pilot in 3 known high-fraud metropolitan areas.

The technical risk is low — these are well-understood methods on publicly available data. The
differentiation will come from (a) quality of explainability, (b) production-readiness of the
architecture, and (c) clarity of the pilot deployment plan.

---

## Next Steps

1. [ ] Download CMS Medicare Part B Provider Utilization and Payment Data (2022 is latest)
2. [ ] Download OIG LEIE exclusion list and normalize NPI join keys
3. [ ] Download NPI Registry (NPPES) for provider taxonomy and address data
4. [ ] Build peer group assignment logic (specialty + HRR + size tier)
5. [ ] Engineer the 20–40 provider-level features described in Section 4.5
6. [ ] Train Isolation Forest baseline, evaluate anomaly score distribution
7. [ ] Train XGBoost with LEIE labels, tune precision/recall threshold
8. [ ] Implement SHAP waterfall for individual provider explanations
9. [ ] Build FastAPI endpoints for risk score and peer comparison
10. [ ] Implement React dashboard: risk queue + provider detail view
11. [ ] Run bias analysis: false positive rates by state, specialty, rural/urban
12. [ ] Write model card and responsible AI documentation
13. [ ] Prepare architecture diagram for judging presentation
14. [ ] Rehearse live demo: score a real NPI, show SHAP explanation, show dashboard drill-down
