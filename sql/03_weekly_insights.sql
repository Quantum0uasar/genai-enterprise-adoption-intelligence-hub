-- =============================================================================
-- GenAI Enterprise Adoption Intelligence Hub
-- 03_weekly_insights.sql
--
-- QUERY 10 (of 10): a weekly executive KPI / segment-comparison table —
-- one row per (week, business unit), suitable as the source query behind a
-- "weekly readout" view or export.
--
-- SYNTHETIC DATA ONLY. All figures describe the fictional Northstar
-- Financial Group dataset. estimated_hours_saved is a MODELED ESTIMATE, not
-- validated ROI. No causal claims are made by this query or its output.
--
-- Validated: executed against PostgreSQL 16 with the schema from
-- sql/01_create_schema.sql populated; returned one row per
-- (week_number, business_unit) with no errors.
-- =============================================================================

WITH meaningful_events AS (
    SELECT
        f.user_key,
        f.feature_key,
        f.estimated_minutes_saved,
        d.week_number,
        d.week_start_date,
        u.business_unit_key
    FROM fact_usage_events f
    JOIN dim_date d ON d.date_key = f.date_key
    JOIN dim_user u ON u.user_key = f.user_key
    WHERE f.event_type IN ('prompt_submitted', 'output_generated', 'feature_completed', 'output_exported')
),
weekly_active_users AS (
    SELECT week_number, week_start_date, business_unit_key, COUNT(DISTINCT user_key) AS wau
    FROM meaningful_events
    GROUP BY week_number, week_start_date, business_unit_key
),
weekly_minutes_saved AS (
    SELECT week_number, business_unit_key, SUM(estimated_minutes_saved) AS total_minutes_saved
    FROM meaningful_events
    GROUP BY week_number, business_unit_key
),
weekly_prompt_library_users AS (
    SELECT me.week_number, me.business_unit_key, COUNT(DISTINCT me.user_key) AS prompt_library_users
    FROM meaningful_events me
    JOIN dim_feature ft ON ft.feature_key = me.feature_key
    WHERE ft.feature_name = 'Prompt Library'
    GROUP BY me.week_number, me.business_unit_key
),
weekly_feedback AS (
    SELECT
        d.week_number,
        u.business_unit_key,
        COUNT(*) AS feedback_submissions,
        ROUND(AVG(ff.rating_1_to_5)::NUMERIC, 2) AS avg_rating,
        ROUND(100.0 * SUM(CASE WHEN ff.would_recommend_flag THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) AS recommendation_rate_pct
    FROM fact_feedback ff
    JOIN dim_date d ON d.date_key = ff.date_key
    JOIN dim_user u ON u.user_key = ff.user_key
    GROUP BY d.week_number, u.business_unit_key
),
weekly_top_barrier AS (
    SELECT week_number, business_unit_key, barrier_category, mentions
    FROM (
        SELECT
            d.week_number,
            u.business_unit_key,
            ff.barrier_category,
            COUNT(*) AS mentions,
            ROW_NUMBER() OVER (
                PARTITION BY d.week_number, u.business_unit_key
                ORDER BY COUNT(*) DESC
            ) AS rn
        FROM fact_feedback ff
        JOIN dim_date d ON d.date_key = ff.date_key
        JOIN dim_user u ON u.user_key = ff.user_key
        WHERE ff.barrier_category IS NOT NULL AND ff.barrier_category <> 'No barrier reported'
        GROUP BY d.week_number, u.business_unit_key, ff.barrier_category
    ) ranked
    WHERE rn = 1
),
company_wide_wau AS (
    SELECT week_number, COUNT(DISTINCT user_key) AS company_wau
    FROM meaningful_events
    GROUP BY week_number
)
SELECT
    w.week_number,
    w.week_start_date,
    bu.business_unit_name,
    w.wau AS weekly_active_users,
    LAG(w.wau) OVER (PARTITION BY w.business_unit_key ORDER BY w.week_number) AS prior_week_wau,
    w.wau - LAG(w.wau) OVER (PARTITION BY w.business_unit_key ORDER BY w.week_number) AS wau_change_vs_prior_week,
    ROUND(100.0 * w.wau / NULLIF(cw.company_wau, 0), 1) AS pct_of_company_wau_this_week,
    COALESCE(pl.prompt_library_users, 0) AS prompt_library_users,
    ROUND(COALESCE(ms.total_minutes_saved, 0)::NUMERIC / 60.0, 1) AS estimated_hours_saved_modeled,
    COALESCE(fb.feedback_submissions, 0) AS feedback_submissions,
    fb.avg_rating,
    fb.recommendation_rate_pct,
    tb.barrier_category AS top_reported_barrier,
    'Estimated hours saved is a MODELED assumption from synthetic data, not validated ROI.' AS disclaimer
FROM weekly_active_users w
JOIN dim_business_unit bu ON bu.business_unit_key = w.business_unit_key
JOIN company_wide_wau cw ON cw.week_number = w.week_number
LEFT JOIN weekly_minutes_saved ms ON ms.week_number = w.week_number AND ms.business_unit_key = w.business_unit_key
LEFT JOIN weekly_prompt_library_users pl ON pl.week_number = w.week_number AND pl.business_unit_key = w.business_unit_key
LEFT JOIN weekly_feedback fb ON fb.week_number = w.week_number AND fb.business_unit_key = w.business_unit_key
LEFT JOIN weekly_top_barrier tb ON tb.week_number = w.week_number AND tb.business_unit_key = w.business_unit_key
ORDER BY w.week_number, bu.business_unit_name;
