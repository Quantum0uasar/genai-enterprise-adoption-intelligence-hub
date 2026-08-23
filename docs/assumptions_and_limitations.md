# Assumptions and Limitations

*Initial version — written alongside the Phase 1 synthetic data generator.
Will be extended as later phases (cleaning, metrics, Power BI, Excel) add
their own modeling choices.*

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
- This document will be expanded with cleaning-specific assumptions once
  `src/transform_data.py` (Phase 2) is built, and with metric-specific
  caveats once `docs/metric_dictionary.md` (Phase 4) is completed.
