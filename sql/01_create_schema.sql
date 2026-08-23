-- =============================================================================
-- GenAI Enterprise Adoption Intelligence Hub
-- 01_create_schema.sql
--
-- Builds a PostgreSQL star schema from the cleaned synthetic CSVs produced by
-- src/transform_data.py (data/processed/clean_*.csv), for the fictional
-- Northstar Financial Group / Northstar Assist scenario.
--
-- SYNTHETIC DATA ONLY. Nothing loaded by this script represents a real
-- company, employee, or system. See data/synthetic_data_dictionary.md and
-- docs/assumptions_and_limitations.md.
--
-- HOW TO RUN (from the repository root, so the \copy paths resolve):
--   createdb genai_adoption
--   psql -d genai_adoption -f sql/01_create_schema.sql
--
-- This script was authored and validated against PostgreSQL 16 in the
-- project's build environment (schema created, ~236K/6K/7.6K rows loaded,
-- and every query in 02_adoption_metrics.sql / 03_weekly_insights.sql run
-- successfully against it). See docs/data_model.md for the entity-relationship
-- narrative and sql/README validation notes.
--
-- Layering:
--   staging.*  -- one table per clean_*.csv, columns typed but unmodified
--   public.*   -- the star schema (dimensions + facts) built from staging
-- =============================================================================

-- -----------------------------------------------------------------------------
-- SECTION 0: Reset (safe to re-run this script from scratch)
-- -----------------------------------------------------------------------------
DROP SCHEMA IF EXISTS staging CASCADE;
CREATE SCHEMA staging;

DROP TABLE IF EXISTS fact_usage_events CASCADE;
DROP TABLE IF EXISTS fact_feedback CASCADE;
DROP TABLE IF EXISTS fact_training_attendance CASCADE;
DROP TABLE IF EXISTS dim_user CASCADE;
DROP TABLE IF EXISTS dim_date CASCADE;
DROP TABLE IF EXISTS dim_feature CASCADE;
DROP TABLE IF EXISTS dim_business_unit CASCADE;
DROP TABLE IF EXISTS dim_role CASCADE;

-- -----------------------------------------------------------------------------
-- SECTION 1: Staging tables (typed 1:1 mirror of data/processed/clean_*.csv)
-- -----------------------------------------------------------------------------

CREATE TABLE staging.stg_users (
    user_id                     TEXT PRIMARY KEY,
    business_unit               TEXT,
    role                        TEXT,
    region                      TEXT,
    manager_level               TEXT,
    hire_date                   DATE,
    assigned_access_date        DATE,
    rollout_wave                INTEGER,
    training_assigned_date      DATE,
    training_completed_date     DATE,
    training_format             TEXT,
    manager_champion_flag       BOOLEAN,
    eligible_for_access_flag    BOOLEAN
);

CREATE TABLE staging.stg_usage_events (
    event_id                    TEXT PRIMARY KEY,
    user_id                     TEXT,
    event_timestamp             TIMESTAMP,
    session_id                  TEXT,
    feature_name                TEXT,
    event_type                  TEXT,
    prompt_category              TEXT,
    output_exported_flag        BOOLEAN,
    successful_completion_flag  BOOLEAN,
    estimated_minutes_saved     NUMERIC,
    session_duration_seconds    NUMERIC,
    error_flag                  BOOLEAN,
    platform                    TEXT,
    source_system                TEXT
);

CREATE TABLE staging.stg_feedback (
    feedback_id                 TEXT PRIMARY KEY,
    user_id                     TEXT,
    feedback_timestamp          TIMESTAMP,
    rating_1_to_5                NUMERIC,
    sentiment_label              TEXT,
    barrier_category             TEXT,
    free_text_feedback           TEXT,
    feature_name                 TEXT,
    would_recommend_flag         BOOLEAN
);

CREATE TABLE staging.stg_training_sessions (
    training_session_id         TEXT PRIMARY KEY,
    session_date                 DATE,
    business_unit                 TEXT,
    training_format               TEXT,
    registered_count               INTEGER,
    attended_count                 INTEGER,
    completion_count               INTEGER,
    facilitator                    TEXT,
    session_topic                  TEXT
);

CREATE TABLE staging.stg_feature_catalog (
    feature_id                   TEXT PRIMARY KEY,
    feature_name                  TEXT,
    feature_category              TEXT,
    target_persona                TEXT,
    release_date                  DATE,
    core_feature_flag             BOOLEAN
);

CREATE TABLE staging.stg_calendar (
    date                          DATE PRIMARY KEY,
    week_start_date                DATE,
    week_number                    INTEGER,
    month                           INTEGER,
    month_name                     TEXT,
    quarter                         INTEGER,
    year                            INTEGER
);

-- -----------------------------------------------------------------------------
-- SECTION 2: Load staging tables from data/processed/clean_*.csv
-- \copy is a psql client-side command: paths are relative to the directory
-- psql is invoked FROM, not the server. Run this script from the repo root.
-- -----------------------------------------------------------------------------
\copy staging.stg_users FROM 'data/processed/clean_users.csv' WITH (FORMAT csv, HEADER true)
\copy staging.stg_usage_events FROM 'data/processed/clean_usage_events.csv' WITH (FORMAT csv, HEADER true)
\copy staging.stg_feedback FROM 'data/processed/clean_feedback.csv' WITH (FORMAT csv, HEADER true)
\copy staging.stg_training_sessions FROM 'data/processed/clean_training_sessions.csv' WITH (FORMAT csv, HEADER true)
\copy staging.stg_feature_catalog FROM 'data/processed/clean_feature_catalog.csv' WITH (FORMAT csv, HEADER true)
\copy staging.stg_calendar FROM 'data/processed/clean_calendar.csv' WITH (FORMAT csv, HEADER true)

-- -----------------------------------------------------------------------------
-- SECTION 3: Dimension tables
-- -----------------------------------------------------------------------------

-- dim_business_unit
-- Grain: one row per business unit. Natural key: business_unit_name.
CREATE TABLE dim_business_unit (
    business_unit_key   SERIAL PRIMARY KEY,
    business_unit_name  TEXT NOT NULL UNIQUE
);

INSERT INTO dim_business_unit (business_unit_name)
SELECT DISTINCT business_unit FROM staging.stg_users
UNION
SELECT DISTINCT business_unit FROM staging.stg_training_sessions
ORDER BY 1;

-- dim_role
-- Grain: one row per job role. manager_level is included as a role-level
-- attribute because, in this dataset, every user of a given role always
-- carries the same manager_level (a reasonable simplification for a
-- portfolio-scale project; a larger org might model this separately).
CREATE TABLE dim_role (
    role_key       SERIAL PRIMARY KEY,
    role_name      TEXT NOT NULL UNIQUE,
    manager_level  TEXT
);

INSERT INTO dim_role (role_name, manager_level)
SELECT DISTINCT role, manager_level FROM staging.stg_users
ORDER BY 1;

-- dim_feature
-- Grain: one row per Northstar Assist feature, plus one synthetic "Unknown"
-- member (feature_key = -1) used by fact rows whose feature_name is missing,
-- so joins to this dimension never need to special-case NULL.
CREATE TABLE dim_feature (
    feature_key         INTEGER PRIMARY KEY,
    feature_id          TEXT UNIQUE,
    feature_name        TEXT NOT NULL UNIQUE,
    feature_category    TEXT,
    target_persona      TEXT,
    release_date        DATE,
    core_feature_flag   BOOLEAN
);

INSERT INTO dim_feature (feature_key, feature_id, feature_name, feature_category, target_persona, release_date, core_feature_flag)
VALUES (-1, 'F00', 'Unknown / Not Captured', 'Unknown', 'Unknown', NULL, NULL);

INSERT INTO dim_feature (feature_key, feature_id, feature_name, feature_category, target_persona, release_date, core_feature_flag)
SELECT
    ROW_NUMBER() OVER (ORDER BY feature_id)::INTEGER AS feature_key,
    feature_id, feature_name, feature_category, target_persona, release_date, core_feature_flag
FROM staging.stg_feature_catalog;

-- dim_date
-- Grain: one row per calendar day across the 24-week rollout window. This is
-- the table that would be "Mark as date table" in Power BI (see
-- powerbi/report_design.md). date_key is an integer YYYYMMDD surrogate key,
-- the conventional choice for fast fact-table joins/partitioning.
CREATE TABLE dim_date (
    date_key           INTEGER PRIMARY KEY,
    full_date          DATE NOT NULL UNIQUE,
    week_start_date    DATE,
    week_number        INTEGER,
    month              INTEGER,
    month_name         TEXT,
    quarter            INTEGER,
    year               INTEGER
);

INSERT INTO dim_date (date_key, full_date, week_start_date, week_number, month, month_name, quarter, year)
SELECT
    TO_CHAR(date, 'YYYYMMDD')::INTEGER,
    date, week_start_date, week_number, month, month_name, quarter, year
FROM staging.stg_calendar
ORDER BY date;

-- dim_user
-- Grain: one row per unique employee (user_id). FKs to dim_business_unit and
-- dim_role. assigned_access_date_key is nullable because a small share of
-- users have no on-file access date (see data_quality_issues.csv).
CREATE TABLE dim_user (
    user_key                      SERIAL PRIMARY KEY,
    user_id                       TEXT NOT NULL UNIQUE,
    business_unit_key             INTEGER REFERENCES dim_business_unit(business_unit_key),
    role_key                      INTEGER REFERENCES dim_role(role_key),
    region                        TEXT,
    hire_date                     DATE,
    assigned_access_date          DATE,
    assigned_access_date_key      INTEGER REFERENCES dim_date(date_key),
    rollout_wave                  INTEGER,
    training_assigned_date        DATE,
    training_completed_date       DATE,
    training_format               TEXT,
    manager_champion_flag         BOOLEAN,
    eligible_for_access_flag      BOOLEAN
);

INSERT INTO dim_user (
    user_id, business_unit_key, role_key, region, hire_date,
    assigned_access_date, assigned_access_date_key, rollout_wave,
    training_assigned_date, training_completed_date, training_format,
    manager_champion_flag, eligible_for_access_flag
)
SELECT
    u.user_id,
    bu.business_unit_key,
    r.role_key,
    u.region,
    u.hire_date,
    u.assigned_access_date,
    TO_CHAR(u.assigned_access_date, 'YYYYMMDD')::INTEGER,
    u.rollout_wave,
    u.training_assigned_date,
    u.training_completed_date,
    u.training_format,
    u.manager_champion_flag,
    u.eligible_for_access_flag
FROM staging.stg_users u
LEFT JOIN dim_business_unit bu ON bu.business_unit_name = u.business_unit
LEFT JOIN dim_role r ON r.role_name = u.role;

-- -----------------------------------------------------------------------------
-- SECTION 4: Fact tables
-- -----------------------------------------------------------------------------

-- fact_usage_events
-- Grain: one row per usage event (1:1 with clean_usage_events.csv). This is
-- the finest-grain fact table in the model; every adoption/engagement metric
-- is built by aggregating this table.
CREATE TABLE fact_usage_events (
    event_id                     TEXT PRIMARY KEY,
    user_key                     INTEGER NOT NULL REFERENCES dim_user(user_key),
    date_key                     INTEGER NOT NULL REFERENCES dim_date(date_key),
    feature_key                  INTEGER NOT NULL REFERENCES dim_feature(feature_key),
    event_timestamp              TIMESTAMP NOT NULL,
    event_type                   TEXT,
    prompt_category              TEXT,
    output_exported_flag         BOOLEAN,
    successful_completion_flag   BOOLEAN,
    estimated_minutes_saved      NUMERIC,
    session_duration_seconds     NUMERIC,
    error_flag                   BOOLEAN,
    platform                     TEXT,
    source_system                TEXT,
    session_id                   TEXT
);

INSERT INTO fact_usage_events (
    event_id, user_key, date_key, feature_key, event_timestamp, event_type,
    prompt_category, output_exported_flag, successful_completion_flag,
    estimated_minutes_saved, session_duration_seconds, error_flag,
    platform, source_system, session_id
)
SELECT
    e.event_id,
    du.user_key,
    TO_CHAR(e.event_timestamp, 'YYYYMMDD')::INTEGER,
    COALESCE(df.feature_key, -1),
    e.event_timestamp,
    e.event_type,
    e.prompt_category,
    e.output_exported_flag,
    e.successful_completion_flag,
    e.estimated_minutes_saved,
    e.session_duration_seconds,
    e.error_flag,
    e.platform,
    e.source_system,
    e.session_id
FROM staging.stg_usage_events e
JOIN dim_user du ON du.user_id = e.user_id
LEFT JOIN dim_feature df ON df.feature_name = e.feature_name;

-- fact_feedback
-- Grain: one row per feedback submission.
CREATE TABLE fact_feedback (
    feedback_id            TEXT PRIMARY KEY,
    user_key               INTEGER NOT NULL REFERENCES dim_user(user_key),
    date_key               INTEGER NOT NULL REFERENCES dim_date(date_key),
    feature_key            INTEGER NOT NULL REFERENCES dim_feature(feature_key),
    feedback_timestamp     TIMESTAMP NOT NULL,
    rating_1_to_5          NUMERIC,
    sentiment_label        TEXT,
    barrier_category       TEXT,
    free_text_feedback     TEXT,
    would_recommend_flag   BOOLEAN
);

INSERT INTO fact_feedback (
    feedback_id, user_key, date_key, feature_key, feedback_timestamp,
    rating_1_to_5, sentiment_label, barrier_category, free_text_feedback, would_recommend_flag
)
SELECT
    f.feedback_id,
    du.user_key,
    TO_CHAR(f.feedback_timestamp, 'YYYYMMDD')::INTEGER,
    COALESCE(df.feature_key, -1),
    f.feedback_timestamp,
    f.rating_1_to_5,
    f.sentiment_label,
    f.barrier_category,
    f.free_text_feedback,
    f.would_recommend_flag
FROM staging.stg_feedback f
JOIN dim_user du ON du.user_id = f.user_id
LEFT JOIN dim_feature df ON df.feature_name = f.feature_name;

-- fact_training_attendance
-- Grain: one row per SCHEDULED TRAINING SESSION (aggregate registered /
-- attended / completed counts for that session), NOT one row per individual
-- attendee. The source data (training_sessions.csv) is an aggregate session
-- log rather than a per-user attendance roster — see
-- docs/assumptions_and_limitations.md. Individual-level training completion
-- is instead available on dim_user (training_assigned_date /
-- training_completed_date).
CREATE TABLE fact_training_attendance (
    training_session_id   TEXT PRIMARY KEY,
    business_unit_key     INTEGER REFERENCES dim_business_unit(business_unit_key),
    date_key              INTEGER NOT NULL REFERENCES dim_date(date_key),
    training_format       TEXT,
    registered_count      INTEGER,
    attended_count        INTEGER,
    completion_count      INTEGER,
    facilitator           TEXT,
    session_topic         TEXT
);

INSERT INTO fact_training_attendance (
    training_session_id, business_unit_key, date_key, training_format,
    registered_count, attended_count, completion_count, facilitator, session_topic
)
SELECT
    t.training_session_id,
    bu.business_unit_key,
    TO_CHAR(t.session_date, 'YYYYMMDD')::INTEGER,
    t.training_format,
    t.registered_count,
    t.attended_count,
    t.completion_count,
    t.facilitator,
    t.session_topic
FROM staging.stg_training_sessions t
LEFT JOIN dim_business_unit bu ON bu.business_unit_name = t.business_unit;

-- -----------------------------------------------------------------------------
-- SECTION 5: Indexes on fact-table foreign keys (join performance)
-- -----------------------------------------------------------------------------
CREATE INDEX idx_fact_usage_events_user_key ON fact_usage_events(user_key);
CREATE INDEX idx_fact_usage_events_date_key ON fact_usage_events(date_key);
CREATE INDEX idx_fact_usage_events_feature_key ON fact_usage_events(feature_key);
CREATE INDEX idx_fact_usage_events_event_type ON fact_usage_events(event_type);

CREATE INDEX idx_fact_feedback_user_key ON fact_feedback(user_key);
CREATE INDEX idx_fact_feedback_date_key ON fact_feedback(date_key);
CREATE INDEX idx_fact_feedback_feature_key ON fact_feedback(feature_key);

CREATE INDEX idx_fact_training_attendance_bu_key ON fact_training_attendance(business_unit_key);
CREATE INDEX idx_fact_training_attendance_date_key ON fact_training_attendance(date_key);

CREATE INDEX idx_dim_user_business_unit_key ON dim_user(business_unit_key);
CREATE INDEX idx_dim_user_role_key ON dim_user(role_key);

-- -----------------------------------------------------------------------------
-- SECTION 6: Post-load validation (row counts should match data/processed/)
-- -----------------------------------------------------------------------------
SELECT 'dim_business_unit' AS table_name, COUNT(*) AS row_count FROM dim_business_unit
UNION ALL SELECT 'dim_role', COUNT(*) FROM dim_role
UNION ALL SELECT 'dim_feature', COUNT(*) FROM dim_feature
UNION ALL SELECT 'dim_date', COUNT(*) FROM dim_date
UNION ALL SELECT 'dim_user', COUNT(*) FROM dim_user
UNION ALL SELECT 'fact_usage_events', COUNT(*) FROM fact_usage_events
UNION ALL SELECT 'fact_feedback', COUNT(*) FROM fact_feedback
UNION ALL SELECT 'fact_training_attendance', COUNT(*) FROM fact_training_attendance
ORDER BY 1;
