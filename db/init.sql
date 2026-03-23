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

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_cases_npi ON provider_service_cases (npi);
CREATE INDEX IF NOT EXISTS idx_cases_label ON provider_service_cases (seed_case_label);
CREATE INDEX IF NOT EXISTS idx_features_state ON provider_features (state);
CREATE INDEX IF NOT EXISTS idx_features_risk ON provider_features (max_seed_risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_features_type ON provider_features (provider_type);
