# SQL Validation Log

**All queries in this folder were actually executed**, not just written, against
a real PostgreSQL 16 instance during development, using the processed
synthetic CSVs in `data/processed/`. This log documents exactly what was run
and confirms it worked, so nothing here is an unverified claim.

## Environment

- PostgreSQL 16.13 (Ubuntu package `postgresql-16`)
- Database: `genai_adoption`
- Loaded via: `psql -d genai_adoption -f sql/01_create_schema.sql` (run from
  the repository root so the `\copy` paths resolve)

## What was run and the result

| Script | Result |
|---|---|
| `sql/01_create_schema.sql` | Ran end-to-end with no errors. Loaded 6,000 users, 236,960 usage events, 7,677 feedback rows, 61 training sessions, 8 features, 168 calendar days into staging, then built and populated all 5 dimension tables and all 3 fact tables. Post-load row counts matched the source `clean_*.csv` files exactly (verified with the validation `SELECT` at the end of the script). |
| `sql/02_adoption_metrics.sql` | All 9 queries ran with no errors and returned plausible, non-empty result sets (e.g. Query 1 returned 192 rows — 24 weeks × 8 business units; Query 9 returned 8 rows, one per business unit, with dormancy rates ranging ~13%–32%). |
| `sql/03_weekly_insights.sql` | Ran with no errors, returned 192 rows (24 weeks × 8 business units), including correctly computed week-over-week WAU deltas via `LAG()`. |

## A real bug this validation caught

Running `01_create_schema.sql` against real PostgreSQL surfaced an actual
data-generation bug: 4 out of 238,617 raw usage events (a rare "curiosity"
`app_opened` event for otherwise-inactive users) were timestamped up to 4 days
past the 24-week rollout's last calendar day, which violated the
`fact_usage_events.date_key` foreign key against `dim_date`. This was fixed
at the source in `src/generate_synthetic_data.py` (the date is now clamped to
the rollout window), the raw/processed data was regenerated, and
`src/transform_data.py` gained an explicit "events after rollout end" check
(mirroring the existing "events before access date" check) so this class of
issue is now caught and logged by the cleaning pipeline even if reintroduced.
This is a good example of why "run it against a real database" is worth doing
instead of only checking SQL syntax.

## Reproducing this validation yourself

```bash
# 1. Regenerate the data (from repo root)
python src/generate_synthetic_data.py
python src/transform_data.py

# 2. Stand up a local PostgreSQL database (adjust to your setup)
createdb genai_adoption

# 3. Build the schema and load data
psql -d genai_adoption -f sql/01_create_schema.sql

# 4. Run the analytical queries
psql -d genai_adoption -f sql/02_adoption_metrics.sql
psql -d genai_adoption -f sql/03_weekly_insights.sql
```

If PostgreSQL isn't available locally, every query is still readable and
reviewable as plain, standard PostgreSQL-dialect SQL (CTEs, window functions,
`FILTER`, `PERCENTILE_CONT`) — see `docs/data_model.md` for the schema
narrative without needing a running database.
