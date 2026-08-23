# GenAI Adoption Weekly Readout

**Reporting period:** Week 24 of 24 (rollout complete) — week of 2026-06-15
**Prepared for:** AI Business Enablement leadership
**Scope:** Northstar Financial Group / Northstar Assist — a **fictional
organization and product**. All figures below are computed from a
**synthetic, randomly generated dataset** (`src/generate_synthetic_data.py`,
seed = 42) and are reproducible from this repository. Nothing in this memo
represents RBC, TD, or any real financial institution, and no figure here
should be read as validated ROI or proof of a causal relationship.

---

## 5 KPIs

| KPI | Value | Source |
|---|---|---|
| Activation Rate | **78.6%** (4,475 of 5,693 eligible users) | `src/analysis.py: activation_rate()` |
| Weekly Active Users (Week 24) | **2,564** (up from 253 in Week 1) | `sql/02_adoption_metrics.sql` Query 1 |
| Median Time-to-Value | **14.4 hours**, company-wide | `src/analysis.py: median_time_to_value()` |
| Training Completion Rate | **66.2%**, company-wide | `src/analysis.py: training_completion_rate()` |
| Estimated Hours Saved (modeled) | **28,086 hours** — *modeled assumption, not validated ROI* | `src/analysis.py: estimated_time_saved()` |

---

## Findings

**1. Retail Banking combines the largest eligible population with the lowest activation rate and lowest training completion.**
Retail Banking carries 1,652 eligible users — the largest of any business
unit — but its activation rate (71.9%) and training completion rate (52.2%,
the lowest company-wide) both trail the company average. *Metric:*
`activation_rate(groupby='business_unit')` and
`training_completion_rate(groupby='business_unit')`.

**2. Training completion is associated with a meaningfully higher activation rate, but this dataset does not prove training causes activation.**
Users who completed training show an 85.0% activation rate, versus 65.9%
for those who didn't — a ~19-point gap. Training completion is not randomly
assigned in this dataset (or in reality), so motivated, well-supported
employees may complete training *and* activate for reasons unrelated to the
training itself. *Metric:* `training_vs_activation()`.

**3. Prompt Library adoption lags in exactly the high-volume business units most likely to benefit from it.**
Prompt Library use is associated with higher activation and retention across
this dataset by design, yet its adoption rate is lowest in Operations
(36.4%) and Retail Banking (37.6%) — the two units with the largest eligible
populations and the lowest activation rates — versus 61.6% in Technology.
*Metric:* `feature_adoption_rate(groupby='business_unit')`, filtered to
Prompt Library.

---

## Recommended Actions

| Segment | Recommended Action | Owner | Expected Measurement (2-4 weeks) |
|---|---|---|---|
| Retail Banking / Operations | Launch a manager-championed, role-specific refresher on Knowledge Search, Document Summarization, and Prompt Library, timed around existing team huddles to fit frontline schedules | **Enablement** | Activation rate +5 points and Prompt Library adoption +8 points in these two business units within 4 weeks |
| Risk and Compliance | Publish 3 additional approved-use-case examples and confirm manager-champion sign-off, to address the "Unsure what use cases are allowed" and "Privacy or compliance concern" barriers already reported | **Business Champion** | Combined share of those two barrier categories in Risk and Compliance feedback down 10 points within 3 weeks |
| Company-wide | Add a Prompt Library walkthrough to the standard onboarding flow, citing its association with higher activation/retention in this dataset (explicitly framed as an association, not a guarantee) | **Product** | Company-wide Prompt Library adoption rate +8 points within 4 weeks |

---

## Limitations

This memo is built entirely from **synthetic, randomly generated data** for
a fictional company and product. Every "association" reported above
(training ↔ activation, Prompt Library ↔ retention) was, in part, a pattern
deliberately designed into the data generator to make this project
analyzable — it is evidence about this one synthetic dataset, not a
validated finding about real GenAI rollouts, and no causal claim is made or
implied. "Estimated hours saved" is a modeled per-action assumption, not a
measured or audited productivity figure, and must not be cited as ROI. See
`docs/assumptions_and_limitations.md` for the complete integrity statement
and `docs/metric_dictionary.md` for every metric's exact definition and
caveats.
