-- CMS Fraud Detection schema
-- Auto-runs on first container start via docker-entrypoint-initdb.d

-- Raw service-level cases (one row per provider-service pair)
CREATE TABLE IF NOT EXISTS provider_service_cases (
    case_id             TEXT PRIMARY KEY,
    npi                 TEXT NOT NULL,
    provider_last_org_name TEXT,
    provider_first_name TEXT,
    provider_credentials TEXT,
    provider_entity_code TEXT,
    provider_city       TEXT,
    provider_state      TEXT,
    provider_zip5       TEXT,
    provider_type       TEXT,
    medicare_participating_ind TEXT,
    hcpcs_cd            TEXT NOT NULL,
    hcpcs_desc          TEXT,
    place_of_service    TEXT,
    tot_benes           DOUBLE PRECISION,
    tot_srvcs           DOUBLE PRECISION,
    tot_bene_day_srvcs  DOUBLE PRECISION,
    avg_submitted_charge DOUBLE PRECISION,
    avg_medicare_allowed_amt DOUBLE PRECISION,
    avg_medicare_payment_amt DOUBLE PRECISION,
    estimated_case_payment_amt DOUBLE PRECISION,
    services_per_bene   DOUBLE PRECISION,
    submitted_to_allowed_ratio DOUBLE PRECISION,
    payment_to_allowed_ratio DOUBLE PRECISION,
    provider_total_hcpcs_codes DOUBLE PRECISION,
    provider_total_benes DOUBLE PRECISION,
    provider_total_services DOUBLE PRECISION,
    provider_total_payment_amt DOUBLE PRECISION,
    present_in_2025_enrollment_file INTEGER,
    enrollment_record_count INTEGER,
    enrollment_provider_type_desc TEXT,
    enrollment_state_cd TEXT,
    present_in_2026_revocation_file INTEGER,
    revocation_reason_summary TEXT,
    peer_scope          TEXT,
    peer_case_count     INTEGER,
    peer_avg_tot_srvcs  DOUBLE PRECISION,
    service_volume_peer_z DOUBLE PRECISION,
    services_per_bene_peer_z DOUBLE PRECISION,
    submitted_to_allowed_peer_z DOUBLE PRECISION,
    payment_peer_z      DOUBLE PRECISION,
    seed_risk_score     INTEGER,
    seed_legitimacy_score INTEGER,
    seed_case_label     TEXT,
    seed_risk_reasons   TEXT,
    seed_legitimacy_reasons TEXT
);

-- Provider-level feature matrix (one row per NPI)
CREATE TABLE IF NOT EXISTS provider_features (
    npi                         TEXT PRIMARY KEY,
    -- Metadata
    provider_name               TEXT,
    entity_code                 TEXT,
    city                        TEXT,
    state                       TEXT,
    zip5                        TEXT,
    provider_type               TEXT,
    medicare_participating      TEXT,
    provider_total_hcpcs_codes  DOUBLE PRECISION,
    provider_total_benes        DOUBLE PRECISION,
    provider_total_services     DOUBLE PRECISION,
    provider_total_payment_amt  DOUBLE PRECISION,
    enrolled_2025               INTEGER,
    enrollment_record_count     INTEGER,
    revoked_2026                INTEGER,
    revocation_reason           TEXT,
    -- Volume features
    unique_hcpcs_codes          INTEGER,
    unique_place_of_service     INTEGER,
    service_line_count          INTEGER,
    total_benes                 DOUBLE PRECISION,
    total_services              DOUBLE PRECISION,
    total_bene_day_services     DOUBLE PRECISION,
    avg_benes_per_line          DOUBLE PRECISION,
    avg_services_per_line       DOUBLE PRECISION,
    avg_services_per_bene       DOUBLE PRECISION,
    max_services_per_bene       DOUBLE PRECISION,
    std_services_per_bene       DOUBLE PRECISION,
    -- Charge features
    mean_submitted_charge       DOUBLE PRECISION,
    max_submitted_charge        DOUBLE PRECISION,
    std_submitted_charge        DOUBLE PRECISION,
    mean_allowed_amt            DOUBLE PRECISION,
    max_allowed_amt             DOUBLE PRECISION,
    mean_payment_amt            DOUBLE PRECISION,
    max_payment_amt             DOUBLE PRECISION,
    std_payment_amt             DOUBLE PRECISION,
    total_estimated_payment     DOUBLE PRECISION,
    mean_charge_ratio           DOUBLE PRECISION,
    max_charge_ratio            DOUBLE PRECISION,
    std_charge_ratio            DOUBLE PRECISION,
    mean_payment_ratio          DOUBLE PRECISION,
    -- Concentration features
    service_hhi                 DOUBLE PRECISION,
    top_code_share              DOUBLE PRECISION,
    top3_code_share             DOUBLE PRECISION,
    -- Peer z-score features
    mean_volume_z               DOUBLE PRECISION,
    max_volume_z                DOUBLE PRECISION,
    mean_intensity_z            DOUBLE PRECISION,
    max_intensity_z             DOUBLE PRECISION,
    mean_charge_z               DOUBLE PRECISION,
    max_charge_z                DOUBLE PRECISION,
    mean_payment_z              DOUBLE PRECISION,
    max_payment_z               DOUBLE PRECISION,
    n_volume_outlier_lines      INTEGER,
    n_intensity_outlier_lines   INTEGER,
    n_charge_outlier_lines      INTEGER,
    -- Risk seed features
    max_seed_risk_score         INTEGER,
    avg_seed_risk_score         DOUBLE PRECISION,
    min_seed_legitimacy_score   INTEGER,
    avg_seed_legitimacy_score   DOUBLE PRECISION,
    n_high_risk_lines           INTEGER,
    n_state_peer_lines          INTEGER,
    -- Derived features
    risk_legitimacy_gap         INTEGER,
    frac_volume_outlier_lines   DOUBLE PRECISION,
    charge_cv                   DOUBLE PRECISION
);

-- Application users (authentication)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'analyst',
    full_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed demo users (bcrypt-hashed passwords — for hackathon/demo only)
INSERT INTO users (username, hashed_password, role, full_name) VALUES
    ('admin',   '$2b$12$wk6qRpFS1wvj3n/cPAMjbOvGxSKOcEkUUWP3mNzCaLNQUVYvM/ma6', 'admin',   'Admin User'),
    ('analyst', '$2b$12$9prGNwBSgoM4n7BECLTmf.vNfrOTm6KUScPvAvtM63TDPadioQ9UC', 'analyst', 'Demo Analyst'),
    ('judge',   '$2b$12$VTHDf5zzI2LDRfqmoh2Stez7QlVvfH0lWSJw5lYZl.poxEDQHMOoG', 'judge',   'Hackathon Judge')
ON CONFLICT (username) DO NOTHING;

-- Analyst case actions (investigation workflow — one row per analyst decision)
-- Note: case_id is TEXT without FK because simulated cases (npi|hcpcs|pos) are
-- not present in provider_service_cases but are still valid targets for actions.
CREATE TABLE IF NOT EXISTS case_actions (
    id          SERIAL PRIMARY KEY,
    case_id     TEXT NOT NULL,
    npi         TEXT NOT NULL,
    action      TEXT NOT NULL,
    notes       TEXT,
    analyst_id  TEXT NOT NULL DEFAULT 'system',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Immutable audit trail for analyst actions and AI queries
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id VARCHAR(100),
    analyst VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Raw CMS Part B service-level data (one row per provider-HCPCS combination)
CREATE TABLE IF NOT EXISTS raw_part_b_service (
    id                          BIGSERIAL PRIMARY KEY,
    npi                         TEXT NOT NULL,
    provider_last_org_name      TEXT,
    provider_first_name         TEXT,
    provider_credentials        TEXT,
    provider_gender             TEXT,
    provider_entity_code        TEXT,
    provider_street_address_1   TEXT,
    provider_street_address_2   TEXT,
    provider_city               TEXT,
    provider_zip5               TEXT,
    provider_state              TEXT,
    provider_country            TEXT,
    provider_type               TEXT,
    medicare_participating_ind  TEXT,
    hcpcs_cd                    TEXT NOT NULL,
    hcpcs_desc                  TEXT,
    hcpcs_drug_ind              TEXT,
    place_of_service            TEXT,
    tot_benes                   DOUBLE PRECISION,
    bene_unique_cnt             DOUBLE PRECISION,
    bene_day_srvcs_cnt          DOUBLE PRECISION,
    tot_srvcs                   DOUBLE PRECISION,
    tot_bene_day_srvcs          DOUBLE PRECISION,
    avg_submitted_charge        DOUBLE PRECISION,
    avg_medicare_allowed_amt    DOUBLE PRECISION,
    avg_medicare_payment_amt    DOUBLE PRECISION,
    avg_medicare_stnd_amt       DOUBLE PRECISION,
    source_version              TEXT NOT NULL,
    loaded_at                   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Raw CMS Part B provider-level summary (one row per NPI)
CREATE TABLE IF NOT EXISTS raw_part_b_provider (
    id                      BIGSERIAL PRIMARY KEY,
    npi                     TEXT NOT NULL,
    provider_last_org_name  TEXT,
    provider_first_name     TEXT,
    provider_credentials    TEXT,
    provider_gender         TEXT,
    provider_entity_code    TEXT,
    provider_street_address TEXT,
    provider_city           TEXT,
    provider_zip5           TEXT,
    provider_state          TEXT,
    provider_country        TEXT,
    provider_type           TEXT,
    medicare_participating_ind TEXT,
    total_hcpcs_codes       INTEGER,
    total_benes             DOUBLE PRECISION,
    total_services          DOUBLE PRECISION,
    total_payment_amt       DOUBLE PRECISION,
    source_version          TEXT NOT NULL,
    loaded_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Raw CMS enrollment file (one row per enrollment record)
CREATE TABLE IF NOT EXISTS raw_enrollment (
    id                      BIGSERIAL PRIMARY KEY,
    npi                     TEXT NOT NULL,
    enrollment_id           TEXT,
    provider_type_cd        TEXT,
    provider_type_desc      TEXT,
    specialty_cd            TEXT,
    state_cd                TEXT,
    first_name              TEXT,
    last_name               TEXT,
    organization_name       TEXT,
    source_version          TEXT NOT NULL,
    loaded_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Raw CMS revocation file (one row per revocation record)
CREATE TABLE IF NOT EXISTS raw_revocations (
    id                  BIGSERIAL PRIMARY KEY,
    npi                 TEXT NOT NULL,
    first_name          TEXT,
    last_name           TEXT,
    organization_name   TEXT,
    revocation_reason   TEXT,
    exclusion_type      TEXT,
    state               TEXT,
    source_version      TEXT NOT NULL,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Data source version registry (one row per source type, updated on each upload)
CREATE TABLE IF NOT EXISTS data_source_versions (
    source_type     TEXT PRIMARY KEY,
    current_version TEXT NOT NULL,
    file_path       TEXT,
    file_hash       TEXT,
    row_count       INTEGER,
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    uploaded_by     TEXT
);

-- Pipeline execution tracking (one row per pipeline run)
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id              BIGSERIAL PRIMARY KEY,
    run_type        TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    current_stage   TEXT,
    progress_pct    DOUBLE PRECISION DEFAULT 0.0,
    source_versions JSONB NOT NULL DEFAULT '{}'::jsonb,
    stage_results   JSONB NOT NULL DEFAULT '[]'::jsonb,
    error_message   TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    triggered_by    TEXT
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_cases_npi ON provider_service_cases (npi);
CREATE INDEX IF NOT EXISTS idx_cases_label ON provider_service_cases (seed_case_label);
CREATE INDEX IF NOT EXISTS idx_features_state ON provider_features (state);
CREATE INDEX IF NOT EXISTS idx_features_risk ON provider_features (max_seed_risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_features_type ON provider_features (provider_type);
CREATE INDEX IF NOT EXISTS idx_case_actions_case_id ON case_actions (case_id);
CREATE INDEX IF NOT EXISTS idx_case_actions_npi ON case_actions (npi);
CREATE INDEX IF NOT EXISTS idx_audit_analyst ON audit_log (analyst);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_raw_part_b_service_npi ON raw_part_b_service (npi);
CREATE INDEX IF NOT EXISTS idx_raw_part_b_service_version ON raw_part_b_service (source_version);
CREATE INDEX IF NOT EXISTS idx_raw_part_b_provider_npi ON raw_part_b_provider (npi);
CREATE INDEX IF NOT EXISTS idx_raw_enrollment_npi ON raw_enrollment (npi);
CREATE INDEX IF NOT EXISTS idx_raw_revocations_npi ON raw_revocations (npi);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs (status)
    WHERE status = 'running';

-- Metadata for trained ML models (additive only)
CREATE TABLE IF NOT EXISTS trained_models (
    id                  BIGSERIAL PRIMARY KEY,
    model_name          TEXT NOT NULL,
    model_version       TEXT NOT NULL,
    model_type          TEXT NOT NULL,
    feature_columns     JSONB NOT NULL DEFAULT '[]'::jsonb,
    training_metrics    JSONB NOT NULL DEFAULT '{}'::jsonb,
    artifact_path       TEXT,
    trained_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (model_name, model_version)
);

-- Optional persistence for per-observation ML scores (additive only)
CREATE TABLE IF NOT EXISTS observation_model_scores (
    id                      BIGSERIAL PRIMARY KEY,
    case_id                 TEXT NOT NULL,
    npi                     TEXT NOT NULL,
    model_name              TEXT NOT NULL,
    model_version           TEXT NOT NULL,
    predicted_probability   DOUBLE PRECISION,
    composite_score         DOUBLE PRECISION,
    risk_label              TEXT,
    score_metadata          JSONB NOT NULL DEFAULT '{}'::jsonb,
    scored_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_obs_model_scores_case_id
    ON observation_model_scores (case_id);
CREATE INDEX IF NOT EXISTS idx_obs_model_scores_npi
    ON observation_model_scores (npi);
CREATE INDEX IF NOT EXISTS idx_obs_model_scores_model
    ON observation_model_scores (model_name, model_version);

CREATE OR REPLACE VIEW bridge_provider_context_v AS
SELECT
    pf.npi,
    pf.provider_type,
    COALESCE(pf.provider_total_payment_amt, 0.0) AS total_payment,
    COALESCE(pf.unique_hcpcs_codes, 0)::DOUBLE PRECISION AS drug_count,
    (
        COALESCE(pf.unique_hcpcs_codes, 0)
        + COALESCE(pf.unique_place_of_service, 0)
    )::DOUBLE PRECISION AS graph_node_degree,
    COALESCE(pf.unique_hcpcs_codes, 0)::DOUBLE PRECISION AS graph_hcpcs_count,
    0.0::DOUBLE PRECISION AS graph_drug_count,
    GREATEST(
        COUNT(*) OVER (PARTITION BY pf.provider_type) - 1,
        0
    )::DOUBLE PRECISION AS graph_shared_specialty_count,
    (
        LEAST(GREATEST(COALESCE(pf.provider_total_payment_amt, 0.0) / 100000.0, 0.0), 5.0)
        + LEAST(GREATEST(COALESCE(pf.unique_hcpcs_codes, 0)::DOUBLE PRECISION / 5.0, 0.0), 5.0)
        + LEAST(
            GREATEST(
                (
                    COALESCE(pf.unique_hcpcs_codes, 0)
                    + COALESCE(pf.unique_place_of_service, 0)
                )::DOUBLE PRECISION / 10.0,
                0.0
            ),
            5.0
        )
    )::DOUBLE PRECISION AS provider_context_score
FROM provider_features pf;

CREATE OR REPLACE VIEW bridge_observation_peer_metrics_v AS
SELECT
    psc.case_id,
    psc.npi,
    psc.provider_type,
    psc.hcpcs_cd,
    COALESCE(psc.services_per_bene, 0.0) AS services_per_bene,
    AVG(psc.services_per_bene) OVER (PARTITION BY psc.provider_type, psc.hcpcs_cd)
        AS peer_avg_spb,
    AVG(psc.submitted_to_allowed_ratio) OVER (PARTITION BY psc.provider_type, psc.hcpcs_cd)
        AS peer_avg_charge_ratio,
    AVG(psc.avg_medicare_payment_amt) OVER (PARTITION BY psc.provider_type, psc.hcpcs_cd)
        AS peer_avg_payment_amt
FROM provider_service_cases psc;

CREATE OR REPLACE VIEW bridge_observation_base_v AS
SELECT
    psc.case_id,
    psc.npi,
    psc.hcpcs_cd,
    psc.provider_type,
    psc.avg_submitted_charge,
    psc.avg_medicare_allowed_amt AS avg_allowed_amount,
    psc.avg_medicare_payment_amt AS avg_payment_amount,
    psc.tot_srvcs AS total_services,
    psc.tot_benes AS total_beneficiaries,
    psc.present_in_2025_enrollment_file,
    psc.present_in_2026_revocation_file,
    psc.submitted_to_allowed_ratio,
    psc.submitted_to_allowed_peer_z,
    psc.services_per_bene_peer_z,
    pm.services_per_bene,
    pm.peer_avg_spb,
    pf.mean_submitted_charge AS charge_per_service,
    pf.avg_services_per_bene AS provider_avg_services_per_bene,
    pf.mean_payment_ratio,
    pf.provider_total_payment_amt,
    pf.unique_hcpcs_codes,
    pf.unique_place_of_service,
    pf.revoked_2026 AS is_revoked,
    0::INTEGER AS is_excluded,
    pc.graph_node_degree,
    pc.graph_hcpcs_count,
    pc.graph_drug_count,
    pc.graph_shared_specialty_count,
    pc.provider_context_score,
    psc.seed_risk_score AS hybrid_risk_score
FROM provider_service_cases psc
JOIN provider_features pf
    ON pf.npi = psc.npi
JOIN bridge_provider_context_v pc
    ON pc.npi = psc.npi
JOIN bridge_observation_peer_metrics_v pm
    ON pm.case_id = psc.case_id;

CREATE OR REPLACE VIEW bridge_observation_scores_v AS
SELECT
    ob.*,
    (
        CASE WHEN COALESCE(ob.present_in_2026_revocation_file, 0) = 1 THEN 25 ELSE 0 END
        + CASE WHEN COALESCE(ob.present_in_2025_enrollment_file, 0) = 0 THEN 10 ELSE 0 END
    )::DOUBLE PRECISION AS rule_score,
    (
        LEAST(
            GREATEST(COALESCE(ob.submitted_to_allowed_peer_z, 0.0) * 15.0, 0.0),
            45.0
        )
        + LEAST(
            GREATEST(
                (
                    COALESCE(
                        ob.services_per_bene / NULLIF(ob.peer_avg_spb, 0.0),
                        1.0
                    ) - 1.0
                ) * 10.0,
                0.0
            ),
            20.0
        )
    )::DOUBLE PRECISION AS anomaly_score
FROM bridge_observation_base_v ob;

CREATE OR REPLACE VIEW bridge_observation_labels_v AS
SELECT
    os.*,
    CASE
        WHEN COALESCE(os.is_revoked, 0) = 1
            OR COALESCE(os.is_excluded, 0) = 1
            OR COALESCE(os.hybrid_risk_score, 0) >= 92
            OR (
                COALESCE(os.rule_score, 0.0) >= 35.0
                AND COALESCE(os.anomaly_score, 0.0) >= 15.0
            )
            THEN 1
        WHEN COALESCE(os.hybrid_risk_score, 0) <= 30
            AND COALESCE(os.is_revoked, 0) = 0
            AND COALESCE(os.is_excluded, 0) = 0
            AND COALESCE(os.rule_score, 0.0) <= 5.0
            AND COALESCE(os.anomaly_score, 0.0) <= 8.0
            THEN 0
        ELSE NULL
    END AS weak_label
FROM bridge_observation_scores_v os;

CREATE OR REPLACE VIEW bridge_training_examples_v AS
SELECT
    ol.case_id AS observation_id,
    ol.npi,
    COALESCE(ol.avg_submitted_charge, 0.0) AS avg_submitted_charge,
    COALESCE(ol.avg_allowed_amount, 0.0) AS avg_allowed_amount,
    COALESCE(ol.avg_payment_amount, 0.0) AS avg_payment_amount,
    COALESCE(ol.total_services, 0.0) AS total_services,
    COALESCE(ol.total_beneficiaries, 0.0) AS total_beneficiaries,
    COALESCE(ol.rule_score, 0.0) AS rule_score,
    COALESCE(ol.anomaly_score, 0.0) AS anomaly_score,
    COALESCE(ol.provider_context_score, 0.0) AS provider_context_score,
    COALESCE(ol.hybrid_risk_score, 0.0) AS hybrid_risk_score,
    COALESCE(ol.submitted_to_allowed_peer_z, 0.0) * 100.0 AS charge_delta_pct,
    COALESCE(ol.services_per_bene_peer_z, 0.0) * 100.0 AS utilization_delta_pct,
    COALESCE(ol.charge_per_service, 0.0) AS charge_per_service,
    COALESCE(ol.provider_avg_services_per_bene, 0.0) AS services_per_bene,
    COALESCE(ol.mean_payment_ratio, 0.0) AS payment_to_charge_ratio,
    COALESCE(ol.is_revoked, 0)::DOUBLE PRECISION AS is_revoked,
    COALESCE(ol.is_excluded, 0)::DOUBLE PRECISION AS is_excluded,
    COALESCE(ol.graph_node_degree, 0.0) AS graph_node_degree,
    COALESCE(ol.graph_hcpcs_count, 0.0) AS graph_hcpcs_count,
    COALESCE(ol.graph_drug_count, 0.0) AS graph_drug_count,
    COALESCE(ol.graph_shared_specialty_count, 0.0) AS graph_shared_specialty_count,
    ol.weak_label
FROM bridge_observation_labels_v ol
WHERE ol.weak_label IS NOT NULL;

-- Additive columns for provider_features (idempotent via IF NOT EXISTS)
ALTER TABLE provider_features ADD COLUMN IF NOT EXISTS last_scored_at  TIMESTAMPTZ;
ALTER TABLE provider_features ADD COLUMN IF NOT EXISTS pipeline_run_id INT REFERENCES pipeline_runs(id) ON DELETE SET NULL;
