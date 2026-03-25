"""System prompts and few-shot examples for AI features.

Contains the PostgreSQL schema description and few-shot NL→SQL pairs
used by the text-to-SQL engine, plus the risk narrative prompt.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Database schema description for text-to-SQL
# ---------------------------------------------------------------------------

SCHEMA_DESCRIPTION = """\
You are an expert SQL analyst for CMS Medicare fraud detection. You translate
natural language questions into PostgreSQL queries against the following schema.

## Tables

### provider_service_cases
One row per provider-service pair (NPI + HCPCS code). Contains billing data,
peer comparison z-scores, and seed risk scores.

Key columns:
- case_id (TEXT PK) — unique identifier
- npi (TEXT) — National Provider Identifier (10 digits)
- provider_last_org_name (TEXT) — provider or organization name
- provider_first_name (TEXT) — individual provider first name
- provider_entity_code (TEXT) — 'I' = individual, 'O' = organization
- provider_city, provider_state, provider_zip5 (TEXT) — location
- provider_type (TEXT) — specialty (e.g. 'Internal Medicine', 'Clinical Laboratory')
- medicare_participating_ind (TEXT) — 'Y' if accepts Medicare assignment
- hcpcs_cd (TEXT) — procedure code (e.g. '99213', '90471')
- hcpcs_desc (TEXT) — procedure description
- place_of_service (TEXT) — 'F' = facility, 'O' = office
- tot_benes (FLOAT) — total Medicare beneficiaries served
- tot_srvcs (FLOAT) — total services performed
- tot_bene_day_srvcs (FLOAT) — total beneficiary-day services
- avg_submitted_charge (FLOAT) — average charge submitted per service
- avg_medicare_allowed_amt (FLOAT) — average Medicare allowed amount
- avg_medicare_payment_amt (FLOAT) — average Medicare payment per service
- estimated_case_payment_amt (FLOAT) — estimated total payment for this case
- services_per_bene (FLOAT) — services per beneficiary ratio
- submitted_to_allowed_ratio (FLOAT) — charge-to-allowed ratio (>1 means overcharging)
- present_in_2025_enrollment_file (INT) — 1 if currently enrolled
- present_in_2026_revocation_file (INT) — 1 if revoked
- revocation_reason_summary (TEXT) — reason for revocation
- peer_scope (TEXT) — peer group used for comparison
- peer_case_count (INT) — number of peers in comparison
- service_volume_peer_z (FLOAT) — z-score vs peers for service volume
- services_per_bene_peer_z (FLOAT) — z-score vs peers for intensity
- submitted_to_allowed_peer_z (FLOAT) — z-score vs peers for charge ratio
- payment_peer_z (FLOAT) — z-score vs peers for payment
- seed_risk_score (INT) — risk score 0-100
- seed_legitimacy_score (INT) — legitimacy score 0-100
- seed_case_label (TEXT) — 'high_risk', 'review', or 'stable'
- seed_risk_reasons (TEXT) — comma-separated risk signal names
- seed_legitimacy_reasons (TEXT) — comma-separated legitimacy signal names

### provider_features
One row per provider (NPI). Aggregated features across all service lines.

Key columns:
- npi (TEXT PK) — National Provider Identifier
- provider_name (TEXT) — display name
- entity_code (TEXT) — 'I' individual, 'O' organization
- city, state, zip5 (TEXT) — location
- provider_type (TEXT) — specialty
- medicare_participating (TEXT) — 'Y'/'N'
- enrolled_2025 (INT) — 1 if in current enrollment file
- revoked_2026 (INT) — 1 if in revocation file
- revocation_reason (TEXT) — revocation reason
- service_line_count (INT) — number of distinct service lines
- unique_hcpcs_codes (INT) — distinct procedure codes billed
- total_benes (FLOAT) — total unique beneficiaries
- total_services (FLOAT) — total services across all codes
- total_estimated_payment (FLOAT) — total estimated payment
- mean_submitted_charge (FLOAT) — average charge across lines
- max_submitted_charge (FLOAT) — highest charge for any line
- mean_payment_amt (FLOAT) — average payment across lines
- max_seed_risk_score (INT) — highest risk score across lines
- avg_seed_risk_score (FLOAT) — average risk score
- n_high_risk_lines (INT) — count of high-risk service lines
- mean_volume_z, max_volume_z (FLOAT) — peer z-scores for volume
- mean_charge_z, max_charge_z (FLOAT) — peer z-scores for charges
- service_hhi (FLOAT) — Herfindahl index (concentration, 0-1)
- top_code_share (FLOAT) — fraction of services from top code (0-1)
- risk_legitimacy_gap (INT) — gap between risk and legitimacy scores

### case_actions
Analyst actions taken on cases (approve, flag, deny, escalate).

Key columns:
- id (SERIAL PK)
- case_id (TEXT) — references a provider_service_cases case_id or a simulated case
- npi (TEXT) — the provider NPI
- action (TEXT) — 'APPROVED', 'FLAGGED', 'DENIED', 'ESCALATED'
- notes (TEXT) — analyst notes
- analyst_id (TEXT) — analyst who took the action (default 'system')
- created_at (TIMESTAMPTZ) — when the action was recorded

## Data Characteristics
- This is **annual aggregated** CMS Medicare billing data, NOT individual claims.
- There are NO date columns, timestamps, or claim submission dates in the billing tables.
- Each row in provider_service_cases is a provider's full-year summary for one procedure code.
- The data shows WHAT providers billed and HOW MUCH, not WHEN individual claims were submitted.
- The only timestamped data is case_actions (analyst investigation actions).

## Important Notes
- Risk scores: 0-30 = stable, 31-50 = review, 51+ = high_risk
- Z-scores: values > 2.0 indicate statistical outliers vs peers
- submitted_to_allowed_ratio > 1.0 means provider charges more than Medicare allows
- service_hhi close to 1.0 means highly concentrated billing (few codes)
- All monetary values are in USD
"""

# ---------------------------------------------------------------------------
# Few-shot examples for text-to-SQL
# ---------------------------------------------------------------------------

FEW_SHOT_EXAMPLES = [
    {
        "question": "How many providers are high risk?",
        "sql": (
            "SELECT count(*) AS high_risk_count "
            "FROM provider_features WHERE max_seed_risk_score > 50;"
        ),
    },
    {
        "question": "What are the top 10 highest risk providers?",
        "sql": (
            "SELECT npi, provider_name, provider_type, state, max_seed_risk_score, "
            "total_estimated_payment FROM provider_features "
            "ORDER BY max_seed_risk_score DESC LIMIT 10;"
        ),
    },
    {
        "question": "What is the average charge for procedure 99213?",
        "sql": (
            "SELECT avg(avg_submitted_charge) AS avg_charge, "
            "count(*) AS provider_count "
            "FROM provider_service_cases WHERE hcpcs_cd = '99213';"
        ),
    },
    {
        "question": "Which states have the most high-risk providers?",
        "sql": (
            "SELECT state, count(*) AS high_risk_count "
            "FROM provider_features WHERE max_seed_risk_score > 50 "
            "GROUP BY state ORDER BY high_risk_count DESC LIMIT 10;"
        ),
    },
    {
        "question": "Show me revoked providers in Florida",
        "sql": (
            "SELECT npi, provider_name, provider_type, revocation_reason "
            "FROM provider_features WHERE state = 'FL' AND revoked_2026 = 1 "
            "ORDER BY max_seed_risk_score DESC;"
        ),
    },
    {
        "question": "What does provider 1821387911 bill for?",
        "sql": (
            "SELECT hcpcs_cd, hcpcs_desc, tot_srvcs, tot_benes, "
            "avg_submitted_charge, seed_risk_score "
            "FROM provider_service_cases WHERE npi = '1821387911' "
            "ORDER BY tot_srvcs DESC;"
        ),
    },
    {
        "question": "Which providers have the highest services per beneficiary?",
        "sql": (
            "SELECT npi, provider_name, provider_type, state, "
            "avg_services_per_bene, max_seed_risk_score "
            "FROM provider_features WHERE total_benes > 10 "
            "ORDER BY avg_services_per_bene DESC LIMIT 10;"
        ),
    },
    {
        "question": "How many providers are in each risk band?",
        "sql": (
            "SELECT CASE "
            "WHEN max_seed_risk_score > 50 THEN 'high_risk' "
            "WHEN max_seed_risk_score > 30 THEN 'review' "
            "ELSE 'stable' END AS risk_band, "
            "count(*) AS provider_count "
            "FROM provider_features GROUP BY risk_band ORDER BY provider_count DESC;"
        ),
    },
    {
        "question": "What's the total estimated payment across all providers?",
        "sql": "SELECT sum(total_estimated_payment) AS total_payment FROM provider_features;",
    },
    {
        "question": "Show me providers who charge more than 3x the Medicare allowed amount",
        "sql": (
            "SELECT npi, provider_last_org_name, hcpcs_cd, hcpcs_desc, "
            "avg_submitted_charge, avg_medicare_allowed_amt, "
            "submitted_to_allowed_ratio, seed_risk_score "
            "FROM provider_service_cases "
            "WHERE submitted_to_allowed_ratio > 3.0 "
            "ORDER BY submitted_to_allowed_ratio DESC LIMIT 20;"
        ),
    },
    {
        "question": "Compare average charges for 99213 in Texas vs California",
        "sql": (
            "SELECT provider_state AS state, "
            "avg(avg_submitted_charge) AS avg_charge, "
            "count(*) AS provider_count "
            "FROM provider_service_cases "
            "WHERE hcpcs_cd = '99213' AND provider_state IN ('TX', 'CA') "
            "GROUP BY provider_state;"
        ),
    },
    {
        "question": "Which specialties have the most outlier billing?",
        "sql": (
            "SELECT provider_type, count(*) AS outlier_count, "
            "avg(max_volume_z) AS avg_volume_z "
            "FROM provider_features WHERE n_volume_outlier_lines > 0 "
            "GROUP BY provider_type ORDER BY outlier_count DESC LIMIT 10;"
        ),
    },
    {
        "question": "Show me the timeline for provider 1821387911",
        "sql": (
            "SELECT hcpcs_cd, hcpcs_desc, tot_srvcs, tot_benes, "
            "avg_submitted_charge, avg_medicare_payment_amt, "
            "estimated_case_payment_amt, seed_risk_score, seed_case_label "
            "FROM provider_service_cases WHERE npi = '1821387911' "
            "ORDER BY estimated_case_payment_amt DESC;"
        ),
    },
    {
        "question": "What actions have been taken on this provider?",
        "sql": (
            "SELECT ca.case_id, ca.action, ca.notes, ca.analyst_id, ca.created_at "
            "FROM case_actions ca WHERE ca.npi = '1821387911' "
            "ORDER BY ca.created_at DESC;"
        ),
    },
    {
        "question": "Show me their billing breakdown",
        "sql": (
            "SELECT hcpcs_cd, hcpcs_desc, tot_srvcs, tot_benes, "
            "services_per_bene, avg_submitted_charge, "
            "submitted_to_allowed_ratio, seed_risk_score, seed_risk_reasons "
            "FROM provider_service_cases WHERE npi = '1821387911' "
            "ORDER BY seed_risk_score DESC;"
        ),
    },
    {
        "question": "Why was this provider flagged?",
        "sql": (
            "SELECT npi, provider_name, max_seed_risk_score, "
            "n_high_risk_lines, service_line_count, "
            "mean_volume_z, mean_charge_z, revoked_2026, revocation_reason "
            "FROM provider_features WHERE npi = '1821387911';"
        ),
    },
    {
        "question": "Who are similar high-risk providers in the same state?",
        "sql": (
            "SELECT pf.npi, pf.provider_name, pf.provider_type, "
            "pf.max_seed_risk_score, pf.total_estimated_payment "
            "FROM provider_features pf "
            "WHERE pf.state = (SELECT state FROM provider_features WHERE npi = '1821387911') "
            "AND pf.max_seed_risk_score > 50 AND pf.npi != '1821387911' "
            "ORDER BY pf.max_seed_risk_score DESC LIMIT 10;"
        ),
    },
]


def build_text_to_sql_system_prompt() -> str:
    """Build the full system prompt for text-to-SQL, including schema + few-shots."""
    examples = "\n\n".join(
        f"Question: {ex['question']}\nSQL: {ex['sql']}" for ex in FEW_SHOT_EXAMPLES
    )
    return f"""{SCHEMA_DESCRIPTION}

## Few-Shot Examples

{examples}

## Instructions
- Return ONLY a valid PostgreSQL SELECT query. No explanations, no markdown.
- Never use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, or GRANT.
- Use LIMIT to cap results (default 20 unless the user specifies otherwise).
- Use column aliases for readability.
- State abbreviations are 2 uppercase letters (e.g. 'FL', 'TX', 'CA').
- NPI values are 10-digit strings stored as TEXT.
- When the user references a provider from earlier in the conversation, use that NPI.

## Handling Unanswerable Questions
- If the question asks for data that truly does not exist (e.g. patient names, diagnoses,
  individual claim dates, real-time data), respond with exactly: UNANSWERABLE
- But if the question CAN be partially answered or redirected to available data, DO answer
  with the closest useful query. For example:
  - "Show me their timeline" → show their service lines ordered by volume (billing profile)
  - "When did they submit claims?" → show their billing summary (no dates available)
  - "Show me their history" → show case_actions history + billing profile
  - "What happened with this provider?" → show risk signals and billing breakdown
"""


# ---------------------------------------------------------------------------
# Risk narrative prompt
# ---------------------------------------------------------------------------

NARRATIVE_SYSTEM_PROMPT = """\
You are a CMS fraud analyst writing concise investigation briefs. Given structured
risk scoring data for a Medicare provider, write a 3-4 sentence summary that:

1. States the overall risk level and recommendation
2. Highlights the most important risk signals with specific numbers
3. Notes any legitimacy factors that mitigate risk
4. Uses plain language a non-technical reviewer can understand

Be factual and direct. Do not speculate. Reference specific data points.
Do not use bullet points — write flowing prose.
"""
