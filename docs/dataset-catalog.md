# CMS Fraud Detection — Public Dataset Catalog

> Comprehensive reference for all publicly available datasets useful for Medicare/Medicaid fraud, waste, and abuse detection.

**Scope**: Medicare Part A/B/D, Medicaid, OIG exclusions, provider registry, Open Payments
**Last Updated**: 2026-03-12
**Status**: Reference document — update annually as CMS releases new data years

---

See also: [Data Pipeline Diagram](diagrams/03-data-pipeline.png) for how these datasets flow through the ETL pipeline.

## Challenge Starter Stack

The official CMS use-case brief explicitly points teams at a small public-data starter set. For the
two-week MVP, treat the following as the default build order:

| Priority | Dataset                                                            | Why it matters                                                                                       | Join key                                |
| -------- | ------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- | --------------------------------------- |
| 1        | Medicare Physician & Other Practitioners - by Provider and Service | Core provider-behavior dataset for peer baselines, code mix, volume, and charge anomalies            | `rndrng_npi`                            |
| 2        | NPPES / NPI Registry                                               | Provider identity, type, location, and taxonomy enrichment                                           | `npi`                                   |
| 3        | Medicare Geographic Variation Public Use File                      | Regional normalization and state or HRR peer benchmarks                                              | geography fields                        |
| 4        | Open Payments                                                      | Financial-relationship enrichment that can strengthen referral or influence narratives               | provider identifiers plus name matching |
| 5        | Medicare Part D Prescribers - by Provider and Drug                 | Prescription-behavior enrichment, especially for specialty mismatch or controlled-substance patterns | `prscrbr_npi`                           |
| 6        | OIG LEIE                                                           | Retrospective validation or screening enrichment for excluded entities                               | NPI, name, organization                 |

Recommended MVP stance:

- Start with Part B plus NPPES to produce a strong provider risk score quickly
- Add Geographic Variation for fairer peer baselines
- Add Open Payments and Part D only if they improve the demo story without destabilizing delivery
- Keep LEIE as validation or enrichment, not as the primary detection strategy

---

## Table of Contents

1. [Medicare Provider Utilization & Payment Data](#1-medicare-provider-utilization--payment-data)
   - 1.1 Part B — Physician/Supplier
   - 1.2 Part D — Prescriber
   - 1.3 Part A Inpatient (MEDPAR-derived)
   - 1.4 Part A Outpatient
   - 1.5 DMEPOS
   - 1.6 Home Health
   - 1.7 Hospice
   - 1.8 Skilled Nursing Facility
2. [LEIE — OIG Exclusion Database](#2-leie--oig-exclusion-database)
3. [Open Payments (Sunshine Act)](#3-open-payments-sunshine-act)
4. [NPPES — NPI Registry](#4-nppes--npi-registry)
5. [Kaggle Labeled Datasets](#5-kaggle-labeled-datasets)
6. [CMS DE-SynPUF — Synthetic Claims](#6-cms-de-synpuf--synthetic-claims)
7. [Supporting Reference Datasets](#7-supporting-reference-datasets)
   - 7.1 HCPCS/CPT Code Reference
   - 7.2 PECOS — Provider Enrollment
   - 7.3 Area Health Resource File (AHRF)
   - 7.4 Hospital Compare
   - 7.5 Physician Compare (now Care Compare)
   - 7.6 Medicare Advantage Penetration
8. [Join Key Architecture](#8-join-key-architecture)
9. [Recommended Download Order](#9-recommended-download-order)

---

## 1. Medicare Provider Utilization & Payment Data

All datasets in this section are published annually by CMS on data.cms.gov. They are aggregated at the provider-service level — not individual claims — so they are publicly available without a DUA (Data Use Agreement). The aggregation threshold means cells with fewer than 11 services are suppressed.

### 1.1 Part B — Physician and Supplier Payments

**Official Name**: Medicare Physician & Other Practitioners — by Provider and Service

**URL Pattern**:

```
https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners/medicare-physician-other-practitioners-by-provider-and-service
```

**Also available as**:

- By Provider (aggregate across all services for a provider)
- By Geography (state/county-level aggregate)
- By Service (HCPCS code aggregate across all providers)

**Format**: CSV (bulk download), REST API (JSON/CSV)

**Key Columns**:

| Column                       | Type   | Fraud Relevance                        |
| ---------------------------- | ------ | -------------------------------------- |
| `rndrng_npi`                 | string | Provider identifier — JOIN key         |
| `rndrng_prvdr_last_org_name` | string | Name matching, alias detection         |
| `rndrng_prvdr_type`          | string | Specialty mismatch detection           |
| `rndrng_prvdr_state_abrvtn`  | string | Geographic outlier analysis            |
| `hcpcs_cd`                   | string | Procedure code billed                  |
| `hcpcs_desc`                 | string | Human-readable service                 |
| `tot_benes`                  | int    | Distinct beneficiaries served          |
| `tot_srvcs`                  | int    | Total services rendered                |
| `tot_sbmtd_chrg`             | float  | Total charges submitted                |
| `tot_mdcr_alowd_amt`         | float  | Medicare allowed amount                |
| `tot_mdcr_pymt_amt`          | float  | Actual Medicare payment                |
| `avg_mdcr_pymt_amt`          | float  | Avg payment per service                |
| `avg_sbmtd_chrg`             | float  | Avg charge submitted                   |
| `avg_mdcr_alowd_amt`         | float  | Avg allowed amount                     |
| `place_of_srvc`              | string | F=facility, O=office (upcoding signal) |

**Approximate Size**:

- By Provider & Service: ~10M rows/year (provider × HCPCS combinations)
- By Provider: ~1.1M rows/year
- By Service (HCPCS): ~60K rows/year

**Years Available**: 2012–2022 (most recent as of cutoff); CMS releases ~18 months after service year.

**Fraud Detection Use Cases**:

- Billing volume outliers vs. peer specialty (z-score per HCPCS + specialty)
- Charge-to-payment ratio inflation (submitted charges >> allowed amounts)
- Place-of-service upcoding (billing facility rate for office visit)
- Services per beneficiary far exceeding anatomical possibility
- Provider bills HCPCS codes outside their specialty
- Geographic clustering of high-billing providers

**Access**: Fully public, no registration required.

---

### 1.2 Part D — Prescriber-Level Drug Payments

**Official Name**: Medicare Part D Prescribers — by Provider and Drug

**URL Pattern**:

```
https://data.cms.gov/provider-summary-by-type-of-service/medicare-part-d-prescribers/medicare-part-d-prescribers-by-provider-and-drug
```

**Also available as**:

- By Provider (aggregate across all drugs for a prescriber)
- By Geography

**Format**: CSV, REST API

**Key Columns**:

| Column                 | Type   | Fraud Relevance                                      |
| ---------------------- | ------ | ---------------------------------------------------- |
| `prscrbr_npi`          | string | Prescriber NPI                                       |
| `prscrbr_type`         | string | Specialty — opioid prescribing by non-pain specialty |
| `prscrbr_state_abrvtn` | string | State license check                                  |
| `brnd_name`            | string | Brand drug name                                      |
| `gnrc_name`            | string | Generic name                                         |
| `tot_clms`             | int    | Total prescription claims                            |
| `tot_30day_fills`      | float  | 30-day fill equivalents                              |
| `tot_drug_cst`         | float  | Total drug cost                                      |
| `tot_benes`            | int    | Distinct beneficiaries                               |
| `opioid_clms`          | int    | Opioid claim count                                   |
| `opioid_drug_cst`      | float  | Opioid drug cost                                     |
| `opioid_benes`         | int    | Opioid beneficiary count                             |
| `antbtc_clms`          | int    | Antibiotic claims                                    |
| `hrm_opioid_clms`      | int    | High-risk/long-acting opioid claims                  |
| `la_opioid_clms`       | int    | Long-acting opioid claims                            |
| `avg_day_suply`        | float  | Average days supply per fill                         |
| `avg_bene_age`         | float  | Average beneficiary age                              |
| `bene_feml_cnt`        | int    | Female beneficiary count                             |

**Approximate Size**: ~25M rows/year (prescriber × drug combinations)

**Years Available**: 2013–2022

**Fraud Detection Use Cases**:

- Opioid pill mill detection (high volume, broad geographic spread of patients)
- Drug cost inflation (prescribing expensive brand over equivalent generic)
- Prescribing drugs outside specialty scope
- Prescribers with high ratio of opioid claims to total claims
- Long-acting opioid prescribing patterns inconsistent with specialty
- Coincident high prescribing + Open Payments pharma relationships (kickback signal)

**Access**: Fully public. The opioid columns were added to the public release specifically to support fraud research.

---

### 1.3 Part A Inpatient — Hospital Discharges (MEDPAR-Derived)

**Official Name**: Medicare Inpatient Hospitals — by Provider and Service (DRG)

**URL Pattern**:

```
https://data.cms.gov/provider-summary-by-type-of-service/medicare-inpatient-hospitals/medicare-inpatient-hospitals-by-provider-and-service
```

**Format**: CSV, REST API

**Key Columns**:

| Column                      | Type   | Fraud Relevance                                |
| --------------------------- | ------ | ---------------------------------------------- |
| `rndrng_prvdr_ccn`          | string | CMS Certification Number (hospital identifier) |
| `rndrng_prvdr_org_name`     | string | Hospital name                                  |
| `rndrng_prvdr_state_abrvtn` | string | State                                          |
| `drg_cd`                    | string | Diagnosis Related Group code                   |
| `drg_desc`                  | string | DRG description                                |
| `tot_dschrgs`               | int    | Total discharges (volume)                      |
| `avg_submtd_cvrd_chrg`      | float  | Avg submitted covered charges                  |
| `avg_ttl_pymt_amt`          | float  | Avg total Medicare payment                     |
| `avg_mdcr_pymt_amt`         | float  | Avg Medicare-only payment                      |

**Approximate Size**: ~200K rows/year (hospital × DRG combinations)

**Years Available**: 2011–2022

**Fraud Detection Use Cases**:

- DRG upcoding: hospital bills higher-severity DRG than diagnosis supports
- Charge inflation: submitted charges far exceeding peer hospitals for same DRG
- Outlier payment patterns: facilities consistently receiving outlier payments (separate from DRG base payment)
- One-day stay patterns for DRGs requiring multi-day admission
- High discharge volume for rarely-indicated procedures

**Access**: Fully public.

---

### 1.4 Part A Outpatient — Facility Services

**Official Name**: Medicare Outpatient Hospitals — by Provider and Service (APC)

**URL Pattern**:

```
https://data.cms.gov/provider-summary-by-type-of-service/medicare-outpatient-hospitals/medicare-outpatient-hospitals-by-provider-and-service
```

**Format**: CSV, REST API

**Key Columns**:

| Column                  | Type   | Fraud Relevance                        |
| ----------------------- | ------ | -------------------------------------- |
| `rndrng_prvdr_ccn`      | string | CMS Certification Number               |
| `rndrng_prvdr_org_name` | string | Facility name                          |
| `apc_cd`                | string | Ambulatory Payment Classification code |
| `apc_desc`              | string | APC description                        |
| `bene_cnt`              | int    | Beneficiary count                      |
| `srvcs_cnt`             | int    | Service count                          |
| `avg_submtd_cvrd_chrg`  | float  | Avg submitted charge                   |
| `avg_mdcr_pymt_amt`     | float  | Avg Medicare payment                   |

**Approximate Size**: ~600K rows/year

**Years Available**: 2011–2022

**Fraud Detection Use Cases**:

- Facility billing for services more appropriate in office setting
- APC-level charge outliers vs. peer facilities
- High-volume low-acuity APCs suggesting unnecessary services
- Cross-reference with Part B for same provider billing both Part A outpatient and Part B for same service (duplicate billing)

**Access**: Fully public.

---

### 1.5 DMEPOS — Durable Medical Equipment

**Official Name**: Medicare Durable Medical Equipment, Prosthetics, Orthotics and Supplies — by Supplier

**URL Pattern**:

```
https://data.cms.gov/provider-summary-by-type-of-service/medicare-durable-medical-equipment-prosthetics-orthotics-and-supplies/medicare-dme-by-supplier-and-service
```

**Format**: CSV, REST API

**Key Columns**:

| Column                      | Type   | Fraud Relevance                               |
| --------------------------- | ------ | --------------------------------------------- |
| `rndrng_npi`                | string | Supplier NPI                                  |
| `rndrng_prvdr_org_name`     | string | Supplier name                                 |
| `rndrng_prvdr_state_abrvtn` | string | State                                         |
| `hcpcs_cd`                  | string | DMEPOS HCPCS code                             |
| `hcpcs_desc`                | string | Item description                              |
| `tot_suplrs`                | int    | Count of distinct suppliers billing this code |
| `tot_suplr_benes`           | int    | Beneficiary count                             |
| `tot_suplr_clms`            | int    | Claim count                                   |
| `tot_suplr_srvcs`           | int    | Service units                                 |
| `avg_suplr_sbmtd_chrg`      | float  | Avg submitted charge                          |
| `avg_suplr_mdcr_alowd_amt`  | float  | Avg allowed amount                            |
| `avg_suplr_mdcr_pymt_amt`   | float  | Avg Medicare payment                          |
| `bene_avg_age`              | float  | Average beneficiary age                       |
| `bene_feml_pct`             | float  | Percent female beneficiaries                  |

**Approximate Size**: ~2M rows/year

**Years Available**: 2013–2022

**Fraud Detection Use Cases**:

- DMEPOS is historically the highest-fraud category in Medicare
- Phantom billing: supplier bills for equipment never delivered
- Kickback signals: ordering physician heavily refers to single supplier
- Geographic impossibilities: supplier in Florida has high volume in Montana
- Beneficiary diversity: very low beneficiary count with high claim volume
- Power wheelchair schemes: HCPCS K0861/K0862 with non-ambulatory diagnoses
- Expensive item substitution: billing for complex wheelchair, delivering basic one

**Access**: Fully public.

---

### 1.6 Home Health Agency Utilization

**Official Name**: Medicare Home Health Agencies — by Provider

**URL Pattern**:

```
https://data.cms.gov/provider-summary-by-type-of-service/medicare-home-health-agencies/medicare-home-health-agencies-by-provider
```

**Format**: CSV, REST API

**Key Columns**:

| Column                      | Type   | Fraud Relevance              |
| --------------------------- | ------ | ---------------------------- |
| `rndrng_prvdr_ccn`          | string | HHA CMS Certification Number |
| `rndrng_prvdr_org_name`     | string | Agency name                  |
| `rndrng_prvdr_state_abrvtn` | string | State                        |
| `tot_hha_epsd`              | int    | Total home health episodes   |
| `tot_hha_benes`             | int    | Beneficiaries served         |
| `tot_hha_chrg`              | float  | Total charges                |
| `tot_mdcr_pymt`             | float  | Total Medicare payment       |
| `avg_hha_pymt`              | float  | Avg payment per episode      |
| `tot_hha_vsit_cnt`          | int    | Total visits                 |
| `avg_hha_vsit_per_epsd`     | float  | Avg visits per episode       |

**Approximate Size**: ~15K rows/year (HHA-level)

**Years Available**: 2013–2022

**Fraud Detection Use Cases**:

- Home health is a major fraud vector, particularly in South Florida and Texas
- Visits per episode far exceeding clinical norms for diagnosis
- High ratio of skilled nursing visits without documented clinical need
- Agencies with 100% of patients meeting homebound criteria (statistical impossibility)
- Clustering of high-billing agencies in specific zip codes (fraud rings)
- Cross-reference with physician referrals to detect kickback networks

**Access**: Fully public.

---

### 1.7 Hospice Provider Utilization

**Official Name**: Medicare Hospice Providers — by Provider

**URL Pattern**:

```
https://data.cms.gov/provider-summary-by-type-of-service/medicare-hospice-providers/medicare-hospice-providers-by-provider
```

**Format**: CSV, REST API

**Key Columns**:

| Column                      | Type   | Fraud Relevance                            |
| --------------------------- | ------ | ------------------------------------------ |
| `rndrng_prvdr_ccn`          | string | Hospice CCN                                |
| `rndrng_prvdr_org_name`     | string | Hospice name                               |
| `rndrng_prvdr_state_abrvtn` | string | State                                      |
| `tot_benes`                 | int    | Total beneficiaries                        |
| `tot_days`                  | int    | Total covered days                         |
| `tot_mdcr_pymt`             | float  | Total Medicare payment                     |
| `avg_pymt_per_diem`         | float  | Avg per diem payment                       |
| `avg_days_per_bene`         | float  | Avg length of hospice stay                 |
| `bene_dschrg_alive_cnt`     | int    | Count discharged alive (revocation signal) |
| `bene_dth_cnt`              | int    | Count who died                             |

**Approximate Size**: ~5K rows/year

**Years Available**: 2014–2022

**Fraud Detection Use Cases**:

- Enrolling non-terminal patients in hospice for per-diem payments
- High discharge-alive rate (inappropriate admissions)
- Extremely long average stays inconsistent with terminal prognosis
- "Live discharge" rate far above national average
- Geographic clustering in specific metro areas (organized fraud)

**Access**: Fully public.

---

### 1.8 Skilled Nursing Facility (SNF) Utilization

**Official Name**: Medicare Skilled Nursing Facilities — by Provider

**URL Pattern**:

```
https://data.cms.gov/provider-summary-by-type-of-service/medicare-skilled-nursing-facility/medicare-skilled-nursing-facility-by-provider
```

**Format**: CSV, REST API

**Key Columns**:

| Column                      | Type   | Fraud Relevance                  |
| --------------------------- | ------ | -------------------------------- |
| `rndrng_prvdr_ccn`          | string | SNF CMS CCN                      |
| `rndrng_prvdr_org_name`     | string | Facility name                    |
| `rndrng_prvdr_state_abrvtn` | string | State                            |
| `tot_benes`                 | int    | Total beneficiaries              |
| `tot_mdcr_stdy_days`        | int    | Total Medicare covered days      |
| `tot_mdcr_pymt`             | float  | Total Medicare payment           |
| `avg_pymt_per_epsd`         | float  | Avg payment per episode          |
| `avg_day_per_bene`          | float  | Avg covered days per beneficiary |

**Approximate Size**: ~15K rows/year

**Years Available**: 2011–2022

**Fraud Detection Use Cases**:

- Billing maximum covered days regardless of patient improvement
- Upcoding therapy minutes to hit higher Resource Utilization Group (RUG) tiers
- Billing for therapy sessions never rendered
- Cross-reference: SNF owned by same entity as referring hospital

**Access**: Fully public.

---

## 2. LEIE — OIG Exclusion Database

**Official Name**: List of Excluded Individuals and Entities (LEIE)

**Source**: Office of Inspector General, HHS

**URL**:

```
https://oig.hhs.gov/exclusions/exclusions_list.asp
https://oig.hhs.gov/exclusions/downloadables/UPDATED.csv
```

**Format**: CSV (monthly updated download), online search API

**Key Columns**:

| Column       | Type   | Fraud Relevance                                                |
| ------------ | ------ | -------------------------------------------------------------- |
| `LASTNAME`   | string | Individual surname                                             |
| `FIRSTNAME`  | string | First name                                                     |
| `MIDNAME`    | string | Middle name                                                    |
| `BUSNAME`    | string | Business/organization name                                     |
| `GENERAL`    | string | General exclusion type category                                |
| `SPECIALTY`  | string | Provider specialty                                             |
| `UPIN`       | string | Unique Physician Identification Number (legacy)                |
| `NPI`        | string | National Provider Identifier (populated for modern exclusions) |
| `DOB`        | date   | Date of birth                                                  |
| `ADDRESS`    | string | Street address                                                 |
| `CITY`       | string | City                                                           |
| `STATE`      | string | State                                                          |
| `ZIP`        | string | ZIP code                                                       |
| `EXCLTYPE`   | string | Exclusion type code (1128a-1128c, 1128b, etc.)                 |
| `EXCLDATE`   | date   | Date of exclusion                                              |
| `REINDATE`   | date   | Reinstatement date (if applicable)                             |
| `WAIVERDATE` | date   | Waiver date (if applicable)                                    |
| `WVRSTATE`   | string | State of waiver                                                |

**Exclusion Type Codes** (critical for understanding severity):

| Code      | Meaning                                                 |
| --------- | ------------------------------------------------------- |
| 1128a(1)  | Conviction for program-related crimes — mandatory       |
| 1128a(2)  | Conviction for patient abuse/neglect — mandatory        |
| 1128a(3)  | Felony conviction for health care fraud — mandatory     |
| 1128a(4)  | Felony conviction for controlled substances — mandatory |
| 1128b(4)  | License revocation/suspension — permissive              |
| 1128b(6)  | False claims act — permissive                           |
| 1128b(15) | Ordering/prescribing while excluded — permissive        |

**Approximate Size**: ~76,000 active exclusions as of 2024; full file ~500K rows including historical reinstatements.

**Fraud Detection Use Cases**:

- **Primary use: fraud labels.** Any CMS provider billing while excluded is committing fraud.
- Join on NPI to flag excluded providers still appearing in utilization data (billing-while-excluded detection)
- Exclusion type distribution analysis (what crimes lead to exclusion in each specialty)
- Time-to-exclusion analysis (how long between first anomaly and exclusion)
- Geographic hot spots of excluded providers
- Reinstatement patterns (recidivism analysis)
- Negative label generation for supervised models: excluded providers are near-certain fraud positives

**Critical Caveat**: NPI is only populated for exclusions post ~2010. Earlier records require fuzzy name + DOB matching to join to NPI registry. The LEIE does NOT contain NPIs for entities (businesses), only individuals.

**Access**: Fully public, no registration required. Monthly update cycle.

---

## 3. Open Payments (Sunshine Act)

**Official Name**: Open Payments — Physician Payments Sunshine Act Data

**Source**: CMS

**URL**:

```
https://openpaymentsdata.cms.gov/
https://openpaymentsdata.cms.gov/datasets
```

**Format**: CSV (separate files per payment category per year), REST API

**Three Payment Categories**:

### 3a. General Payments

Direct payments from pharmaceutical/device companies to physicians: meals, speaking fees, consulting, travel, education.

**Key Columns**:

| Column                                                      | Type   | Fraud Relevance                  |
| ----------------------------------------------------------- | ------ | -------------------------------- |
| `physician_profile_id`                                      | string | CMS physician profile ID         |
| `physician_first_name`                                      | string | Name                             |
| `physician_npi`                                             | string | NPI (not always populated)       |
| `physician_specialty`                                       | string | Specialty                        |
| `physician_license_state_code_1`                            | string | License state                    |
| `submitting_applicable_manufacturer_or_applicable_gpo_name` | string | Paying company                   |
| `total_amount_of_payment_usdollars`                         | float  | Payment amount                   |
| `date_of_payment`                                           | date   | Payment date                     |
| `number_of_payments_included_in_total_amount`               | int    | Count of payments                |
| `form_of_payment_or_transfer_of_value`                      | string | Cash, in-kind, etc.              |
| `nature_of_payment_or_transfer_of_value`                    | string | Speaking, consulting, food, etc. |
| `name_of_drug_or_biological_or_device_or_medical_supply_1`  | string | Product name — JOIN to Part D    |
| `product_category_or_therapeutic_area_1`                    | string | Therapeutic category             |

### 3b. Research Payments

Payments tied to research studies. Lower fraud signal but useful for network analysis.

### 3c. Ownership & Investment Interests

Financial interests (stock, ownership) in reporting entities.

**Key Columns**:

| Column                                                      | Type   | Fraud Relevance    |
| ----------------------------------------------------------- | ------ | ------------------ |
| `physician_profile_id`                                      | string | Profile ID         |
| `physician_npi`                                             | string | NPI                |
| `total_amount_invested_usdollars`                           | float  | Investment amount  |
| `value_of_interest`                                         | float  | Current value      |
| `interest_held_by_physician_or_an_immediate_family_member`  | string | Who holds interest |
| `submitting_applicable_manufacturer_or_applicable_gpo_name` | string | Company            |

**Approximate Size**:

- General payments: ~13M rows/year
- Research payments: ~400K rows/year
- Ownership interests: ~50K rows/year

**Years Available**: 2013–2022 (program started August 2013)

**Fraud Detection Use Cases**:

- **Kickback detection**: Physician receives large payments from Company X → prescribes/uses Company X products at anomalously high rates
- Cross-reference Open Payments with Part D: does payment amount correlate with prescription volume for that drug?
- "Pill mill" enhancement: opioid prescribers receiving speaking fees from opioid manufacturers
- Device-procedure correlation: orthopedic surgeon receiving device company payments bills abnormally high implant volume
- Ownership interest → self-referral (Stark Law) violation signal
- Network construction: company → physician → beneficiary payment flows

**Critical Note**: NPI is not always populated in Open Payments. CMS uses a "physician profile ID" system. A crosswalk file is available at openpaymentsdata.cms.gov linking profile IDs to NPIs.

**Access**: Fully public, no registration required.

---

## 4. NPPES — NPI Registry

**Official Name**: National Plan and Provider Enumeration System (NPPES) — NPI Registry

**Source**: CMS

**URL**:

```
https://download.cms.gov/nppes/NPI_Files.html
https://download.cms.gov/nppes/NPPI_Data_Dissemination_<Month>_<Year>.zip
```

**Format**: CSV (full replacement file monthly, weekly incremental updates)

**File Structure**: The monthly full dissemination download is a ZIP containing:

- `npidata_pfile_<date>-<date>.csv` — main NPI data (~7GB uncompressed)
- `endpoint_pfile_<date>-<date>.csv` — electronic endpoint data
- `othername_pfile_<date>-<date>.csv` — other name data for organizations
- `pl_pfile_<date>-<date>.csv` — practice location data

**Key Columns in Main File**:

| Column                                                         | Type   | Fraud Relevance                     |
| -------------------------------------------------------------- | ------ | ----------------------------------- |
| `NPI`                                                          | string | 10-digit NPI — universal JOIN key   |
| `Entity_Type_Code`                                             | int    | 1=Individual, 2=Organization        |
| `Provider_Last_Name_(Legal_Name)`                              | string | Surname                             |
| `Provider_First_Name`                                          | string | First name                          |
| `Provider_Middle_Name`                                         | string | Middle name                         |
| `Provider_Credential_Text`                                     | string | Credentials (MD, DO, NP, etc.)      |
| `Provider_First_Line_Business_Practice_Location_Address`       | string | Practice street                     |
| `Provider_Business_Practice_Location_Address_City_Name`        | string | City                                |
| `Provider_Business_Practice_Location_Address_State_Name`       | string | State                               |
| `Provider_Business_Practice_Location_Address_Postal_Code`      | string | ZIP                                 |
| `Provider_Business_Practice_Location_Address_Telephone_Number` | string | Phone                               |
| `Healthcare_Provider_Taxonomy_Code_1`                          | string | Primary specialty taxonomy          |
| `Healthcare_Provider_Taxonomy_Code_2`                          | string | Secondary taxonomy (up to 15 slots) |
| `Provider_License_Number_1`                                    | string | State license number                |
| `Provider_License_Number_State_Code_1`                         | string | License state                       |
| `NPI_Deactivation_Reason_Code`                                 | string | Why NPI was deactivated             |
| `NPI_Deactivation_Date`                                        | date   | Deactivation date                   |
| `NPI_Reactivation_Date`                                        | date   | Reactivation date                   |
| `Is_Sole_Proprietor`                                           | string | Sole proprietor flag                |
| `Is_Organization_Subpart`                                      | string | Subpart flag                        |
| `Parent_Organization_LBN`                                      | string | Parent organization name            |
| `Parent_Organization_TIN`                                      | string | Parent organization TIN             |

**Approximate Size**: ~8M active NPIs in the current file (~7GB CSV uncompressed)

**Years Available**: Current snapshot only (monthly replacement). Historical snapshots are not systematically archived by CMS but can be derived from utilization data join coverage.

**Fraud Detection Use Cases**:

- **Universal JOIN key**: Every other dataset joins to NPI. This is the backbone.
- Specialty verification: provider bills HCPCS codes outside their taxonomy specialty
- Geographic verification: provider bills services in state where they have no license
- Deactivated NPI billing: NPI was deactivated but still appears in claims
- Deceased provider billing: cross-reference with SSA death master file (requires additional source)
- Sole proprietor flag: high-volume sole proprietors with no employees are a fraud signal
- Name/credential mismatch between NPPES and billing records

**Access**: Fully public, no registration. Monthly full downloads from CMS download site (~1.5GB compressed ZIP).

---

## 5. Kaggle Labeled Datasets

### 5.1 Healthcare Provider Fraud Detection Analysis

**Dataset Name**: Healthcare Provider Fraud Detection Analysis

**Source**: Kaggle

**URL**:

```
https://www.kaggle.com/datasets/rohitrox/healthcare-provider-fraud-detection-analysis
```

**Format**: CSV (4 files)

**Files**:

| File                                      | Rows (approx) | Description                            |
| ----------------------------------------- | ------------- | -------------------------------------- |
| `Train-1542865627584.csv`                 | ~5,000 rows   | Provider-level with binary fraud label |
| `Train_Beneficiarydata-1542865627584.csv` | ~138,000 rows | Beneficiary demographics               |
| `Train_Inpatientdata-1542865627584.csv`   | ~40,000 rows  | Inpatient claims                       |
| `Train_Outpatientdata-1542865627584.csv`  | ~517,000 rows | Outpatient claims                      |

**Key Columns — Provider Labels File**:

| Column           | Values                  | Notes              |
| ---------------- | ----------------------- | ------------------ |
| `Provider`       | Provider ID (synthetic) | JOIN key to claims |
| `PotentialFraud` | Yes/No                  | Binary fraud label |

**Key Columns — Claims Files**:

| Column                     | Type   | Notes                           |
| -------------------------- | ------ | ------------------------------- |
| `BeneID`                   | string | Beneficiary ID                  |
| `ClaimID`                  | string | Claim ID                        |
| `ClaimStartDt`             | date   | Service start                   |
| `ClaimEndDt`               | date   | Service end                     |
| `Provider`                 | string | Provider ID                     |
| `InscClaimAmtReimbursed`   | float  | Amount reimbursed               |
| `AttendingPhysician`       | string | Attending physician ID          |
| `OperatingPhysician`       | string | Operating physician ID          |
| `OtherPhysician`           | string | Other physician ID              |
| `AdmissionDt`              | date   | Admission date (inpatient only) |
| `ClmDiagnosisCode_1`-`_10` | string | ICD-10 diagnosis codes          |
| `ClmProcedureCode_1`-`_6`  | string | ICD-10 procedure codes          |
| `ClmAdmitDiagnosisCode`    | string | Admitting diagnosis             |
| `DeductibleAmtPaid`        | float  | Beneficiary deductible paid     |
| `IPAnnualDeductibleAmt`    | float  | Inpatient annual deductible     |
| `IPAnnualReimbursementAmt` | float  | Annual inpatient reimbursement  |
| `OPAnnualDeductibleAmt`    | float  | Outpatient annual deductible    |
| `OPAnnualReimbursementAmt` | float  | Annual outpatient reimbursement |

**Key Columns — Beneficiary File**:

| Column                            | Type   | Notes                         |
| --------------------------------- | ------ | ----------------------------- |
| `BeneID`                          | string | Beneficiary ID                |
| `DOB`                             | date   | Date of birth                 |
| `DOD`                             | date   | Date of death (if applicable) |
| `Gender`                          | int    | 1=Male, 2=Female              |
| `Race`                            | int    | Race code                     |
| `RenalDiseaseIndicator`           | string | ESRD flag                     |
| `State`                           | int    | State code                    |
| `County`                          | int    | County code                   |
| `NoOfMonths_PartACvrd`            | int    | Part A coverage months        |
| `NoOfMonths_PartBCvrd`            | int    | Part B coverage months        |
| `ChronicCond_Alzheimer`           | int    | Alzheimer flag                |
| `ChronicCond_Heartfailure`        | int    | Heart failure flag            |
| `ChronicCond_KidneyDisease`       | int    | Kidney disease flag           |
| `ChronicCond_Cancer`              | int    | Cancer flag                   |
| `ChronicCond_ObstrPulmonary`      | int    | COPD flag                     |
| `ChronicCond_Depression`          | int    | Depression flag               |
| `ChronicCond_Diabetes`            | int    | Diabetes flag                 |
| `ChronicCond_IschemicHeart`       | int    | Ischemic heart disease flag   |
| `ChronicCond_Osteoporasis`        | int    | Osteoporosis flag             |
| `ChronicCond_rheumatoidArthritis` | int    | RA flag                       |
| `ChronicCond_stroke`              | int    | Stroke flag                   |

**Fraud Detection Use Cases**:

- **Only widely used labeled dataset for Medicare fraud** — this is the standard benchmark
- Supervised classification: XGBoost/RF/neural net with binary fraud label
- Feature engineering: aggregate claims to provider level, join beneficiary comorbidities
- Anomaly detection baseline: train on non-fraud providers, score all
- Benchmark for model comparison

**Critical Caveats**:

- Synthetic dataset derived from real Medicare patterns — NOT real CMS data
- Provider-level labels only (not claim-level): "this provider is fraudulent" not "this claim is fraudulent"
- Label generation methodology is not fully disclosed; treat as approximate
- Class imbalance: ~10% fraud rate at provider level
- Small scale (~5K providers) vs. real Medicare (~1.1M providers)
- No temporal dimension — all claims appear concurrent
- Use for prototyping and benchmarking ONLY; do not use for real fraud detection conclusions

**Access**: Free, requires Kaggle account.

---

### 5.2 Other Kaggle Datasets of Note

**Medicare Part D Opioid Prescriber Summary**:

```
https://www.kaggle.com/datasets/cms/cms-medicare-part-d-opioid-prescribers-by-provider
```

This is a rehost of the official CMS Part D opioid dataset. Same data as section 1.2, with opioid columns prefiltered.

**CMS Medicare Provider Utilization and Payment Data**:

```
https://www.kaggle.com/datasets/cms/cms-medicare-physician-supplier-procedures-2015
```

Rehost of Part B by Provider & Service for 2015. Convenient for experimentation but use official source for production.

---

## 6. CMS DE-SynPUF — Synthetic Medicare Claims

**Official Name**: CMS 2008–2010 Data Entrepreneurs' Synthetic Public Use File (DE-SynPUF)

**Source**: CMS

**URL**:

```
https://www.cms.gov/Research-Statistics-Data-and-Systems/Downloadable-Public-Use-Files/SynPUFs/DE_Syn_PUF
```

**Format**: CSV (20 sample files, each representing 5% of Medicare beneficiaries)

**Files Per Sample**:

| File Type                | Description                                                         |
| ------------------------ | ------------------------------------------------------------------- |
| Beneficiary Summary      | Beneficiary demographics, chronic conditions, Part A/B/D enrollment |
| Inpatient Claims         | Inpatient facility claims with diagnosis/procedure codes            |
| Outpatient Claims        | Outpatient facility claims                                          |
| Carrier Claims           | Part B physician/supplier claims (equivalent to MEDPAR carrier)     |
| Prescription Drug Events | Part D drug events                                                  |

**Key Columns — Beneficiary**:

| Column              | Type   | Notes                         |
| ------------------- | ------ | ----------------------------- |
| `DESYNPUF_ID`       | string | Synthetic beneficiary ID      |
| `BENE_BIRTH_DT`     | date   | Date of birth                 |
| `BENE_DEATH_DT`     | date   | Date of death (if applicable) |
| `BENE_SEX_IDENT_CD` | int    | Sex                           |
| `BENE_RACE_CD`      | int    | Race                          |
| `SP_ALZHDMTA`       | int    | Alzheimer's/dementia flag     |
| `SP_CHF`            | int    | Heart failure flag            |
| `SP_CHRNKIDN`       | int    | Chronic kidney disease flag   |
| `SP_CNCR`           | int    | Cancer flag                   |
| `SP_COPD`           | int    | COPD flag                     |
| `SP_DEPRESSN`       | int    | Depression flag               |
| `SP_DIABETES`       | int    | Diabetes flag                 |
| `SP_ISCHMCHT`       | int    | Ischemic heart disease flag   |
| `SP_OSTEOPRS`       | int    | Osteoporosis flag             |
| `SP_RA_OA`          | int    | RA/OA flag                    |
| `SP_STRKETIA`       | int    | Stroke/TIA flag               |

**Key Columns — Inpatient Claims**:

| Column                           | Type   | Notes                   |
| -------------------------------- | ------ | ----------------------- |
| `DESYNPUF_ID`                    | string | Beneficiary ID          |
| `CLM_ID`                         | string | Claim ID                |
| `SEGMENT`                        | int    | Claim segment           |
| `CLM_FROM_DT`                    | date   | Service start           |
| `CLM_THRU_DT`                    | date   | Service end             |
| `PRVDR_NUM`                      | string | Provider number (CCN)   |
| `CLM_PMT_AMT`                    | float  | Payment amount          |
| `CLM_PASS_THRU_PER_DIEM_AMT`     | float  | Per diem amount         |
| `NCH_BENE_IP_DDCTBL_AMT`         | float  | Inpatient deductible    |
| `NCH_BENE_PTA_COINSRNC_LBLTY_AM` | float  | Part A coinsurance      |
| `NCH_BENE_BLOOD_DDCTBL_LBLTY_AM` | float  | Blood deductible        |
| `CLM_UTLZTN_DAY_CNT`             | int    | Utilization day count   |
| `NCH_BENE_DSCHRG_DT`             | date   | Discharge date          |
| `CLM_DRG_CD`                     | string | DRG code                |
| `ICD9_DGNS_CD_1`-`_10`           | string | ICD-9 diagnosis codes   |
| `ICD9_PRCDR_CD_1`-`_6`           | string | ICD-9 procedure codes   |
| `HCPCS_CD_1`-`_45`               | string | HCPCS codes on claim    |
| `AT_PHYSN_NPI`                   | string | Attending physician NPI |
| `OP_PHYSN_NPI`                   | string | Operating physician NPI |
| `OT_PHYSN_NPI`                   | string | Other physician NPI     |

**Approximate Size**:

- 20 samples × 116,352 beneficiaries = ~2.3M synthetic beneficiaries total
- Inpatient: ~150K records per sample
- Outpatient: ~500K records per sample
- Carrier (Part B): ~1.5M records per sample

**Years Covered**: 2008–2010 (3-year longitudinal follow-up per beneficiary)

**Fraud Detection Use Cases**:

- Schema prototyping: understand real Medicare claim structure before working with real data
- Pipeline development: build ingest/feature/model pipeline without DUA
- Algorithm testing: test anomaly detection on plausible distributions
- Education and teaching

**Critical Caveats**:

- Synthetic data generated from real Medicare microdata — NOT actual claims
- Statistical properties approximate real data but edge cases are missing
- Fraud signals are NOT embedded — there are no fraudulent patterns to detect
- ICD-9 codes (real Medicare now uses ICD-10)
- 2008–2010 vintage — reimbursement rates and codes are outdated
- Do NOT use for real fraud detection, policy analysis, or publication without prominent disclaimer
- CMS specifically warns: "SynPUF should NOT be used as a substitute for actual Medicare data"

**Access**: Fully public, no DUA required. However, access to real CMS Medicare microdata (RESDAC) requires a DUA and approved research protocol — do not conflate.

---

## 7. Supporting Reference Datasets

### 7.1 HCPCS / CPT Code Reference

**Official Name**: Healthcare Common Procedure Coding System (HCPCS) Code Files

**Source**: CMS

**URL**:

```
https://www.cms.gov/Medicare/Coding/HCPCSReleaseCodeSets/Alpha-Numeric-HCPCS
```

**Format**: ZIP containing TXT/CSV and Excel files

**Key Files**:

- `HCPC<year>.xlsx` — full HCPCS Level II code set with descriptions
- `ANWEB<year>.txt` — addenda for new/revised/deleted codes

**Key Columns**:

| Column                 | Type   | Notes                       |
| ---------------------- | ------ | --------------------------- |
| `HCPC`                 | string | 5-character HCPCS code      |
| `SEQNUM`               | string | Sequence number             |
| `RECID`                | string | Record ID                   |
| `LONG_DESCRIPTION`     | string | Full code description       |
| `SHORT_DESCRIPTION`    | string | Abbreviated description     |
| `PRICE_EFFECTIVE_DATE` | date   | Effective date              |
| `COVERAGE_CODE`        | string | Medicare coverage status    |
| `ACTION_CODE`          | string | N=new, R=revised, D=deleted |

**CPT codes** (Level I HCPCS) are owned by the AMA and NOT freely available. The CMS HCPCS file only covers Level II (non-physician services: DMEPOS, drugs, ambulance). For CPT descriptions, use CMS Medicare Physician Fee Schedule lookup or purchase AMA license.

**Fraud Detection Use Cases**:

- Decode HCPCS codes in all utilization datasets for human-readable explanations
- Identify deleted codes being billed (billing discontinued codes)
- Coverage code filtering: flag billing for non-covered services as possible upcoding
- Map HCPCS to revenue center codes for APC/DRG consistency checks

**Access**: Fully public.

---

### 7.2 PECOS — Provider Enrollment Chain and Ownership System

**Official Name**: Medicare Enrollment Data — PECOS Public Data Extract

**Source**: CMS / data.cms.gov

**URL**:

```
https://data.cms.gov/provider-characteristics/medicare-provider-supplier-enrollment/medicare-fee-for-service-public-provider-enrollment
```

**Format**: CSV, REST API

**Key Columns**:

| Column                 | Type   | Fraud Relevance                               |
| ---------------------- | ------ | --------------------------------------------- |
| `NPI`                  | string | NPI                                           |
| `PECOS_ASSGN`          | string | Medicare assignment status                    |
| `ENRLMT_ID`            | string | Enrollment ID                                 |
| `PROVIDER_TYPE_CODE`   | string | Provider type (taxonomy-adjacent)             |
| `PROVIDER_TYPE_TEXT`   | string | Human-readable provider type                  |
| `STATE_CD`             | string | State of enrollment                           |
| `ENRLMT_STUS_EFCTV_DT` | date   | Enrollment effective date                     |
| `ENRLMT_END_DT`        | date   | Enrollment end date                           |
| `MDCR_STUS_CD`         | string | Medicare status code                          |
| `IND_PAC_ID`           | string | Individual PAC ID (Physician Aligned Care ID) |
| `IND_ASSGN_CD`         | string | Assignment code                               |
| `GRP_PAC_ID`           | string | Group PAC ID                                  |
| `GRP_ENRLMT_ID`        | string | Group enrollment ID                           |
| `ORG_NM`               | string | Organization name                             |

**Approximate Size**: ~4M rows (active + recent historical enrollments)

**Fraud Detection Use Cases**:

- Verify provider is actively enrolled before flagging billing anomalies
- Detect billing by providers with lapsed or never-enrolled status
- Identify providers enrolled under one specialty billing under another
- Group/individual enrollment chain: detect shell organizations
- Enrollment effective date vs. first billing date: billing before enrollment = fraud signal
- Multiple enrollment changes in short period = instability signal

**Access**: Fully public extract available. Full PECOS system is not public.

---

### 7.3 Area Health Resource File (AHRF)

**Official Name**: Area Health Resources Files (AHRF)

**Source**: Health Resources & Services Administration (HRSA)

**URL**:

```
https://data.hrsa.gov/topics/health-workforce/ahrf
```

**Format**: CSV (county-level), SAS transport format

**Key Columns** (county-level contextual data):

| Column     | Category     | Fraud Relevance                               |
| ---------- | ------------ | --------------------------------------------- |
| `F12424`   | Population   | County population (denominator normalization) |
| `F1482860` | Physicians   | Active patient care MDs per 100K              |
| `F1481860` | Specialists  | Specialist counts by type                     |
| `F0892011` | Poverty      | Percent below poverty line                    |
| `F1198011` | Unemployment | Unemployment rate                             |
| `F0021017` | Rural        | Rural-urban continuum code                    |
| `FIPS`     | Geography    | 5-digit county FIPS code                      |

**Fraud Detection Use Cases**:

- Normalize provider billing volume by local market density
- Rural vs. urban adjustment for what constitutes an outlier
- Poverty index as confounder for billing patterns
- Access to care context: areas with few physicians may explain unusual referral patterns
- Peer group construction: compare providers to others in similar market conditions

**Access**: Free download after brief registration on HRSA data portal.

---

### 7.4 Hospital Compare

**Official Name**: Hospital Compare — Hospital General Information

**Source**: CMS / data.cms.gov / Medicare Care Compare

**URL**:

```
https://data.cms.gov/provider-data/dataset/xubh-q36u
https://data.cms.gov/provider-data/sites/default/files/resources/092a4b99c7a62e17f9eba2aeeb00b8d7_1700168706/Hospital_General_Information.csv
```

**Format**: CSV, REST API

**Key Columns**:

| Column                               | Type    | Notes                                          |
| ------------------------------------ | ------- | ---------------------------------------------- |
| `Facility ID`                        | string  | CMS Certification Number (CCN)                 |
| `Facility Name`                      | string  | Hospital name                                  |
| `Address`                            | string  | Street address                                 |
| `City/Town`                          | string  | City                                           |
| `State`                              | string  | State                                          |
| `ZIP Code`                           | string  | ZIP                                            |
| `County/Parish`                      | string  | County                                         |
| `Phone Number`                       | string  | Phone                                          |
| `Hospital Type`                      | string  | Acute Care, Critical Access, Psychiatric, etc. |
| `Hospital Ownership`                 | string  | Government, Proprietary, Voluntary non-profit  |
| `Emergency Services`                 | string  | Yes/No                                         |
| `Hospital overall rating`            | int     | 1–5 star quality rating                        |
| `HCAHPS Patient Survey`              | various | Patient experience scores                      |
| `Mortality national comparison`      | string  | Better/Same/Worse than national rate           |
| `Safety of Care national comparison` | string  | Safety score comparison                        |
| `Readmission national comparison`    | string  | Readmission score comparison                   |

**Approximate Size**: ~5,000 hospitals

**Fraud Detection Use Cases**:

- Hospital ownership type: proprietary hospitals have higher historical fraud rates
- Quality score as anomaly context: poor quality + high billing = risk signal
- Hospital type verification: critical access hospital billing non-eligible services
- Readmission rates: unusually low rates with high volumes may indicate cherry-picking
- Emergency services flag: cross-reference with emergency admission billing

**Access**: Fully public.

---

### 7.5 Care Compare — Physician Compare (Successor)

**Official Name**: Physician Compare Initiative / Medicare Care Compare Physician Data

**Source**: CMS

**URL**:

```
https://data.cms.gov/provider-data/dataset/mj5m-pzi6
```

**Format**: CSV, REST API

**Key Columns**:

| Column                             | Type   | Notes                          |
| ---------------------------------- | ------ | ------------------------------ |
| `NPI`                              | string | NPI                            |
| `PAC ID`                           | string | PAC ID                         |
| `Professional Enrollment ID`       | string | Enrollment ID                  |
| `Last Name`                        | string | Provider last name             |
| `First Name`                       | string | Provider first name            |
| `Middle Name`                      | string | Middle name                    |
| `Suffix`                           | string | Suffix (Jr., Sr., etc.)        |
| `Gender`                           | string | M/F                            |
| `Credential`                       | string | MD, DO, NP, PA, etc.           |
| `Medical school name`              | string | Medical school                 |
| `Graduation year`                  | int    | Medical school graduation year |
| `Primary specialty`                | string | Board specialty                |
| `Secondary specialty 1`–`4`        | string | Additional specialties         |
| `Organization legal name`          | string | Practice name                  |
| `Group Practice PAC ID`            | string | Group PAC ID                   |
| `Number of Group Practice members` | int    | Group size                     |
| `Line 1 Street Address`            | string | Practice address               |
| `City`                             | string | City                           |
| `State`                            | string | State                          |
| `Zip Code`                         | string | ZIP                            |
| `Phone Number`                     | string | Phone                          |
| `Hospital affiliation CCN 1`–`5`   | string | Hospital affiliations          |
| `Reported Quality Measures`        | string | Quality measure participation  |

**Approximate Size**: ~1M physician records

**Fraud Detection Use Cases**:

- Specialty verification: primary specialty vs. HCPCS codes billed
- Board certification as risk modifier
- Group size as context: solo practitioners vs. large groups have different fraud profiles
- Hospital affiliations: billing for hospital services without affiliation
- Years in practice: very new providers with very high billing volume

**Access**: Fully public.

---

### 7.6 Medicare Advantage Plan Data

**Official Name**: Medicare Advantage Enrollment and Plan Data

**Source**: CMS

**URL**:

```
https://www.cms.gov/Research-Statistics-Data-and-Systems/Statistics-Trends-and-Reports/MCRAdvPartDEnrolData
```

**Format**: CSV, ZIP

**Fraud Detection Use Cases**:

- Market context: areas with high Medicare Advantage penetration have different FFS billing patterns
- Risk adjustment fraud: MA plans submit diagnoses to inflate risk scores (different fraud type — not covered by FFS datasets)
- Coverage gap analysis: FFS billing in high-MA areas

**Access**: Fully public.

---

## 8. Join Key Architecture

The NPI is the universal join key across all public CMS datasets. The following diagram shows how datasets link together:

```
NPPES (NPI Registry)
│   NPI → all demographic, specialty, location attributes
│
├──── Part B Utilization (rndrng_npi)
│         ↓ hcpcs_cd
│         → HCPCS Reference (code descriptions)
│
├──── Part D Prescriber (prscrbr_npi)
│
├──── DMEPOS (rndrng_npi)
│
├──── Open Payments (physician_npi)
│         ↓ drug/device name
│         → cross-reference to Part D drugs prescribed
│
├──── LEIE (npi — join with caveats)
│         → FRAUD LABELS for supervised learning
│
├──── PECOS (NPI)
│         → enrollment status, enrollment dates
│
└──── Care Compare (NPI)
          → specialty board certification, group affiliation

Hospital-level datasets join on CCN (CMS Certification Number):
  - Inpatient (rndrng_prvdr_ccn)
  - Outpatient (rndrng_prvdr_ccn)
  - Home Health (rndrng_prvdr_ccn)
  - SNF (rndrng_prvdr_ccn)
  - Hospital Compare (Facility ID = CCN)

Beneficiary-level (requires DUA — not in public data):
  - RESDAC Medicare claims (BeneID, HICN, MBI)
  - SynPUF (DESYNPUF_ID — synthetic only)
  - Kaggle dataset (BeneID — synthetic only)
```

---

## 9. Recommended Download Order

For the cms-fraud-detection project, download and process in this order to build a working pipeline:

### Phase 1: Reference Tables (small, fast, required for joins)

1. **NPPES NPI Registry** — the backbone JOIN key (~1.5GB ZIP)
2. **HCPCS Code Reference** — decode all procedure codes (~10MB)
3. **LEIE Exclusion List** — fraud labels (~5MB CSV)
4. **PECOS Enrollment** — active enrollment verification (~200MB)

### Phase 2: Core Utilization Data (medium, primary signal source)

5. **Part B by Provider** — 2019–2022, provider-level aggregate (~500MB/year)
6. **Part B by Provider & Service** — 2019–2022, granular billing (~2GB/year)
7. **Part D by Provider** — 2019–2022, prescribing patterns (~800MB/year)
8. **DMEPOS** — 2019–2022, high-fraud category (~300MB/year)

### Phase 3: Enrichment Data (adds network and quality context)

9. **Open Payments General** — 2019–2022, kickback signals (~2GB/year)
10. **Care Compare Physicians** — specialty verification (~100MB)
11. **Hospital Compare** — facility quality scores (~10MB)

### Phase 4: Specialty Care (if in scope)

12. **Home Health** — 2019–2022
13. **Hospice** — 2019–2022
14. **SNF** — 2019–2022
15. **Inpatient / Outpatient** — 2019–2022

### Phase 5: Labeled Training Data

16. **Kaggle Healthcare Provider Fraud Detection** — for initial model prototyping only
17. **SynPUF** — for pipeline schema testing only

---

## Key Notes for This Project

### What We Have vs. What We Need

| What Public Data Gives Us       | What Requires DUA / Not Available  |
| ------------------------------- | ---------------------------------- |
| Provider-level aggregates       | Individual claim-level data        |
| Suppressed cells (<11 services) | All claims regardless of volume    |
| Annual snapshots                | Real-time or monthly claims        |
| Payment amounts                 | Diagnosis codes at claim level     |
| LEIE exclusion as fraud label   | CMS internal fraud case database   |
| Billing patterns                | Actual fraudulent claim indicators |

### Suppression Problem

The most important limitation of all public utilization data is the **11-service suppression threshold**. Any provider-HCPCS combination with fewer than 11 services in a year is suppressed. This means:

- Rare services are invisible
- New providers (first year) have sparse data
- Small-volume fraudsters may be entirely hidden
- Mitigation: use provider-level aggregates (not service-level) where suppression is less severe

### Label Scarcity

Fraud labels from LEIE are a necessary approximation. Key caveats:

- LEIE captures exclusions, not indictments — many fraudsters are never excluded
- Time lag: exclusion can occur years after fraud
- Survivorship: active fraudsters not yet caught are in the non-fraud class (noisy negatives)
- Recommendation: treat as positive label set only; use anomaly detection as primary method, supervised learning as secondary

### Temporal Join Strategy

CMS releases data ~18 months after service year. For a 2024 model:

- Most recent available data: 2022 service year
- LEIE: monthly updates (current)
- NPPES: monthly updates (current)
- Strategy: train on 2019–2021 utilization, validate on 2022, use current LEIE for labels

---

_This catalog represents dataset knowledge as of August 2025. CMS releases new service years annually. Check data.cms.gov for the latest available years._
