# Metric Dictionary

Every metric below is computed from the fictional Northstar Financial Group /
Northstar Assist **synthetic** dataset. Each metric is implemented in three
places, kept consistent by design:

- Python: `src/analysis.py`
- SQL: `sql/02_adoption_metrics.sql` / `sql/03_weekly_insights.sql`
- Power BI: `powerbi/dax_measures.md`

Read this document before interpreting any chart, notebook output, SQL
result, or Power BI visual in this project.

---

### Eligible Users

- **Numerator/definition:** Count of users where `eligible_for_access_flag = TRUE` AND `assigned_access_date` is not null.
- **Denominator:** N/A (a base count).
- **Timeframe:** As of the reporting date (or "as of" the max date in the dataset for a point-in-time snapshot).
- **Purpose:** The base population every other adoption metric is measured against.
- **Caveat:** A small number of users have `assigned_access_date` populated but `eligible_for_access_flag = FALSE` (an entitlement-lag data-quality pattern, documented in `data/synthetic_data_dictionary.md`) — these are correctly excluded here.
- **Interpretation example:** "5,693 of 6,000 synthetic users are eligible as of the current reporting date; the remaining 307 are pending eligibility or access."

### Activated User / Activation Rate

- **Numerator (Activated User):** An eligible user who (completed training **OR** used the Prompt Library at least once) **AND** completed ≥ 3 "meaningful actions" (`prompt_submitted`, `output_generated`, `feature_completed`, `output_exported`) within 14 days of `assigned_access_date`.
- **Activation Rate = Activated Users / Eligible Users.**
- **Timeframe:** Evaluated as a point-in-time status (a user is or isn't activated based on their first 14 days), aggregable by any dimension (business unit, role, rollout wave).
- **Purpose:** Distinguishes "got access" from "got real value" — the core adoption KPI leadership tracks.
- **Caveat:** This is a **designed, association-based definition**, not a validated behavioral science model of "true" activation, and the qualifying threshold (3 actions in 14 days) is a reasonable but arbitrary choice. Training completion is not randomly assigned in this dataset, so activation differences by training status are associations, not proof that training *causes* activation.
- **Interpretation example:** "Technology shows a 94% activation rate vs. 72% in Retail Banking — worth investigating whether that gap reflects role fit, training format, or time constraints, not proof of any single cause."

### Weekly Active Users (WAU)

- **Numerator/definition:** Distinct users with ≥ 1 meaningful action in a given calendar week.
- **Denominator:** N/A (a count).
- **Timeframe:** Per rollout week (1–24).
- **Purpose:** The standard week-over-week adoption pulse metric.
- **Caveat:** Counts *any* meaningful action equally — a single quick prompt counts the same as a full research session.
- **Interpretation example:** "WAU grew from 253 in week 1 to over 2,000 by week 20 — but check the underlying business-unit mix before assuming broad-based growth (see WAU-by-business-unit chart)."

### Monthly Active Users (MAU, trailing 28 days)

- **Numerator/definition:** Distinct users with ≥ 1 meaningful action in the trailing 28 days as of a reference date.
- **Denominator:** N/A (a count).
- **Timeframe:** Rolling 28-day window ending at the reference/reporting date.
- **Purpose:** A less noisy, longer-window view of the active base than WAU.
- **Caveat:** A rolling window means MAU on any given day reflects up to 4 weeks of history, which can mask a recent sharp change.
- **Interpretation example:** "MAU of ~3,500 as of the last event in the dataset means roughly 58% of all 6,000 (synthetic) employees engaged at least once in the trailing month."

### Stickiness (WAU / MAU)

- **Numerator/definition:** WAU ÷ MAU (28-day), expressed as a percentage.
- **Timeframe:** A given week's WAU over the MAU ending that week.
- **Purpose:** A commonly used *proxy* for engagement depth/habitual use.
- **Caveat:** **This is a proxy for engagement depth, not a complete measure of value delivered.** A small, highly repeat-engaged group can produce the same ratio as a larger, lightly engaged one — always read alongside WAU and feature adoption, never alone.
- **Interpretation example:** "Stickiness around 70-75% in the back half of the rollout suggests most monthly users are also weekly users — a sign of habit formation, not proof that the habit is valuable."

### Feature Adoption Rate

- **Numerator/definition:** Distinct users who `feature_completed` or `output_exported` a given feature.
- **Denominator:** Distinct eligible users (simplification — see caveat).
- **Timeframe:** Cumulative over the analysis window (typically the full rollout-to-date).
- **Purpose:** Identifies which features are actually driving repeat, completed use vs. just being opened/tried.
- **Caveat:** The denominator used here is **all eligible users**, not a feature-specific target persona (e.g. Code Assistant's true addressable audience is really just Developers/Analysts). This means adoption rates for narrowly-targeted features (Code Assistant, Data Analysis) will structurally read lower than broadly-targeted ones (Knowledge Search) even if uptake *within their target persona* is strong. Always pair this metric with the role/business-unit cut (Query 3 / `feature_adoption_rate(groupby=...)`) before concluding a feature is underperforming.
- **Interpretation example:** "Code Assistant's company-wide adoption rate (19.2%) looks low next to Knowledge Search (55.8%) — but within Technology/Developer, Code Assistant's adoption rate is far higher, which is the more meaningful comparison."

### Time-to-Value

- **Numerator/definition:** Hours from `assigned_access_date` to the user's first successful `feature_completed`, `output_exported`, or `output_generated` event.
- **Denominator:** N/A (a per-user duration; reported as a median across a group).
- **Timeframe:** Measured once per user (their first qualifying event).
- **Purpose:** How quickly new users get to a real, completed outcome — a core "time-to-value" onboarding metric.
- **Caveat:** Only computed for users who *did* reach a first successful action; users who never did are excluded from this metric (and should be read alongside the activation rate and dormancy metrics, not in isolation).
- **Interpretation example:** "Risk and Compliance has the *fastest* median time-to-value (13.2 hours) despite having the slowest WAU ramp — suggesting that once Risk and Compliance users engage, they reach value quickly; the barrier there is likely activation/access confidence, not the product itself."

### Retention (weekly activation cohort)

- **Numerator/definition:** Distinct users from a given cohort (grouped by the week of their first meaningful action) who are active again in cohort week + N.
- **Denominator:** Total users in that cohort.
- **Timeframe:** Weeks 0–8 after each cohort's start week.
- **Purpose:** Shows whether new-user engagement holds up over time, and whether later cohorts retain better/worse than earlier ones (e.g. as training and communications matured).
- **Caveat:** The cohort here is anchored to "week of first meaningful action" (an activation-week proxy), which is a simpler, purely date-driven definition than the full formal "Activated User" definition above — the two are related but not identical populations.
- **Interpretation example:** "Week-1 cohort retention falls from 100% (week 0, by definition) to ~56% by week 8 — a meaningful but not catastrophic decline, worth comparing against later cohorts to see if retention improved as onboarding matured."

### Dormancy / Dormant Users

- **Numerator/definition:** Activated users with **no** meaningful action in the trailing 28 days as of the reference date.
- **Denominator:** Activated users (for the Dormancy Rate %).
- **Timeframe:** Rolling 28-day window as of the reference/reporting date.
- **Purpose:** Flags previously-engaged users who have gone quiet — a re-engagement target list for enablement teams.
- **Caveat:** Dormancy is inherently sensitive to the reference date chosen; a user "dormant" today may simply be between usage bursts.
- **Interpretation example:** "Retail Banking has both the most activated users and the highest dormancy rate (~32%) — a large re-engagement opportunity, whereas Risk and Compliance's lower dormancy rate (~12%) suggests better-sustained engagement once activated."

### Training Completion Rate

- **Numerator/definition:** Users with a non-null `training_completed_date`.
- **Denominator:** Users with a non-null `training_assigned_date`.
- **Timeframe:** Cumulative (any time up to the reporting date).
- **Purpose:** A direct enablement-team KPI — are assigned trainings actually getting completed?
- **Caveat:** Doesn't capture training *quality* or relevance, only completion.
- **Interpretation example:** "Retail Banking's 55% completion rate (by generator design, reflecting time-constrained frontline schedules) is the lowest of all business units — a candidate root cause for its lower activation rate."

### Estimated Productivity Time Saved

- **Numerator/definition:** Sum of `estimated_minutes_saved` across successful `feature_completed` / `output_exported` / `output_generated` events.
- **Denominator:** N/A (a total, or divided by user/feature count for an average).
- **Timeframe:** Cumulative over the analysis window.
- **Purpose:** A directional, feature-level signal of where the tool may be delivering the most value.
- **Caveat — the most important one in this project:** `estimated_minutes_saved` is a **modeled assumption sampled by the synthetic data generator** (a plausible per-feature range, not a measurement). **It is not validated ROI, not a causal estimate, and must never be reported as real productivity impact.** Treat it purely as a relative, directional signal for a portfolio exercise.
- **Interpretation example:** "Document Summarization's high total estimated-minutes-saved is a function of its high usage volume *and* its assumed per-action range, both of which are modeling choices — this number supports a discussion about where to invest enablement effort, not a finance-grade ROI claim."

### Recommendation Rate

- **Numerator/definition:** Feedback submissions where `would_recommend_flag = TRUE`.
- **Denominator:** All feedback submissions with a non-null `would_recommend_flag`.
- **Timeframe:** Cumulative, or by week/business unit.
- **Purpose:** A simple NPS-style pulse on user sentiment, easy to trend over time.
- **Caveat:** Feedback is self-selected (users choose to submit it), so it may not represent the full eligible population evenly across business units or activity levels.
- **Interpretation example:** "A 66% company-wide recommendation rate, with Risk and Compliance below average early in the rollout and climbing later — consistent with the sentiment-improvement pattern designed into this business unit's synthetic feedback."

---

## A note on causal language

None of the metrics above establish causation. Where two metrics move
together in this dataset (training completion and activation rate; manager
champions and engagement; Prompt Library use and retention), that
relationship was **deliberately designed into the synthetic data generator**
to give this project something realistic to analyze — it is not evidence
that either factor *causes* the other, in this dataset or in any real
deployment. See `docs/assumptions_and_limitations.md` for the full integrity
statement.
