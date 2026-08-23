# Qualitative User Research Plan

A follow-up research plan to investigate the dashboard/memo findings in
`docs/executive_weekly_readout.md` for the fictional Northstar Assist
rollout. **This plan and every example in it are entirely hypothetical** —
written to demonstrate how a real enablement team would follow up on
usage-analytics findings with qualitative research. No real interviews have
been conducted; no real personal information is used anywhere in this
document.

## Objective

Usage analytics (Phases 3-4 of this project) can show *that* Retail Banking
and Operations activate at lower rates and complete less training, and *that*
Prompt Library adoption lags in those units — but it cannot say *why*. This
research plan exists to answer the "why" behind three specific quantitative
findings, so recommended actions are based on understanding, not just
pattern-matching a dashboard.

## Target user segments (3)

1. **Low-activation, high-eligibility frontline staff** — Retail Banking and
   Operations employees who were granted access but did not activate (per
   `docs/metric_dictionary.md`'s definition), to understand real barriers to
   getting started.
2. **Risk and Compliance users who reported "unsure what's allowed" or
   "privacy concern" barriers** — to pressure-test whether published
   approved-use-case guidance is actually reaching and satisfying this group.
3. **Power users who use Prompt Library heavily** (across any business unit)
   — to understand what makes this feature valuable to them, and why it
   might not be discovered by others.

## Recruiting criteria

- Drawn from the **synthetic** `clean_users.csv` / `clean_usage_events.csv` /
  `clean_feedback.csv` population matching each segment's usage pattern
  (e.g. Segment 1: `business_unit` in {Retail Banking, Operations},
  `Is Activated` = False, `eligible_for_access_flag` = True).
- Target 6-8 participants per segment (18-24 total) — enough for thematic
  saturation in a qualitative study of this scope, not a statistically
  representative sample.
- Mix of tenure (new hire vs. 2+ years) and manager-champion status within
  each segment, to check whether findings hold across those splits.
- In a real deployment: recruit via an opt-in email through the business
  unit's regular communications channel, not a cold ask from the AI
  Enablement team, to reduce selection bias toward already-engaged users.

## 8 semi-structured interview questions

1. Walk me through the last time you opened (or almost opened) Northstar
   Assist. What were you trying to get done?
2. What, if anything, made it hard to get started with the tool early on?
3. Do you feel confident about what you're allowed to use it for in your
   role? What would make that clearer?
4. Tell me about a time the tool's output wasn't useful. What happened next?
5. Have you heard of [Prompt Library / a specific underused feature]? If
   yes, what's stopped you from using it more? If no, why do you think it
   hasn't come up?
6. How did your training experience match (or not match) what you actually
   need day-to-day?
7. If you could change one thing about how this tool was rolled out to your
   team, what would it be?
8. Is there anything about your day-to-day work that makes this tool a
   better or worse fit for you than for other roles you've seen use it?

## Consent and privacy considerations

- Participation is voluntary and opt-in; no manager is present during
  interviews to avoid influencing candor.
- Recordings (if any) and notes are anonymized before analysis — no
  participant name, employee ID, or verbatim quote identifiable to a
  specific person is stored in shared analysis artifacts.
- Participants are told upfront that findings will be aggregated into
  themes for enablement/product decisions, not used for individual
  performance review.
- Data retention and deletion follow the organization's standard research-
  data policy (in a fictional scenario, this project does not define one —
  a real implementation would cite the actual policy here).
- No real personal information is used in this document or any example
  output from it.

## Coding framework for feedback themes

A simple two-axis framework, applied to interview notes and, in parallel, to
the existing `barrier_category` free-text feedback in `clean_feedback.csv`:

| Axis | Categories |
|---|---|
| **Barrier type** | Time/workload · Clarity of allowed use · Output quality/trust · Discoverability · Training fit · Technical/performance |
| **Barrier depth** | Surface (easily fixed with a comms/UI change) · Structural (requires a process, policy, or role-design change) |

Each coded excerpt gets one barrier type and one depth rating. Themes that
recur across ≥ 3 participants in a segment are treated as segment-level
findings; anything mentioned by 1-2 participants is noted as a possible lead
for the next round, not a finding.

## How qualitative findings complement — not replace — usage analytics

Usage analytics (this project's SQL/Python/Power BI/Excel deliverables)
answer **what** is happening at scale and **how big** a pattern is (e.g.
"Retail Banking's activation rate is 71.9%, the second-lowest in the
company"). Qualitative research answers **why** and **what to actually
change** — the mechanism behind the number. Neither replaces the other:
a barrier category in `feedback.csv` (e.g. "No time to learn") tells you
*that* time is cited as a barrier by a certain share of a business unit;
an interview can reveal *which part* of the workflow makes time the binding
constraint, which is what turns a barrier count into a specific,
actionable fix.

## Example: how a user quote could change a recommended action

**Before qualitative input:** the memo's Recommended Action for Retail
Banking (informed only by usage data) was "launch a manager-championed
refresher on Knowledge Search, Document Summarization, and Prompt Library."

**Hypothetical interview finding (illustrative, not a real quote):** several
Segment 1 participants describe not lacking time in general, but
specifically lacking a natural moment in their **existing** workflow to open
a separate tool mid-client-interaction — the barrier isn't "no time to
learn," it's "no obvious point in my workflow to use this."

**Revised action:** instead of (or in addition to) a training refresher, the
recommendation shifts toward embedding Northstar Assist directly into the
tool Retail Banking staff already have open during client interactions
(e.g. the Outlook or Teams plugin surfaced in `usage_events.platform`),
reducing the number of steps to first use. This is a materially different,
more specific fix than "more training" — exactly the kind of change
qualitative research is meant to surface.
