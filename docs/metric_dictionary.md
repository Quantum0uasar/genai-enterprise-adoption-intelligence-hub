# Metric Dictionary

**Status: placeholder.** This document will be completed in the analysis
phase (Phase 4 of the implementation plan), once `src/analysis.py` and the
SQL query set (`sql/02_adoption_metrics.sql`) exist to compute and validate
these definitions against the cleaned data.

It will define, for each metric: numerator, denominator, timeframe, business
purpose, at least one caveat, and at least one worked interpretation example.
Planned metrics include: Eligible Users, Activated User / Activation Rate,
Weekly Active Users (WAU), Monthly Active Users (MAU, trailing 28 days),
Stickiness (WAU/MAU), Feature Adoption Rate, Time-to-Value, Retention (weekly
activation cohorts), Dormancy, Training Completion Rate, Estimated
Productivity Time Saved (modeled, not validated ROI), and Recommendation
Rate.

All metrics will be computed on the synthetic dataset described in
`data/synthetic_data_dictionary.md` and will carry the same integrity caveats
documented in `docs/assumptions_and_limitations.md`.
