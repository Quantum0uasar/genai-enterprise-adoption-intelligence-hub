# Power BI Build Instructions

## Why there is no `.pbix` file in this repository

A `.pbix` is a binary file that only Power BI Desktop can meaningfully create
or validate — there is no way to generate one programmatically here and
honestly claim it opens correctly, contains working relationships, or
renders the visuals in `powerbi/report_design.md`. Rather than fabricate a
binary that can't be verified, this project ships everything needed to build
the real thing yourself in Power BI Desktop in well under an hour:

- `powerbi/dax_measures.md` — the exact model (tables, relationships,
  cardinalities, filter directions) and every measure's DAX, already
  cross-checked against the equivalent, already-executed Python
  (`src/analysis.py`) and SQL (`sql/02_adoption_metrics.sql`) logic.
- `powerbi/report_design.md` — all three report pages, visual-by-visual,
  with exact fields/measures and interpretation notes.
- `data/processed/clean_*.csv` — the data to import, already cleaned and
  validated (see `data/processed/data_quality_summary.md`).

This is an intentional, disclosed choice, not a shortcut: **the `.pbix` is
meant to be built manually in Power BI Desktop**, and doing so is itself part
of demonstrating the skill this project is meant to showcase.

## Prerequisites

- Power BI Desktop (Windows; free download from Microsoft)
- This repository cloned locally, with `data/processed/clean_*.csv` already
  generated (`python src/generate_synthetic_data.py && python src/transform_data.py`
  from the repo root)

## Step 1 — Get Data

1. Open Power BI Desktop → **Get Data → Text/CSV**.
2. Import each of the 6 files individually from `data/processed/`:
   `clean_users.csv`, `clean_usage_events.csv`, `clean_feedback.csv`,
   `clean_training_sessions.csv`, `clean_feature_catalog.csv`,
   `clean_calendar.csv`.
3. On each import, click **Transform Data** (not "Load") so you land in
   Power Query Editor before anything is loaded — you'll fix data types there.
4. Rename each query to match the table names in `powerbi/dax_measures.md`
   §1 (e.g. `clean_users` → `Users`, `clean_usage_events` → `Usage_Events`,
   etc.) via the Query Settings pane on the right.

## Step 2 — Power Query type fixes (per table)

The CSVs are already clean (see `data/processed/data_quality_summary.md`),
so this step is about confirming Power Query auto-detected types correctly,
not further cleaning:

- **Users**: confirm `hire_date`, `assigned_access_date`,
  `training_assigned_date`, `training_completed_date` are **Date** type (not
  Date/Time); `rollout_wave` is **Whole Number**; `manager_champion_flag`,
  `eligible_for_access_flag` are **True/False**.
- **Usage_Events**: confirm `event_timestamp` is **Date/Time**;
  `estimated_minutes_saved`, `session_duration_seconds` are **Decimal
  Number**; `output_exported_flag`, `successful_completion_flag`,
  `error_flag` are **True/False**.
- **Feedback**: confirm `feedback_timestamp` is **Date/Time**;
  `rating_1_to_5` is **Whole Number** (it will show blanks for the ~15
  nulled out-of-range ratings — that's expected, see the data quality log);
  `would_recommend_flag` is **True/False**.
- **Training_Sessions**: confirm `session_date` is **Date**;
  `registered_count`/`attended_count`/`completion_count` are **Whole Number**.
- **Feature_Catalog**: confirm `release_date` is **Date**;
  `core_feature_flag` is **True/False**.
- **Calendar**: confirm `date`/`week_start_date` are **Date**;
  `week_number`/`month`/`quarter`/`year` are **Whole Number**.

## Step 3 — Add the calculated helper columns (in Power Query, before loading)

1. On **Usage_Events**, add a custom column: `event_date` =
   `Date.From([event_timestamp])`, type **Date**.
2. On **Feedback**, add a custom column: `feedback_date` =
   `Date.From([feedback_timestamp])`, type **Date**.
3. On **Feature_Catalog**, use **Home → Enter Data** to append one row:
   `feature_id = "F00"`, `feature_name = "Unknown / Not Captured"`,
   `feature_category = "Unknown"`, `target_persona = "Unknown"`,
   `release_date = null`, `core_feature_flag = null` — then **Append
   Queries** (Home → Append Queries → Append as New, or merge into the
   existing Feature_Catalog query) so this row loads alongside the real 8
   features. This mirrors the `-1` "Unknown" member used in the PostgreSQL
   model (`sql/01_create_schema.sql`) so a null `feature_name` never breaks a
   relationship.
4. Build **Business_Unit** and **Role** as small reference dimensions:
   right-click **Users** → **Reference** → rename to `Business_Unit` → keep
   only the `business_unit` column → **Remove Duplicates** → rename the
   column to `business_unit_name`. Repeat for `Role` (source column `role`,
   rename to `role_name`).
5. Click **Close & Apply**.

## Step 4 — Build relationships

Go to **Model view** and create each relationship listed in
`powerbi/dax_measures.md` §2 via drag-and-drop (drag the "many" column onto
the "one" column) or **Manage Relationships → New**. Set cardinality to
**Many to one (*:1)** and cross-filter direction to **Single** for every one
of them — do not accept Power BI's "Both" auto-suggestion if it offers it.

## Step 5 — Mark the date table

**Modeling ribbon → Mark as Date Table**, select the `Calendar` table, and
confirm `date` as the date column. This is required before the time-
intelligence measures (`Previous Week WAU`, using `DATEADD`) will work
correctly.

## Step 6 — Hide technical fields

In **Model view**, right-click and **Hide in Report View** for:
`Usage_Events[event_id]`, `Usage_Events[session_id]`,
`Feedback[feedback_id]`, `Training_Sessions[training_session_id]`,
`Feature_Catalog[feature_id]`.

## Step 7 — Add calculated columns and measures

Open a new table via **Table Tools → New Table** for the disconnected
"Weeks Since Activation" table:

```dax
Weeks Since Activation = GENERATESERIES(0, 8, 1)
```

Rename its single column to `WeeksOut`. Then, on the **Users** table,
add each calculated column from `powerbi/dax_measures.md` §3, in the order
listed (later columns depend on earlier ones). Finally, create every measure
in §4 (right-click a table in the Fields pane → **New Measure**; a common
convention is to put all measures in the `Users` table or a dedicated blank
"_Measures" table — either works).

**Validate as you go:** after adding each measure, drop it into a blank card
visual and compare the number to the equivalent output already computed and
saved in this repo — `src/analysis.py`'s printed output, or a row from
`sql/02_adoption_metrics.sql` / `sql/03_weekly_insights.sql`. They should
match (small differences are expected only for measures using a "trailing 28
days as of today" pattern, since Python/SQL freeze `as_of_date` at the
dataset's max event date while `TODAY()` in DAX reflects your build date).

## Step 8 — Build the three report pages

Follow `powerbi/report_design.md` visual-by-visual. Apply the theme from its
§4 (**View → Themes → Customize current theme**, paste in the hex values).
Add the disclaimer text box to each page: *"Synthetic portfolio data.
Estimated time saved is modeled, not validated ROI."*

## Step 9 — Save and screenshot

Save as `powerbi/GenAI_Adoption_Intelligence.pbix` (this path is
`.gitignore`d — see below — so it stays local to your machine unless you
choose to commit it). Take screenshots of all three pages and add them to
`docs/project_screenshots/` for the README.

## A note on committing the `.pbix` yourself

If you build this and want to commit the resulting `.pbix` to your fork,
that's entirely reasonable — just be aware `.pbix` files are binary and can
grow large with embedded data; consider Git LFS if you do. This repository's
`.gitignore` excludes local Power BI temp/lock files (`~$*.pbix`) but does
**not** block a real `.pbix` from being added if you choose to.
