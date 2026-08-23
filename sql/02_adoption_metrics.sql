-- =============================================================================
-- GenAI Enterprise Adoption Intelligence Hub
-- 02_adoption_metrics.sql
--
-- 9 of the 10 requested analytical queries, run against the star schema built
-- by sql/01_create_schema.sql. Each query is self-contained (CTEs only, no
-- shared temp tables) so any one can be copy-pasted and run on its own.
--
-- SYNTHETIC DATA ONLY — see data/synthetic_data_dictionary.md and
-- docs/assumptions_and_limitations.md. "Estimated minutes saved" figures are
-- modeled assumptions baked into the data generator, not measured or
-- validated ROI. No query here claims or tests causation.
--
-- Metric definitions match docs/metric_dictionary.md; read that document
-- alongside this file for numerator/denominator/caveat detail.
--
-- Validated: every query below was executed against PostgreSQL 16 with the
-- schema populated from data/processed/*.csv and returned results without
-- error (see sql/README_VALIDATION.md for the run log).
-- =============================================================================


-- -----------------------------------------------------------------------------
-- QUERY 1: Weekly Active Users (WAU) by business unit
-- WAU = distinct users with >= 1 "meaningful action" (prompt_submitted,
-- output_generated, feature_completed, output_exported) in a calendar week.
-- -----------------------------------------------------------------------------
SELECT
    d.week_number,
    d.week_start_date,
    bu.business_unit_name,
    COUNT(DISTINCT f.user_key) AS weekly_active_users
FROM fact_usage_events f
JOIN dim_date d ON d.date_key = f.date_key
JOIN dim_user u ON u.user_key = f.user_key
JOIN dim_business_unit bu ON bu.business_unit_key = u.business_unit_key
WHERE f.event_type IN ('prompt_submitted', 'output_generated', 'feature_completed', 'output_exported')
GROUP BY d.week_number, d.week_start_date, bu.business_unit_name
ORDER BY d.week_number, bu.business_unit_name;


-- -----------------------------------------------------------------------------
-- QUERY 2: Activation rate by rollout wave
-- Activated user = eligible user who (completed training OR used Prompt
-- Library at least once) AND has >= 3 meaningful actions within 14 days of
-- assigned_access_date. This is an association-based definition designed
-- into the dataset, not a validated causal model of "true" activation.
-- -----------------------------------------------------------------------------
WITH eligible_users AS (
    SELECT u.user_key, u.rollout_wave, u.assigned_access_date, u.training_completed_date
    FROM dim_user u
    WHERE u.eligible_for_access_flag = TRUE
      AND u.assigned_access_date IS NOT NULL
),
meaningful_actions_14d AS (
    SELECT
        f.user_key,
        COUNT(*) AS meaningful_action_count
    FROM fact_usage_events f
    JOIN eligible_users e ON e.user_key = f.user_key
    WHERE f.event_type IN ('prompt_submitted', 'output_generated', 'feature_completed', 'output_exported')
      AND f.event_timestamp::date <= e.assigned_access_date + INTERVAL '14 days'
    GROUP BY f.user_key
),
prompt_library_users AS (
    SELECT DISTINCT f.user_key
    FROM fact_usage_events f
    JOIN dim_feature ft ON ft.feature_key = f.feature_key
    WHERE ft.feature_name = 'Prompt Library'
),
activated AS (
    SELECT
        e.user_key,
        e.rollout_wave,
        (e.training_completed_date IS NOT NULL OR pl.user_key IS NOT NULL) AS met_qualification_condition,
        COALESCE(m.meaningful_action_count, 0) AS meaningful_action_count
    FROM eligible_users e
    LEFT JOIN prompt_library_users pl ON pl.user_key = e.user_key
    LEFT JOIN meaningful_actions_14d m ON m.user_key = e.user_key
)
SELECT
    rollout_wave,
    COUNT(*) AS eligible_users,
    SUM(CASE WHEN met_qualification_condition AND meaningful_action_count >= 3 THEN 1 ELSE 0 END) AS activated_users,
    ROUND(
        100.0 * SUM(CASE WHEN met_qualification_condition AND meaningful_action_count >= 3 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        1
    ) AS activation_rate_pct
FROM activated
GROUP BY rollout_wave
ORDER BY rollout_wave;


-- -----------------------------------------------------------------------------
-- QUERY 3: Feature adoption rate by business unit and role
-- Feature adoption rate here = distinct users who completed or exported a
-- given feature / distinct eligible users in that business unit + role cut.
-- (Simplification: denominator is all eligible users, not feature-specific
-- target persona — see docs/metric_dictionary.md caveat.)
-- -----------------------------------------------------------------------------
WITH eligible_users AS (
    SELECT u.user_key, u.business_unit_key, u.role_key
    FROM dim_user u
    WHERE u.eligible_for_access_flag = TRUE AND u.assigned_access_date IS NOT NULL
),
feature_completers AS (
    SELECT DISTINCT f.user_key, f.feature_key
    FROM fact_usage_events f
    WHERE f.event_type IN ('feature_completed', 'output_exported')
)
SELECT
    bu.business_unit_name,
    r.role_name,
    ft.feature_name,
    COUNT(DISTINCT eu.user_key) AS eligible_users,
    COUNT(DISTINCT fc.user_key) AS users_who_completed_feature,
    ROUND(100.0 * COUNT(DISTINCT fc.user_key) / NULLIF(COUNT(DISTINCT eu.user_key), 0), 1) AS feature_adoption_rate_pct
FROM eligible_users eu
JOIN dim_business_unit bu ON bu.business_unit_key = eu.business_unit_key
JOIN dim_role r ON r.role_key = eu.role_key
CROSS JOIN dim_feature ft
LEFT JOIN feature_completers fc ON fc.user_key = eu.user_key AND fc.feature_key = ft.feature_key
WHERE ft.feature_key <> -1
GROUP BY bu.business_unit_name, r.role_name, ft.feature_name
ORDER BY bu.business_unit_name, r.role_name, ft.feature_name;


-- -----------------------------------------------------------------------------
-- QUERY 4: Median time-to-value by business unit
-- Time-to-value = hours from assigned_access_date to the user's first
-- successful completion / export / core-feature action.
-- -----------------------------------------------------------------------------
WITH first_value_event AS (
    SELECT
        f.user_key,
        MIN(f.event_timestamp) AS first_value_ts
    FROM fact_usage_events f
    WHERE f.successful_completion_flag = TRUE
      AND f.event_type IN ('feature_completed', 'output_exported', 'output_generated')
    GROUP BY f.user_key
),
time_to_value AS (
    SELECT
        u.user_key,
        u.business_unit_key,
        EXTRACT(EPOCH FROM (fv.first_value_ts - u.assigned_access_date::timestamp)) / 3600.0 AS hours_to_value
    FROM dim_user u
    JOIN first_value_event fv ON fv.user_key = u.user_key
    WHERE u.assigned_access_date IS NOT NULL
      AND fv.first_value_ts >= u.assigned_access_date::timestamp
)
SELECT
    bu.business_unit_name,
    COUNT(*) AS users_with_first_value,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.hours_to_value)::NUMERIC, 1) AS median_hours_to_value
FROM time_to_value t
JOIN dim_business_unit bu ON bu.business_unit_key = t.business_unit_key
GROUP BY bu.business_unit_name
ORDER BY median_hours_to_value;


-- -----------------------------------------------------------------------------
-- QUERY 5: Weekly retention for each activation cohort
-- Cohort = week of first meaningful action ("activation week" proxy, not the
-- full formal activation definition, to keep cohorts date-anchored). Retention
-- in week N = % of the cohort active in (cohort_week + N).
-- -----------------------------------------------------------------------------
WITH meaningful_events AS (
    SELECT f.user_key, d.week_number
    FROM fact_usage_events f
    JOIN dim_date d ON d.date_key = f.date_key
    WHERE f.event_type IN ('prompt_submitted', 'output_generated', 'feature_completed', 'output_exported')
),
cohort AS (
    SELECT user_key, MIN(week_number) AS cohort_week
    FROM meaningful_events
    GROUP BY user_key
),
cohort_activity AS (
    SELECT
        c.cohort_week,
        me.week_number - c.cohort_week AS weeks_since_activation,
        COUNT(DISTINCT me.user_key) AS active_users
    FROM cohort c
    JOIN meaningful_events me ON me.user_key = c.user_key
    WHERE me.week_number >= c.cohort_week
    GROUP BY c.cohort_week, me.week_number - c.cohort_week
),
cohort_size AS (
    SELECT cohort_week, COUNT(*) AS cohort_users
    FROM cohort
    GROUP BY cohort_week
)
SELECT
    ca.cohort_week,
    cs.cohort_users,
    ca.weeks_since_activation,
    ca.active_users,
    ROUND(100.0 * ca.active_users / NULLIF(cs.cohort_users, 0), 1) AS retention_rate_pct
FROM cohort_activity ca
JOIN cohort_size cs ON cs.cohort_week = ca.cohort_week
WHERE ca.weeks_since_activation BETWEEN 0 AND 8
ORDER BY ca.cohort_week, ca.weeks_since_activation;


-- -----------------------------------------------------------------------------
-- QUERY 6: Training completion versus activation
-- Reports activation rate split by whether the user completed training.
-- This is an ASSOCIATION only — see docs/metric_dictionary.md and
-- docs/assumptions_and_limitations.md: training completion is not randomly
-- assigned in this dataset, so no causal claim is made or supported.
-- -----------------------------------------------------------------------------
WITH eligible_users AS (
    SELECT u.user_key, u.assigned_access_date, u.training_completed_date
    FROM dim_user u
    WHERE u.eligible_for_access_flag = TRUE AND u.assigned_access_date IS NOT NULL
),
meaningful_actions_14d AS (
    SELECT f.user_key, COUNT(*) AS meaningful_action_count
    FROM fact_usage_events f
    JOIN eligible_users e ON e.user_key = f.user_key
    WHERE f.event_type IN ('prompt_submitted', 'output_generated', 'feature_completed', 'output_exported')
      AND f.event_timestamp::date <= e.assigned_access_date + INTERVAL '14 days'
    GROUP BY f.user_key
),
prompt_library_users AS (
    SELECT DISTINCT f.user_key
    FROM fact_usage_events f
    JOIN dim_feature ft ON ft.feature_key = f.feature_key
    WHERE ft.feature_name = 'Prompt Library'
)
SELECT
    CASE WHEN e.training_completed_date IS NOT NULL THEN 'Completed Training' ELSE 'Did Not Complete Training' END AS training_status,
    COUNT(*) AS eligible_users,
    SUM(CASE
        WHEN (e.training_completed_date IS NOT NULL OR pl.user_key IS NOT NULL)
         AND COALESCE(m.meaningful_action_count, 0) >= 3
        THEN 1 ELSE 0
    END) AS activated_users,
    ROUND(
        100.0 * SUM(CASE
            WHEN (e.training_completed_date IS NOT NULL OR pl.user_key IS NOT NULL)
             AND COALESCE(m.meaningful_action_count, 0) >= 3
            THEN 1 ELSE 0
        END) / NULLIF(COUNT(*), 0),
        1
    ) AS activation_rate_pct
FROM eligible_users e
LEFT JOIN prompt_library_users pl ON pl.user_key = e.user_key
LEFT JOIN meaningful_actions_14d m ON m.user_key = e.user_key
GROUP BY training_status
ORDER BY training_status;


-- -----------------------------------------------------------------------------
-- QUERY 7: Feedback barrier ranking by business unit
-- Ranks each business unit's top reported adoption barriers (excluding "No
-- barrier reported") by share of that unit's feedback submissions.
-- -----------------------------------------------------------------------------
WITH barrier_counts AS (
    SELECT
        bu.business_unit_name,
        ff.barrier_category,
        COUNT(*) AS mentions
    FROM fact_feedback ff
    JOIN dim_user u ON u.user_key = ff.user_key
    JOIN dim_business_unit bu ON bu.business_unit_key = u.business_unit_key
    WHERE ff.barrier_category IS NOT NULL AND ff.barrier_category <> 'No barrier reported'
    GROUP BY bu.business_unit_name, ff.barrier_category
),
bu_totals AS (
    SELECT business_unit_name, SUM(mentions) AS total_barrier_mentions
    FROM barrier_counts
    GROUP BY business_unit_name
)
SELECT
    bc.business_unit_name,
    bc.barrier_category,
    bc.mentions,
    ROUND(100.0 * bc.mentions / NULLIF(bt.total_barrier_mentions, 0), 1) AS pct_of_bu_barrier_mentions,
    RANK() OVER (PARTITION BY bc.business_unit_name ORDER BY bc.mentions DESC) AS barrier_rank
FROM barrier_counts bc
JOIN bu_totals bt ON bt.business_unit_name = bc.business_unit_name
ORDER BY bc.business_unit_name, barrier_rank;


-- -----------------------------------------------------------------------------
-- QUERY 8: Estimated minutes saved by feature
-- DISCLAIMER: estimated_minutes_saved is a MODELED ASSUMPTION baked into the
-- synthetic data generator (a plausible per-feature range sampled randomly
-- per successful action). It is NOT a measured value, NOT validated ROI, and
-- must never be reported as real productivity impact.
-- -----------------------------------------------------------------------------
SELECT
    ft.feature_name,
    COUNT(*) FILTER (WHERE f.estimated_minutes_saved IS NOT NULL) AS successful_actions_with_estimate,
    ROUND(SUM(f.estimated_minutes_saved)::NUMERIC, 0) AS total_estimated_minutes_saved,
    ROUND(SUM(f.estimated_minutes_saved)::NUMERIC / 60.0, 1) AS total_estimated_hours_saved,
    ROUND(AVG(f.estimated_minutes_saved)::NUMERIC, 1) AS avg_estimated_minutes_saved_per_action,
    'MODELED ESTIMATE — synthetic data, not validated ROI' AS disclaimer
FROM fact_usage_events f
JOIN dim_feature ft ON ft.feature_key = f.feature_key
WHERE ft.feature_key <> -1
GROUP BY ft.feature_name
ORDER BY total_estimated_minutes_saved DESC;


-- -----------------------------------------------------------------------------
-- QUERY 9: Dormant users — activated users with no meaningful action in the
-- trailing 28 days as of the most recent event in the dataset.
-- -----------------------------------------------------------------------------
WITH reporting_date AS (
    SELECT MAX(event_timestamp)::date AS as_of_date FROM fact_usage_events
),
eligible_users AS (
    SELECT u.user_key, u.assigned_access_date, u.training_completed_date, u.business_unit_key
    FROM dim_user u
    WHERE u.eligible_for_access_flag = TRUE AND u.assigned_access_date IS NOT NULL
),
meaningful_actions_14d AS (
    SELECT f.user_key, COUNT(*) AS meaningful_action_count
    FROM fact_usage_events f
    JOIN eligible_users e ON e.user_key = f.user_key
    WHERE f.event_type IN ('prompt_submitted', 'output_generated', 'feature_completed', 'output_exported')
      AND f.event_timestamp::date <= e.assigned_access_date + INTERVAL '14 days'
    GROUP BY f.user_key
),
prompt_library_users AS (
    SELECT DISTINCT f.user_key
    FROM fact_usage_events f
    JOIN dim_feature ft ON ft.feature_key = f.feature_key
    WHERE ft.feature_name = 'Prompt Library'
),
activated_users AS (
    SELECT e.user_key, e.business_unit_key
    FROM eligible_users e
    LEFT JOIN prompt_library_users pl ON pl.user_key = e.user_key
    LEFT JOIN meaningful_actions_14d m ON m.user_key = e.user_key
    WHERE (e.training_completed_date IS NOT NULL OR pl.user_key IS NOT NULL)
      AND COALESCE(m.meaningful_action_count, 0) >= 3
),
last_28d_activity AS (
    SELECT DISTINCT f.user_key
    FROM fact_usage_events f, reporting_date rd
    WHERE f.event_type IN ('prompt_submitted', 'output_generated', 'feature_completed', 'output_exported')
      AND f.event_timestamp::date > rd.as_of_date - INTERVAL '28 days'
)
SELECT
    bu.business_unit_name,
    COUNT(*) AS activated_users,
    COUNT(*) FILTER (WHERE l.user_key IS NULL) AS dormant_users,
    ROUND(100.0 * COUNT(*) FILTER (WHERE l.user_key IS NULL) / NULLIF(COUNT(*), 0), 1) AS dormancy_rate_pct
FROM activated_users a
JOIN dim_business_unit bu ON bu.business_unit_key = a.business_unit_key
LEFT JOIN last_28d_activity l ON l.user_key = a.user_key
GROUP BY bu.business_unit_name
ORDER BY dormancy_rate_pct DESC;
