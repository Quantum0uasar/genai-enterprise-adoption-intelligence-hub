# Assumptions and Limitations

*Covers generation (Phase 1), cleaning (Phase 2), SQL/analysis (Phases 3-4),
and Power BI/Excel (Phases 5-6) modeling choices. Read alongside
`data/synthetic_data_dictionary.md`, `docs/metric_dictionary.md`, and
`docs/data_model.md`.*

## Integrity statement

- All data in this repository — users, events, feedback, training sessions,
  ratings, and free-text comments — is **synthetically generated**. It does
  not come from, and is not modeled on, any specific real company's data.
- The organization ("Northstar Financial Group") and product ("Northstar
  Assist") are **fictional**. This project makes no claim of affiliation with
  or access to RBC, TD, or any real financial institution.
- Any "estimated minutes/hours saved" figures are **modeled assumptions**
  baked into the data generator (a plausible per-feature range sampled
  randomly), not measurements of real productivity, and not validated ROI.
- Where the generator builds in a correlation (e.g., "Prompt Library use is
  more common among power users," "training completion shifts activity level
  upward," "Risk and Compliance sentiment improves later in the rollout"),
  that correlation is a **designed data-generation assumption** used to make
  the dataset realistic enough for analysis practice. It is not evidence of a
  causal relationship, and later analysis phases will describe these patterns
  as associations only.

## Key generation assumptions

1. **Rollout structure.** 24 weeks, 6 waves of 4 weeks each, starting
   2026-01-05. Business units are assigned wave-probability distributions
   reflecting the scenario brief (Technology/Capital Markets earlier;
   Risk and Compliance later).
2. **Activation-adjacent behavior is simulated at the individual-event level,
   not computed here.** The generator produces raw events; whether a given
   user counts as "activated" under the project's formal metric definition
   (see `docs/metric_dictionary.md`, to be completed in a later phase) is
   calculated downstream, not hard-coded per user.
3. **Activity level.** Each user is probabilistically assigned a hidden
   "none / light / moderate / power" engagement level based on business unit,
   role, manager-champion status, and training completion, with intentional
   randomness so that training and champions influence but do not fully
   determine engagement (reflecting the brief's requirement that "training
   should improve, but not perfectly determine, activation").
4. **Feature access windows.** `Data Analysis` and `Code Assistant` release
   in weeks 5 and 7 respectively (phased technical-feature rollout); the
   other 6 features are available from week 1. Events cannot reference a
   feature before its release week.
5. **Training sessions vs. individual training records.** `training_sessions.csv`
   is an aggregate log of scheduled/instructor-led sessions per business unit.
   `users.csv`'s `training_assigned_date`/`training_completed_date` are
   generated independently per user and are not joined row-for-row to a
   specific session — this reflects that some completions may be self-paced
   eLearning not tied to a scheduled session. This is a simplification made
   for a portfolio-scale project; a production system would maintain an
   explicit attendance-record table.
6. **Free-text feedback is templated, not generative.** Comments in
   `feedback.csv` are drawn from a small set of hand-written synthetic
   sentence templates keyed to barrier category and sentiment, not produced
   by a language model and not real employee statements.

## Known limitations

- The dataset is a simplification of real enterprise telemetry: it does not
  model things like multi-turn conversation context, organizational
  hierarchy effects beyond `manager_level`, seasonal business cycles, or
  attrition/new-hire churn during the rollout window.
- Random-seed determinism (seed = 42) makes the dataset perfectly
  reproducible, but also means all "realism" comes from the hand-tuned
  probability distributions in `src/generate_synthetic_data.py`, not from
  any real observed behavior.
- Correlational patterns designed into the data (training ↔ activation,
  manager champions ↔ engagement, Prompt Library ↔ retention) are intended
  to give later analysis something meaningful to find — they should not be
  read as validation that these relationships hold in a real deployment.

## Cleaning-pipeline assumptions (`src/transform_data.py`, Phase 2)

1. **Negative values are nulled, not row-deleted.** A negative
   `session_duration_seconds` or `estimated_minutes_saved` is treated as a
   corrupted *value*, not a corrupted *event* — the field is set to null and
   logged, but the rest of the event (event_type, feature_name, timestamp)
   is retained. An alternative, equally defensible design would drop the
   whole row; this project's choice preserves more usable data at the cost
   of a slightly more complex null-handling story downstream.
2. **Out-of-range feedback ratings are nulled, not row-deleted**, for the
   same reason — `sentiment_label`, `barrier_category`, and
   `free_text_feedback` remain informative even when `rating_1_to_5` is
   corrupted.
3. **Events before `assigned_access_date` are removed entirely** (not
   nulled), because a business-rule violation on the timestamp itself makes
   the whole event's timing untrustworthy, unlike a negative numeric field
   which is an isolated corruption.
4. **Events after the rollout's last calendar day are removed entirely**,
   for the same reason — added after a real bug surfaced during Phase 3
   PostgreSQL validation (see `sql/README_VALIDATION.md`) where a handful of
   generator-produced events fell past `calendar.csv`'s date range.
5. **No missing value is ever invented.** Missing `assigned_access_date`,
   `manager_champion_flag`, `feature_name`, or `free_text_feedback` are
   retained as null and documented in `data/processed/data_quality_issues.csv`
   with an explicit count and resolution, never filled with an assumed value.

## Metric-definition assumptions (`docs/metric_dictionary.md`, Phases 3-4)

1. **Feature Adoption Rate's denominator is all eligible users**, not a
   feature-specific target persona. This is a simplification: features aimed
   at a narrow technical audience (Code Assistant, Data Analysis) will
   structurally show lower company-wide adoption rates than broadly-targeted
   features, even if uptake within their intended audience is strong. Always
   pair the company-wide figure with the role/business-unit breakdown.
2. **Retention cohorts are anchored to "week of first meaningful action,"**
   a simpler, purely date-driven proxy for "activation week" — not identical
   to the full formal Activated User definition, which also requires a
   training/Prompt-Library qualifying condition. The two populations overlap
   heavily but are not the same set.
3. **Dormancy and MAU use a fixed "as of" reference date** (the maximum
   event timestamp in the dataset), since this project has no live current
   date to report against. A production system would use the actual current
   date.
4. **"Estimated productivity time saved" is aggregated exactly as generated**
   (summed from `estimated_minutes_saved`), with no attempt to adjust,
   discount, or validate it against any external benchmark — because none
   exists for a fictional product. Any hours-saved figure in this project
   is a **relative, directional signal for portfolio purposes only.**

## Power BI / Excel modeling assumptions (Phases 5-6)

1. **Power BI's import model uses natural keys** (`user_id`,
   `feature_name`, `business_unit_name`, calendar `date`) instead of the
   PostgreSQL model's surrogate integer keys, since Power Query/DAX work
   naturally with text keys and there is no ETL-performance reason to
   introduce surrogates at this dataset's scale. See `docs/data_model.md`.
2. **A synthetic "Unknown / Not Captured" feature-dimension row** is added
   in both the SQL and Power BI models so that fact rows with a missing
   `feature_name` never produce a broken join or an inconsistent blank-row
   behavior across visuals.
3. **The Excel workbook (`excel/GenAI_Weekly_Adoption_Readout.xlsx`) was
   built programmatically with `openpyxl`**, not through Power Query's UI —
   see `excel/excel_build_guide.md` for exactly which capabilities that
   implies (real Excel Tables, formulas, and conditional formatting) versus
   which require the student to complete manually in the Excel desktop app
   (an interactive Power Query connection, PivotTable slicers). The guide is
   explicit about this boundary rather than implying more automation than
   was actually achieved.

## Known limitations (all phases)

- The dataset is a simplification of real enterprise telemetry: it does not
  model things like multi-turn conversation context, organizational
  hierarchy effects beyond `manager_level`, seasonal business cycles, or
  attrition/new-hire churn during the rollout window.
- Random-seed determinism (seed = 42) makes the dataset perfectly
  reproducible, but also means all "realism" comes from the hand-tuned
  probability distributions in `src/generate_synthetic_data.py`, not from
  any real observed behavior.
- `fact_training_attendance` / `Training_Sessions` is grained at the
  **scheduled session** level (aggregate registered/attended/completed
  counts), not the individual attendee level — it cannot be joined to
  `dim_user`/`Users` directly. Individual training status lives on
  `dim_user.training_completed_date` instead.
- No part of this project performs statistical significance testing,
  regression adjustment, or any other technique that would be required to
  support a causal claim. Every "association" reported in the executive
  memo, notebooks, or SQL output is exactly that — an association observed
  in one synthetic dataset — and is worded accordingly.
