# Power BI Report Design

Three report pages, built manually in Power BI Desktop on top of the model in
`powerbi/dax_measures.md` (see `powerbi/BUILD_INSTRUCTIONS.md` for the
click-by-click build). Every page:

- Carries the visible disclaimer: **"Synthetic portfolio data. Estimated time
  saved is modeled, not validated ROI."** (a text box, bottom of page, gray
  text, present on all three pages)
- Uses the theme in §4 below (navy / medium blue / white / light gray, no
  logos)
- Shows a title, one-line subtitle describing the audience/purpose, and a
  "Last refreshed: [date]" text box driven by a measure:
  `Last Refreshed = "Last refreshed: " & FORMAT(TODAY(), "MMMM d, yyyy")`

---

## Page 1 — Executive Adoption Overview

**Audience:** AI Business Enablement leader and product manager.
**Purpose:** Answer "are we adopting this, and where's it working or not"
in under 30 seconds.

| # | Visual | Type | Fields / measures | Question it answers | How to interpret |
|---|---|---|---|---|---|
| 1 | KPI cards (row of 6) | Card | `Eligible Users`, `Activated Users`, `Activation Rate`, `WAU`, `Median Time to Value Hours`, `Estimated Hours Saved` | "Where do we stand right now, company-wide?" | Read left to right as a funnel-style snapshot; `Estimated Hours Saved` card must show the "modeled" disclaimer as a subtitle. |
| 2 | Weekly trend | Line chart (dual axis) | X: `Calendar[week_number]`; Y1: `WAU`; Y2: `Activation Rate` | "Is engagement growing, and is quality (activation) keeping pace with volume (WAU)?" | A rising WAU line with a flat/falling activation-rate line signals growth in casual use without growth in real adoption — worth flagging. |
| 3 | Adoption funnel | Funnel chart | Stages: `Eligible Users` → `Training Completion Rate` (count) → users with ≥1 meaningful action → `Activated Users` | "Where do we lose people in the journey from access to real use?" | The biggest single drop-off between adjacent stages is the highest-leverage intervention point. |
| 4 | Activation rate by business unit | Clustered bar chart | Axis: `Business_Unit[business_unit_name]`; Value: `Activation Rate` | "Which business units are ahead or behind?" | Compare each bar to the company-wide reference line (see `Activation Rate` as a constant/reference line); bars well below it are enablement targets. |
| 5 | Business-unit matrix | Matrix | Rows: `Business_Unit[business_unit_name]`; Values: `Activated Users`, `Activation Rate`, `WAU`, `Median Time to Value Hours`, `Estimated Hours Saved` | "Give me the full scorecard per business unit in one table." | Use conditional formatting (data bars) on `Activation Rate` and `Median Time to Value Hours` (reversed color scale — lower is better) to make outliers visually obvious. |
| 6 | Slicers | Slicer (x4) | `Calendar[week_number]` (or date range), `Business_Unit[business_unit_name]`, `Role[role_name]`, `Users[rollout_wave]` | Lets a viewer drill into any segment/time window. | Slicers apply to every visual on the page via the model's single-direction relationships. |
| 7 | Dynamic narrative | Card / text box bound to a measure | `Executive Narrative` | "Give me the one-sentence takeaway for whatever I've filtered to." | Re-reads automatically as slicers change; always ends with the "association only" caveat. |
| 8 | Disclaimer text box | Text box | Static text | — | "Synthetic portfolio data. Estimated time saved is modeled, not validated ROI." |

---

## Page 2 — Usage, Features, and Retention

**Audience:** Product analytics and product team.
**Purpose:** Which features work, how fast do users return, and where does
engagement decay.

| # | Visual | Type | Fields / measures | Question it answers | How to interpret |
|---|---|---|---|---|---|
| 1 | Feature adoption | Bar chart | Axis: `Feature_Catalog[feature_name]`; Value: `Feature Adoption Rate` | "Which features are actually driving completed, repeat use?" | Compare against the "broadly adopted" vs. "technical-audience" feature split — expect Knowledge Search/Document Summarization high, Code Assistant/Data Analysis structurally lower company-wide (see caveat in `docs/metric_dictionary.md`). |
| 2 | Feature usage trend | Line chart, multi-series | X: `Calendar[week_number]`; Y: distinct-user count of `feature_completed`/`output_exported` events; Legend: `Feature_Catalog[feature_name]` | "Is a feature's popularity growing, flat, or fading?" | A feature released later (Data Analysis, Code Assistant) should show a later ramp-up start — confirms the phased-release design is reflected correctly. |
| 3 | Cohort retention heatmap | Matrix (conditional-formatted as heatmap) | Rows: `Users[Activation Week]`; Columns: `'Weeks Since Activation'[WeeksOut]` (0-8); Values: `Retention % (heatmap)` | "How well do we retain users after their first real engagement, and is that improving over time?" | Darker/greener cells = higher retention; scan down a column to compare cohorts, and across a row to see decay within one cohort. |
| 4 | Time-to-value distribution | Histogram (Users table, `Hours To Value` binned) | Axis: `Hours To Value` (binned, e.g. 12-hour bins); Value: count of users | "How long does it typically take a new user to get real value?" | A left-skewed distribution (most users fast) with a long right tail highlights a subset who take much longer — a training/onboarding opportunity. |
| 5 | Stickiness by business unit | Clustered bar chart | Axis: `Business_Unit[business_unit_name]`; Value: `Stickiness WAU/MAU` | "Where is engagement most habitual vs. most occasional?" | Reminder: stickiness is a proxy for depth, not value — pair with the feature adoption chart before concluding a high-stickiness unit is a "success." |
| 6 | Training vs. activation scatter | Scatter chart | X: `Training Completion Rate`; Y: `Activation Rate`; Legend/size: `Business_Unit[business_unit_name]` (bubble size = `Eligible Users`) | "Is training completion associated with higher activation, by business unit?" | A positive-sloping pattern supports the association documented in `docs/metric_dictionary.md` — **label this visual explicitly as association, not causation**, since training completion isn't randomly assigned. |
| 7 | Role-by-feature heatmap | Matrix (conditional-formatted) | Rows: `Role[role_name]`; Columns: `Feature_Catalog[feature_name]`; Values: `Feature Adoption Rate` | "Which roles use which features?" | Expect a visible block pattern: Developers/Analysts high on Code Assistant/Data Analysis, Relationship Managers/Managers high on Drafting Assistant/Meeting Notes. |
| 8 | Dormant users + trend | Card (`Dormant Users`) + line chart (`Dormancy Rate` by week) | `Dormant Users`, `Dormancy Rate` over `Calendar[week_number]` | "How big is our re-engagement backlog, and is it growing?" | A rising dormancy-rate trend late in the rollout is an early warning sign, independent of headline WAU growth. |
| 9 | Interpretation text box | Text box | Static text | — | "This page is for the product team: use it to decide which features to invest enablement effort in, and which cohorts need a re-engagement nudge. Retention and stickiness are *proxies* for value, not proof of it — cross-check against qualitative feedback on Page 3 before prioritizing." |

---

## Page 3 — Barriers, Feedback, and Actions

**Audience:** Enablement, training, and rollout teams.
**Purpose:** What's stopping adoption, in users' own (synthetic) words, and
what should we do next week.

| # | Visual | Type | Fields / measures | Question it answers | How to interpret |
|---|---|---|---|---|---|
| 1 | Feedback KPI cards | Card (x2) | `Average Feedback Rating`, `Recommendation Rate` | "What's the overall sentiment pulse?" | Read alongside the barrier chart below — a mediocre average rating with one dominant barrier is more actionable than a mediocre rating with no clear pattern. |
| 2 | Barriers by business unit | Stacked bar chart | Axis: `Business_Unit[business_unit_name]`; Value: count of `Feedback` rows; Legend: `Feedback[barrier_category]` (excluding "No barrier reported") | "What's uniquely holding back each business unit?" | Expect Risk and Compliance to skew toward "Privacy or compliance concern" / "Unsure what use cases are allowed," and Retail Banking/Operations toward "No time to learn" / "Lack of relevant training" (by generator design). |
| 3 | Feature satisfaction | Bar chart | Axis: `Feature_Catalog[feature_name]`; Value: `Average Feedback Rating` (filtered to feedback tied to that feature) | "Which features have the best/worst user sentiment?" | A feature with high adoption (Page 2) but low satisfaction here is a "fix the experience" priority, not a "promote it more" priority. |
| 4 | Anonymized feedback table | Table | `Feedback[feedback_timestamp]`, `Feedback[sentiment_label]`, `Feedback[barrier_category]`, `Feedback[free_text_feedback]`, `Feedback[feature_name]` (no `user_id`/name shown) | "What are people actually saying?" | All comments are synthetic, templated text (see `data/synthetic_data_dictionary.md`) — useful for illustrating the *kind* of feedback pattern, not as real quotes. |
| 5 | Segment action matrix | Matrix | Rows: `Business_Unit[business_unit_name]`; Values: `Activation Rate`, `Training Completion Rate`, `Top Barrier Category`, + a manually-authored "Suggested Intervention" column (see note below) | "One table I can take into a leadership meeting." | `Top Barrier Category` is dynamic (DAX measure); the "Suggested Intervention" text is authored by the analyst per segment (not a DAX measure) — pair each row's numbers with a specific, proportionate action. |
| 6 | Prioritization quadrant | Scatter chart | X: `Eligible Users`; Y: `Activation Rate`; quadrant lines at the median of each axis; Legend: `Business_Unit[business_unit_name]` | "Where should enablement effort go first?" | Four quadrants: (low activation, high eligible users) = biggest-impact fix target; (low activation, low training completion) = training-gap target; (high activity, low satisfaction) = experience-fix target; (high activity, high satisfaction) = protect/showcase as a reference case. |
| 7 | Recommended actions table | Table (manually authored, not a DAX measure) | Columns: Segment, Observed Signal, Recommended Action, Owner, Expected Measurement | "What do we actually do next week?" | This table is written by the analyst from the quadrant + matrix above, following the exact structure used in `docs/executive_weekly_readout.md` — keep it to 3-5 rows so it stays actionable. |

**Suggested Intervention / Recommended Actions authoring note:** these two
columns are the one place on the report that is *not* a live DAX
measure — they are analyst judgment calls, written the same way the Week 24
memo's "Recommended Actions" section is written (see
`docs/executive_weekly_readout.md`), and should be refreshed manually each
reporting period alongside the memo, not expected to auto-update.

---

## 4. Theme

Bank-style, accessible, no branding:

| Role | Color | Hex |
|---|---|---|
| Primary (titles, top KPI accents) | Navy | `#1B3A6B` |
| Secondary (bars, lines) | Medium blue | `#2F5F9E` |
| Tertiary (secondary series) | Light blue | `#5B8FC7` |
| Background | White | `#FFFFFF` |
| Panel/card background | Light gray | `#F2F4F7` |
| Negative/warning accent (used sparingly — e.g. dormancy, low satisfaction) | Muted red | `#A3324A` |
| Body text | Dark gray | `#2B2B2B` |

Apply via **View → Themes → Browse for themes**, importing a small JSON theme
file built from these hex values (Power BI Desktop: Customize current theme →
paste these under Name/Dataviz colors). Keep font at the Power BI default
(Segoe UI), 10-11pt for body text, 14-16pt bold for page titles, consistent
across all three pages. No RBC or any real company logo anywhere in the
report.

**General visual hygiene applied to every page:** remove gridlines except
light horizontal ones on bar/line charts; data labels only where they add
information a viewer can't get from the axis; consistent 2-decimal-or-less
number formatting on percentages; every visual has a one-line title stating
the metric, not just the chart type.
