# CMS Demo Data Research and Graph Strategy

> Review draft for the March 2026 hackathon sprint. This is a planning document only. No
> implementation should start until the data stack, scoring unit, and architecture are approved.

STATUS: review-draft
created: 2026-03-12
updated: 2026-03-12
owner: Codex research pass

---

## Executive Take

The public-data path is viable, but only if the demo is honest about what the data represents.

- The best MVP data spine is `Part B provider/service + NPPES + public provider enrollment + revoked providers + geographic variation`.
- The best enrichment layers are `Part D`, `DME referring provider/service`, and `Open Payments`.
- `OIG LEIE` is useful for screening and retrospective validation, but it is weak as a primary join
  source because most rows do not carry an NPI.
- The public CMS files are not claim-level adjudication data. They are provider-level or
  provider-service aggregates. We should not claim that we are classifying every real CMS claim or
  payment line.
- The most defensible scoring unit for the demo is a `ProviderCase` built from an aggregate payment
  slice such as `NPI + HCPCS + place_of_service + year`, `NPI + drug + year`, or `NPI + DME
category + year`.
- The best technical shape is not graph-only. Use `DuckDB + Parquet` for ingestion and feature
  engineering, then project high-value entities and edges into `Neo4j` for explainability and
  investigator workflow.

## Primary Questions This Research Answers

1. Which public datasets can we actually use in the sprint?
2. Which datasets are strong enough for the demo, and which are only secondary enrichment?
3. How do the sources connect into a provider-risk graph?
4. What is the right unit of scoring if we want both fraud signals and legitimacy signals?
5. What should our differentiator be relative to the publicly described CMS program-integrity stack?

## Official Source Inventory

These are the official pages or APIs used for discovery and download.

| Source family                                 | Official source                                                                                                   | Notes                                                                           |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| CMS provider utilization and payment data     | https://data.cms.gov/provider-summary-by-type-of-service                                                          | Primary source for Part A, Part B, Part D, DME, and geographic public use files |
| CMS data API                                  | https://data.cms.gov/data-api                                                                                     | Bulk data is downloadable through the site and API-backed resources             |
| CMS NPPES downloads                           | https://download.cms.gov/nppes/NPI_Files.html                                                                     | Monthly, weekly, and deactivated NPI files                                      |
| CMS Open Payments program page                | https://www.cms.gov/priorities/key-initiatives/open-payments/data                                                 | Program overview and publication cadence                                        |
| Open Payments dataset catalog API             | https://openpaymentsdata.cms.gov/api/1/metastore/schemas/dataset/items?show-reference-ids=false                   | Machine-readable catalog with direct download URLs                              |
| OIG LEIE                                      | https://oig.hhs.gov/exclusions/downloadables/UPDATED.csv                                                          | Direct CSV download for the exclusion list                                      |
| CMS fraud portal                              | https://www.cms.gov/fraud                                                                                         | Public view of CMS fraud and program-integrity infrastructure                   |
| Fraud Prevention Operations Center fact sheet | https://www.cms.gov/files/document/fact-sheet-fraud-prevention-operations-center-fpoc.pdf                         | Public description of the operational fraud review environment                  |
| Fraud Prevention System 2 PIA                 | https://www.cms.gov/files/document/fps2-pia.pdf                                                                   | Public description of the data-sharing and analytics environment                |
| UPIC overview                                 | https://www.cms.gov/medicare/medicaid-coordination/center-program-integrity/unified-program-integrity-contractors | Public description of contractor-led investigation and review workflow          |

## What I Downloaded Locally

All downloaded files are staged under `data/raw/public_sources/`.

| Family          | Local size | Key files staged locally                                                                                                                                                                                                                                                                                      | Why it matters                                                             |
| --------------- | ---------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `cms/`          |     `8.6G` | `part_b_provider_2023.csv`, `part_b_provider_service_2023.csv`, `part_d_provider_2023.csv`, `part_d_provider_drug_2023.csv`, `dme_referring_provider_service_2023.csv`, `public_provider_enrollment_q4_2025.csv`, `revoked_providers_q1_2026.csv`, `geographic_variation_national_state_county_2014_2023.csv` | Core provider behavior, peer baselines, enrollment, and sanctions          |
| `openpayments/` |     `9.4G` | `general_payments_2024.csv`, `research_payments_2024.csv`, `ownership_payments_2024.csv`, `physician_distinct_profile_2024.csv`, `reporting_entity_profile_2024.csv`, `provider_profile_id_mapping_2024.csv`                                                                                                  | Manufacturer and financial-relationship enrichment                         |
| `nppes/`        |     `1.1G` | `nppes_monthly_2026_03_v2.zip`, `nppes_weekly_2026_03_02_03_08_v2.zip`, `nppes_deactivated_2026_03_v2.zip`                                                                                                                                                                                                    | Provider identity, taxonomy, address, activation, and deactivation context |
| `oig/`          |      `15M` | `leie_updated.csv`                                                                                                                                                                                                                                                                                            | Exclusion screening and retrospective validation                           |

Approximate total staged footprint: `19G`.

## Dataset Quality and Demo Suitability

### 1. Core CMS behavior files

| Dataset                                    |         Rows | Join key                                | Quality assessment                                                                                                                 | Demo role                                               |
| ------------------------------------------ | -----------: | --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| Part B provider                            |  `1,259,343` | `Rndrng_NPI`                            | Strong. One row per NPI, no missing provider type or state in the profiled file.                                                   | Core identity and annual provider baseline              |
| Part B provider and service                |  `9,660,647` | `Rndrng_NPI`, `HCPCS_Cd`                | Strong. `HCPCS` and `place_of_service` are complete; only small sparsity in RUCA.                                                  | Core scoring table                                      |
| Part D provider                            |  `1,380,665` | `Prscrbr_NPI`                           | Usable, but suppression flags are common.                                                                                          | Secondary enrichment                                    |
| Part D provider and drug                   | `26,794,878` | `Prscrbr_NPI`, `Brnd_Name`, `Gnrc_Name` | Usable, but heavily suppression-aware. Many subgroup fields contain public suppression markers.                                    | Secondary enrichment for prescribing-risk patterns      |
| DME referring provider and service         |  `1,439,587` | `Rfrg_NPI`, `HCPCS_CD`, `RBCS_Id`       | Mixed. Strong keys, but `Tot_Suplr_Benes` is null in roughly `70%` of rows.                                                        | Useful for referral-pattern flags, not for every metric |
| Public provider enrollment                 |  `2,957,262` | `NPI`                                   | Strong content, but the CSV needs a tolerant parser because of row-format issues. Row count was preserved with permissive parsing. | Critical status and enrollment context                  |
| Revoked providers                          |      `7,465` | `NPI`                                   | Strong and compact. Excellent for retrospective validation and risk boosting.                                                      | Sanctions and weak-supervision seed                     |
| Geographic variation national/state/county |     `33,639` | geography keys                          | Strong and compact. Good peer-normalization layer.                                                                                 | Benchmark normalization                                 |

### 2. Open Payments

| Dataset                     |         Rows | Join key                                                | Quality assessment                                                                  | Demo role                                     |
| --------------------------- | -----------: | ------------------------------------------------------- | ----------------------------------------------------------------------------------- | --------------------------------------------- |
| Physician distinct profile  |  `1,616,118` | `Covered_Recipient_NPI`                                 | Strong direct physician crosswalk with low NPI sparsity.                            | Best Open Payments bridge table               |
| General payments            | `15,383,596` | `Covered_Recipient_NPI`, `Covered_Recipient_Profile_ID` | Strong enough for production-style enrichment. Direct NPI is present for most rows. | Best event-level financial relationship table |
| Research payments           |    `756,906` | `Covered_Recipient_Profile_ID`                          | Weak direct NPI coverage. Most rows do not carry an NPI.                            | Optional enrichment only                      |
| Ownership payments          |      `4,591` | `Covered_Recipient_NPI`, `Covered_Recipient_Profile_ID` | Small but high-value.                                                               | High-signal enrichment                        |
| Reporting entity profile    |      `2,900` | `AMGPO_Making_Payment_ID`                               | Strong compact dimension table.                                                     | Manufacturer or GPO metadata                  |
| Provider profile ID mapping |      `2,180` | profile IDs                                             | Very small helper mapping.                                                          | Minor bridge table                            |

### 3. NPPES and OIG

| Dataset                  |                                     Observed size or count | Join key                                | Quality assessment                                                                  | Demo role                                      |
| ------------------------ | ---------------------------------------------------------: | --------------------------------------- | ----------------------------------------------------------------------------------- | ---------------------------------------------- |
| NPPES monthly V2         |           `1.0G` zip, about `11.26G` uncompressed main CSV | `NPI`                                   | Rich and authoritative, but too heavy to parse live during the demo build.          | Baseline identity snapshot after preprocessing |
| NPPES weekly V2          | `30,722` lines including header in the sampled weekly file | `NPI`                                   | Excellent as a small freshness layer.                                               | Fast delta update source                       |
| NPPES deactivated report |            `336,536` rows including header in the workbook | `NPI`                                   | Valuable for status changes, but needs workbook parsing.                            | Status-change enrichment                       |
| OIG LEIE                 |                                              `82,749` rows | NPI when present, otherwise name or org | Weak direct NPI coverage. Roughly `89.7%` of profiled rows had missing or zero NPI. | Screening and retrospective validation only    |

## The Most Important Quality Findings

- `Part B provider and service` is the strongest core table. It is large enough to be meaningful and
  clean enough to build reliable peer comparisons.
- `Part D` is valuable, but public suppression is everywhere. We need suppression-aware feature
  engineering and should avoid claiming precision on heavily suppressed subgroup metrics.
- `Public provider enrollment` is strategically important because it gives status and specialty
  context, but we must use a tolerant CSV reader in the pipeline.
- `General payments` is much more useful than `research payments` for direct provider joins.
- `NPPES monthly` is too heavy to treat as an on-demand runtime source. It should become a curated
  identity dimension once, then refreshed by weekly deltas.
- `LEIE` is not a good primary label table. It is still useful as a sanity check, a screening edge,
  and a historical credibility signal.

## Join Coverage That Matters

Distinct NPI overlap across the staged sources:

| Join                                               |                                             Overlap | Why it matters                                                            |
| -------------------------------------------------- | --------------------------------------------------: | ------------------------------------------------------------------------- |
| Part B provider -> public provider enrollment      | `1,213,556` providers (`96.4%` of Part B providers) | Enrollment is a near-universal status layer                               |
| Part B provider -> Part D provider                 |                       `835,315` providers (`66.3%`) | Strong cross-program provider overlap                                     |
| Part B provider -> Open Payments physician profile |                       `831,175` providers (`66.0%`) | Open Payments can enrich a large share of Part B providers                |
| Part B provider -> Open Payments general payments  |                       `575,263` providers (`45.7%`) | Event-level financial relationships are available for a meaningful subset |
| Part B provider -> DME referring provider/service  |                       `261,928` providers (`20.8%`) | DME signals are selective but useful                                      |
| Part B provider -> revoked providers               |                            `863` providers (`0.1%`) | Rare but high-confidence risk cases                                       |
| Part B provider -> LEIE rows with nonzero NPI      |                                     `187` providers | Direct LEIE NPI joins are too sparse to anchor the model                  |
| Part D provider -> Open Payments physician profile | `1,040,305` providers (`75.3%` of Part D providers) | Strong bridge between prescribing and financial relationships             |
| Part D provider -> Open Payments general payments  |                       `708,648` providers (`51.3%`) | Good crosswalk for prescriber influence patterns                          |

## What This Means for the Demo

The data supports a strong `provider-case scoring and explanation demo`. It does not support a fully
honest `claim-by-claim pre-adjudication classifier` from public data alone.

### Recommended scoring unit

Use one of these as the main `Case` node:

- `ProviderServiceCase = NPI + HCPCS + place_of_service + year`
- `ProviderDrugCase = NPI + generic_or_brand_drug + year`
- `ProviderDMECase = referring_NPI + RBCS_or_HCPCS + year`

Why this is the right compromise:

- These units map directly to the public aggregates we actually have.
- They allow provider-to-peer comparisons.
- They support signal attribution without inventing fake precision.
- They still look like payment-review work to judges.

### If the UI must show "each payment"

Use one of these patterns and label it clearly:

- `PaymentSlice` nodes built from public aggregates, with full provenance back to CMS source rows
- Synthetic claim records for UX only, backed by public aggregate features and clearly marked as
  simulated examples

Do not present these as real CMS claim-line decisions.

## How the Sources Connect

The public data naturally forms a provider-centered evidence graph.

![Evidence Graph](diagrams/05-evidence-graph.png)

### Canonical entities

| Node                  | Backing source                       | Purpose                                           |
| --------------------- | ------------------------------------ | ------------------------------------------------- |
| `Provider`            | Part B, Part D, NPPES, enrollment    | Canonical identity anchor                         |
| `Enrollment`          | Public provider enrollment           | Active or recent enrollment context               |
| `Revocation`          | Revoked providers                    | High-confidence adverse status                    |
| `Exclusion`           | LEIE                                 | Screening and credibility context                 |
| `Specialty`           | NPPES, Part B, Part D                | Peer-group definitions                            |
| `GeoBenchmark`        | Geographic variation PUF             | Regional normalization                            |
| `ProviderServiceCase` | Part B provider and service          | Main scoring unit                                 |
| `ProviderDrugCase`    | Part D provider and drug             | Prescribing-risk scoring unit                     |
| `ProviderDMECase`     | DME referring provider and service   | DME-focused scoring unit                          |
| `OpenPaymentEvent`    | General payments, ownership payments | Financial relationship event                      |
| `Manufacturer`        | Reporting entity profile             | Paying organization                               |
| `Signal`              | Engineered features                  | Human-readable evidence nodes                     |
| `SourceRecord`        | Any raw file                         | Provenance back to exact source table and row set |

## Fraud Signals and Legitimacy Signals

The product story gets stronger if the model explains both suspicion and stabilization.

### Suspicion signals

| Signal family              | Example signals                                                                                 | Main source                          |
| -------------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------ |
| Volume outliers            | Services per beneficiary, claims volume, cost intensity far above specialty and geography peers | Part B, Part D, geographic variation |
| Mix anomalies              | HCPCS or drug mix inconsistent with specialty or enrollment type                                | Part B, Part D, NPPES, enrollment    |
| Price anomalies            | Charge-to-allowed and charge-to-payment ratios well above peers                                 | Part B                               |
| Place-of-service anomalies | Facility versus office mix inconsistent with peers or service norm                              | Part B                               |
| Growth shocks              | Abrupt year-over-year change in billing or prescribing                                          | Part B, Part D                       |
| DME concentration          | Unusual concentration in DME categories or suppliers                                            | DME referring provider/service       |
| Influence patterns         | Manufacturer payment concentration or ownership ties                                            | Open Payments                        |
| Compliance history         | Revocation or exclusion adjacency                                                               | Revoked providers, LEIE              |

### Legitimacy signals

| Signal family         | Example signals                                                   | Main source                          |
| --------------------- | ----------------------------------------------------------------- | ------------------------------------ |
| Stable identity       | NPPES, enrollment, and billing identity agree across sources      | NPPES, enrollment, Part B, Part D    |
| Specialty consistency | Billed services and prescribed drugs align with provider taxonomy | NPPES, Part B, Part D                |
| Peer alignment        | Utilization and payment ratios stay within peer bands             | Part B, Part D, geographic variation |
| Clean status          | No revocation, no exclusion, active enrollment                    | Enrollment, revoked providers, LEIE  |
| Multi-year stability  | No sudden volume spikes or role changes                           | Part B, Part D, NPPES                |
| Diverse relationships | Open Payments not concentrated to suspicious levels               | Open Payments                        |

![Signal Taxonomy](diagrams/08-signal-taxonomy.png)

### Recommended output contract

For every scored case:

- `risk_score`
- `risk_band`
- `top_risk_signals`
- `top_legitimacy_signals`
- `supporting_peer_baseline`
- `source_provenance`

This directly answers the user-facing requirement:

- If the case looks suspicious, show why.
- If the case looks legitimate, show what stabilizes it.

## Recommended Demo Architecture

The fastest credible build is a hybrid analytics and graph stack.

![Data Pipeline](diagrams/03-data-pipeline.png)

> Full architecture specification: [Architecture v3](architecture-v3.md) | All diagrams: [docs/diagrams/](diagrams/)

### Why this architecture is the right fit

- `DuckDB` is the fastest way to profile and transform files of this size inside the sprint.
- `Parquet` gives us repeatable, compressed intermediate tables.
- `Neo4j` gives the demo a natural relationship view and supports explainable drill-down.
- A graph database alone is not the right engine for heavy raw CSV feature building.
- A pure tabular dashboard would miss the relationship story that differentiates the demo.

## Current Publicly Described CMS System vs Our Differentiator

### What the public CMS material suggests today

Public CMS materials describe a multi-part program-integrity environment that includes the fraud
portal, contractor-led review via `UPICs`, and centralized operations and analytics components such as
the `Fraud Prevention Operations Center` and `Fraud Prevention System 2`.

That public picture suggests a system that is:

- operationally complex
- contractor and workflow heavy
- strong on case management and review coordination
- not naturally transparent to an end user about why a provider or payment pattern looks suspicious

### Our differentiator

We should not pitch "better black-box fraud AI." We should pitch:

- a transparent provider evidence graph
- a balanced decision surface that shows both suspicion and legitimacy
- source-level provenance for every signal
- peer-based context by specialty and geography
- a demo path from public data today to pre-payment screening tomorrow

That positioning is more credible than claiming that we have replaced the existing CMS fraud stack.

## Recommended MVP Stack

### Must-have for implementation

- Part B provider and service
- Part B provider
- NPPES weekly or preprocessed monthly baseline
- Public provider enrollment
- Revoked providers
- Geographic variation national, state, county

### Add if time allows

- Part D provider
- Part D provider and drug
- DME referring provider and service
- Open Payments physician profile
- Open Payments general payments
- Open Payments ownership payments

### Keep as optional or validation only

- OIG LEIE
- Open Payments research payments
- Inpatient and outpatient provider service files

## What Not To Do In The MVP

- Do not claim real claim-level adjudication from public aggregate data.
- Do not make `LEIE` the main label source.
- Do not run the raw monthly NPPES file directly in every analysis loop.
- Do not make the first version graph-only.
- Do not make the first version a black-box-only anomaly score with no evidence model.

## Recommended First Implementation Sequence After Approval

1. Canonicalize the provider identity spine from `Part B + enrollment + NPPES`.
2. Build `ProviderServiceCase` as the primary scored unit from Part B.
3. Add peer baselines by specialty, geography, and place of service.
4. Create explainable risk and legitimacy signals.
5. Project scored cases and relationships into Neo4j.
6. Layer in Part D, DME, and Open Payments as enrichment.

## Approval Decisions Needed

Please approve or change these before build-out:

1. Approve `ProviderServiceCase` as the primary scored unit.
2. Approve `DuckDB + Parquet + Neo4j` as the demo architecture.
3. Approve the must-have dataset stack listed above.
4. Decide whether the UI should use public `PaymentSlice` nodes only or also include synthetic
   payment examples for storytelling.

## Local Data Paths

Main local staging paths:

- `data/raw/public_sources/cms/`
- `data/raw/public_sources/openpayments/`
- `data/raw/public_sources/nppes/`
- `data/raw/public_sources/oig/`

The largest staged files right now are:

- `data/raw/public_sources/openpayments/general_payments_2024.csv` at about `8.3G`
- `data/raw/public_sources/cms/part_d_provider_drug_2023.csv` at about `3.6G`
- `data/raw/public_sources/cms/part_b_provider_service_2023.csv` at about `2.9G`
- `data/raw/public_sources/nppes/nppes_monthly_2026_03_v2.zip` at about `1.0G` zipped

## Bottom Line

We have enough public data, right now, to build a strong and defensible fraud-risk demo. The winning
move is to center the MVP on provider-service risk cases, not pretend that public aggregate files are
real pre-adjudication claims. If we keep the system evidence-driven, graph-enabled, and explicit
about both fraud and legitimacy signals, this can be both technically credible and demo-friendly.
