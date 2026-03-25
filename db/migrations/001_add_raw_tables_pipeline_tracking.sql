-- Migration 001: Add raw source tables, pipeline tracking schema, and case_actions
-- Idempotent — safe to run on a fresh DB or an existing deployment.
-- Apply with: psql $DATABASE_URL -f db/migrations/001_add_raw_tables_pipeline_tracking.sql

-- ---------------------------------------------------------------------------
-- Analyst case actions (ghost schema bug-fix — was referenced in cases.py but
-- missing from init.sql, causing failures on fresh deployments)
-- case_id is TEXT without FK so simulated cases (npi|hcpcs|pos) are supported.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS case_actions (
    id          SERIAL PRIMARY KEY,
    case_id     TEXT NOT NULL,
    npi         TEXT NOT NULL,
    action      TEXT NOT NULL,
    notes       TEXT,
    analyst_id  TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_case_actions_case_id ON case_actions (case_id);

-- ---------------------------------------------------------------------------
-- Raw CMS Part B service-level data (one row per provider-HCPCS combination)
-- ---------------------------------------------------------------------------
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
    provider_zip                TEXT,
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

CREATE INDEX IF NOT EXISTS idx_raw_part_b_service_npi     ON raw_part_b_service (npi);
CREATE INDEX IF NOT EXISTS idx_raw_part_b_service_version ON raw_part_b_service (source_version);

-- ---------------------------------------------------------------------------
-- Raw CMS Part B provider-level summary (one row per NPI)
-- ---------------------------------------------------------------------------
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
    provider_zip            TEXT,
    provider_state          TEXT,
    provider_country        TEXT,
    provider_type           TEXT,
    medicare_participating  TEXT,
    total_hcpcs_codes       INTEGER,
    total_benes             DOUBLE PRECISION,
    total_services          DOUBLE PRECISION,
    total_payment_amt       DOUBLE PRECISION,
    source_version          TEXT NOT NULL,
    loaded_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_part_b_provider_npi ON raw_part_b_provider (npi);

-- ---------------------------------------------------------------------------
-- Raw CMS enrollment file (one row per enrollment record)
-- ---------------------------------------------------------------------------
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

CREATE INDEX IF NOT EXISTS idx_raw_enrollment_npi ON raw_enrollment (npi);

-- ---------------------------------------------------------------------------
-- Raw CMS revocation file (one row per revocation record)
-- ---------------------------------------------------------------------------
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

CREATE INDEX IF NOT EXISTS idx_raw_revocations_npi ON raw_revocations (npi);

-- ---------------------------------------------------------------------------
-- Data source version registry
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_source_versions (
    source_type     TEXT PRIMARY KEY,
    current_version TEXT NOT NULL,
    file_path       TEXT,
    file_hash       TEXT,
    row_count       INTEGER,
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    uploaded_by     TEXT
);

-- ---------------------------------------------------------------------------
-- Pipeline execution tracking
-- ---------------------------------------------------------------------------
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

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs (status)
    WHERE status = 'running';

-- ---------------------------------------------------------------------------
-- Extend provider_features with scoring provenance columns
-- ---------------------------------------------------------------------------
ALTER TABLE provider_features ADD COLUMN IF NOT EXISTS last_scored_at  TIMESTAMPTZ;
ALTER TABLE provider_features ADD COLUMN IF NOT EXISTS pipeline_run_id INT REFERENCES pipeline_runs(id) ON DELETE SET NULL;
