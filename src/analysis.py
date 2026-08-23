"""
GenAI Enterprise Adoption Intelligence Hub
Reusable metric functions for the fictional Northstar Financial Group /
Northstar Assist synthetic dataset.

Operates ONLY on the cleaned data in data/processed/ (produced by
src/transform_data.py) — never on data/raw/. Every function here mirrors a
metric definition in docs/metric_dictionary.md; the two should be read
together.

SYNTHETIC DATA ONLY. "Estimated time saved" is a modeled assumption baked
into the data generator, never a measured or validated ROI figure. Nothing
here tests or claims causation — associations (e.g. training vs. activation)
are reported as associations only. See docs/assumptions_and_limitations.md.

Intended usage: `import src.analysis as ga` from a notebook or script run
from the repository root, or `from src import analysis as ga`.
"""

import os

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")

MEANINGFUL_EVENT_TYPES = ["prompt_submitted", "output_generated", "feature_completed", "output_exported"]
VALUE_EVENT_TYPES = ["feature_completed", "output_exported", "output_generated"]

TIME_SAVED_DISCLAIMER = (
    "estimated_minutes_saved / estimated_hours_saved are MODELED ASSUMPTIONS "
    "built into the synthetic data generator, not measured or validated ROI."
)

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data(processed_dir=PROCESSED_DIR):
    """Loads all six clean_*.csv files with dates parsed. Returns a dict."""
    users = pd.read_csv(
        os.path.join(processed_dir, "clean_users.csv"),
        parse_dates=["hire_date", "assigned_access_date", "training_assigned_date", "training_completed_date"],
    )
    events = pd.read_csv(
        os.path.join(processed_dir, "clean_usage_events.csv"),
        parse_dates=["event_timestamp"],
    )
    feedback = pd.read_csv(
        os.path.join(processed_dir, "clean_feedback.csv"),
        parse_dates=["feedback_timestamp"],
    )
    training = pd.read_csv(
        os.path.join(processed_dir, "clean_training_sessions.csv"),
        parse_dates=["session_date"],
    )
    features = pd.read_csv(
        os.path.join(processed_dir, "clean_feature_catalog.csv"),
        parse_dates=["release_date"],
    )
    calendar = pd.read_csv(
        os.path.join(processed_dir, "clean_calendar.csv"),
        parse_dates=["date", "week_start_date"],
    )
    return {
        "users": users, "events": events, "feedback": feedback,
        "training": training, "features": features, "calendar": calendar,
    }


# ---------------------------------------------------------------------------
# Eligibility / activation
# ---------------------------------------------------------------------------

def get_eligible_users(users):
    """Eligible users: assigned access AND eligible_for_access_flag == True."""
    return users[users["eligible_for_access_flag"].fillna(False) & users["assigned_access_date"].notna()].copy()


def get_meaningful_events(events):
    return events[events["event_type"].isin(MEANINGFUL_EVENT_TYPES)].copy()


def compute_activation(users, events):
    """
    Activated user = eligible user who (completed training OR used Prompt
    Library at least once) AND has >= 3 meaningful actions within 14 days of
    assigned_access_date.

    Returns eligible_users with an added boolean 'activated' column.
    Caveat: this is a designed, association-based definition (see
    docs/metric_dictionary.md) — not a causal or externally validated model
    of "true" activation.
    """
    eligible = get_eligible_users(users)
    meaningful = get_meaningful_events(events)

    merged = meaningful.merge(eligible[["user_id", "assigned_access_date"]], on="user_id", how="inner")
    within_14d = merged[merged["event_timestamp"] <= merged["assigned_access_date"] + pd.Timedelta(days=14)]
    action_counts = within_14d.groupby("user_id").size().rename("meaningful_action_count_14d")

    prompt_library_users = set(events.loc[events["feature_name"] == "Prompt Library", "user_id"].unique())

    result = eligible.copy()
    result = result.merge(action_counts, on="user_id", how="left")
    result["meaningful_action_count_14d"] = result["meaningful_action_count_14d"].fillna(0)
    result["used_prompt_library"] = result["user_id"].isin(prompt_library_users)
    result["completed_training"] = result["training_completed_date"].notna()
    result["activated"] = (
        (result["completed_training"] | result["used_prompt_library"])
        & (result["meaningful_action_count_14d"] >= 3)
    )
    return result


def activation_rate(users, events, groupby=None):
    """Returns activation rate (%) overall or grouped by a users.csv column
    (e.g. 'business_unit', 'rollout_wave')."""
    activation = compute_activation(users, events)
    if groupby is None:
        return pd.Series({
            "eligible_users": len(activation),
            "activated_users": int(activation["activated"].sum()),
            "activation_rate_pct": round(100 * activation["activated"].mean(), 1),
        })
    grouped = activation.groupby(groupby).agg(
        eligible_users=("user_id", "count"),
        activated_users=("activated", "sum"),
    )
    grouped["activation_rate_pct"] = round(100 * grouped["activated_users"] / grouped["eligible_users"], 1)
    return grouped.reset_index()


# ---------------------------------------------------------------------------
# Active users / stickiness
# ---------------------------------------------------------------------------

def weekly_active_users(events, calendar, users=None, groupby=None):
    """
    WAU: distinct users with >=1 meaningful action per calendar week.
    Pass `users` and `groupby` (a column on the users table, e.g.
    'business_unit') to break WAU out by segment.
    """
    meaningful = get_meaningful_events(events)
    cal = calendar[["date", "week_number", "week_start_date"]].rename(columns={"date": "event_date"})
    meaningful = meaningful.copy()
    meaningful["event_date"] = meaningful["event_timestamp"].dt.normalize()
    merged = meaningful.merge(cal, on="event_date", how="left")

    group_cols = ["week_number", "week_start_date"] + ([groupby] if groupby else [])
    if groupby:
        if users is None:
            raise ValueError("weekly_active_users(groupby=...) requires the `users` DataFrame.")
        merged = merged.merge(users[["user_id", groupby]], on="user_id", how="left")
    wau = merged.groupby(group_cols)["user_id"].nunique().rename("weekly_active_users").reset_index()
    return wau.sort_values(group_cols)


def mau_28d(events, as_of_date=None):
    """MAU: distinct users with >=1 meaningful action in the trailing 28 days."""
    meaningful = get_meaningful_events(events)
    if as_of_date is None:
        as_of_date = meaningful["event_timestamp"].max()
    window_start = as_of_date - pd.Timedelta(days=28)
    window = meaningful[(meaningful["event_timestamp"] > window_start) & (meaningful["event_timestamp"] <= as_of_date)]
    return window["user_id"].nunique()


def stickiness(events, calendar, week_number, as_of_date=None):
    """
    Stickiness = WAU (for a given week) / MAU (trailing 28 days as of that
    week's end). Caveat: a proxy for engagement DEPTH, not a complete measure
    of value delivered — a small, highly repeat-engaged group can produce the
    same ratio as a larger, lightly engaged one.
    """
    wau_table = weekly_active_users(events, calendar)
    wau_row = wau_table[wau_table["week_number"] == week_number]
    if wau_row.empty:
        return np.nan
    wau = wau_row["weekly_active_users"].iloc[0]
    week_end = calendar.loc[calendar["week_number"] == week_number, "date"].max()
    mau = mau_28d(events, as_of_date=as_of_date or week_end)
    return round(100 * wau / mau, 1) if mau else np.nan


# ---------------------------------------------------------------------------
# Feature adoption
# ---------------------------------------------------------------------------

def feature_adoption_rate(users, events, groupby=None):
    """
    Feature adoption rate = distinct users who completed/exported a feature /
    distinct eligible users (in the same group cut, if any).
    Caveat: denominator is ALL eligible users, not a feature-specific target
    persona — see docs/metric_dictionary.md.
    """
    eligible = get_eligible_users(users)
    completions = events[events["event_type"].isin(["feature_completed", "output_exported"])]
    completions = completions.dropna(subset=["feature_name"])

    group_cols = (["feature_name"] if not groupby else [groupby, "feature_name"])
    eligible_cols = ["user_id"] + ([groupby] if groupby else [])

    comp_users = completions.merge(eligible[eligible_cols], on="user_id", how="inner")
    adopted = comp_users.groupby(group_cols)["user_id"].nunique().rename("adopted_users")

    denom = eligible.groupby(groupby)["user_id"].nunique() if groupby else pd.Series({"_all": eligible["user_id"].nunique()})

    rows = []
    features = sorted(events["feature_name"].dropna().unique())
    groups = eligible[groupby].dropna().unique() if groupby else ["_all"]
    for g in groups:
        denom_n = denom.get(g, 0) if groupby else denom["_all"]
        for feat in features:
            key = (g, feat) if groupby else feat
            adopted_n = adopted.get(key, 0)
            rows.append({
                (groupby or "segment"): g, "feature_name": feat,
                "eligible_users": denom_n, "adopted_users": adopted_n,
                "feature_adoption_rate_pct": round(100 * adopted_n / denom_n, 1) if denom_n else np.nan,
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Time-to-value
# ---------------------------------------------------------------------------

def time_to_value(users, events):
    """
    Per-user hours from assigned_access_date to first successful completion/
    export/core-feature action (VALUE_EVENT_TYPES with successful_completion_flag).
    Returns one row per user with a first-value event.
    """
    eligible = get_eligible_users(users)
    successful_value_events = events[
        events["event_type"].isin(VALUE_EVENT_TYPES) & events["successful_completion_flag"].fillna(False)
    ]
    first_value = successful_value_events.groupby("user_id")["event_timestamp"].min().rename("first_value_ts")

    merged = eligible.merge(first_value, on="user_id", how="inner")
    merged = merged[merged["first_value_ts"] >= merged["assigned_access_date"]]
    merged["hours_to_value"] = (
        merged["first_value_ts"] - merged["assigned_access_date"]
    ).dt.total_seconds() / 3600.0
    return merged[["user_id", "business_unit", "role", "hours_to_value"]]


def median_time_to_value(users, events, groupby="business_unit"):
    ttv = time_to_value(users, events)
    result = ttv.groupby(groupby)["hours_to_value"].agg(
        users_with_first_value="count", median_hours_to_value="median"
    ).round(1).reset_index()
    return result.sort_values("median_hours_to_value")


# ---------------------------------------------------------------------------
# Retention / dormancy
# ---------------------------------------------------------------------------

def retention_cohorts(events, calendar, max_weeks_out=8):
    """
    Cohort = week of a user's first meaningful action. Retention in week N =
    % of the cohort active in (cohort_week + N). Note: this cohort definition
    uses "first meaningful action" as an activation-week proxy, which is
    simpler than (and does not require) the full formal activation
    definition, so it can be computed purely from event dates.
    """
    meaningful = get_meaningful_events(events).copy()
    cal = calendar[["date", "week_number"]].rename(columns={"date": "event_date"})
    meaningful["event_date"] = meaningful["event_timestamp"].dt.normalize()
    merged = meaningful.merge(cal, on="event_date", how="left")

    cohort_week = merged.groupby("user_id")["week_number"].min().rename("cohort_week")
    merged = merged.merge(cohort_week, on="user_id", suffixes=("", "_cohort"))
    merged["weeks_since_activation"] = merged["week_number"] - merged["cohort_week"]
    merged = merged[merged["weeks_since_activation"].between(0, max_weeks_out)]

    cohort_sizes = cohort_week.value_counts().rename("cohort_users")

    active = merged.groupby(["cohort_week", "weeks_since_activation"])["user_id"].nunique().rename("active_users")
    result = active.reset_index()
    result = result.merge(cohort_sizes.rename_axis("cohort_week").reset_index(), on="cohort_week")
    result["retention_rate_pct"] = round(100 * result["active_users"] / result["cohort_users"], 1)
    return result.sort_values(["cohort_week", "weeks_since_activation"])


def dormant_users(users, events, as_of_date=None, groupby="business_unit"):
    """Activated users with no meaningful action in the trailing 28 days."""
    activation = compute_activation(users, events)
    activated = activation[activation["activated"]]

    meaningful = get_meaningful_events(events)
    if as_of_date is None:
        as_of_date = meaningful["event_timestamp"].max()
    window_start = as_of_date - pd.Timedelta(days=28)
    recently_active = set(
        meaningful.loc[
            (meaningful["event_timestamp"] > window_start) & (meaningful["event_timestamp"] <= as_of_date), "user_id"
        ].unique()
    )
    activated = activated.copy()
    activated["is_dormant"] = ~activated["user_id"].isin(recently_active)

    result = activated.groupby(groupby).agg(
        activated_users=("user_id", "count"), dormant_users=("is_dormant", "sum")
    ).reset_index()
    result["dormancy_rate_pct"] = round(100 * result["dormant_users"] / result["activated_users"], 1)
    return result.sort_values("dormancy_rate_pct", ascending=False)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def training_completion_rate(users, groupby=None):
    df = users.copy()
    df["training_assigned"] = df["training_assigned_date"].notna()
    df["training_completed"] = df["training_completed_date"].notna()
    assigned = df[df["training_assigned"]]

    if groupby is None:
        return pd.Series({
            "users_assigned": len(assigned),
            "users_completed": int(assigned["training_completed"].sum()),
            "training_completion_rate_pct": round(100 * assigned["training_completed"].mean(), 1),
        })
    grouped = assigned.groupby(groupby).agg(
        users_assigned=("user_id", "count"), users_completed=("training_completed", "sum")
    )
    grouped["training_completion_rate_pct"] = round(100 * grouped["users_completed"] / grouped["users_assigned"], 1)
    return grouped.reset_index()


def training_vs_activation(users, events):
    """
    Activation rate split by training completion. ASSOCIATION ONLY: training
    completion is not randomly assigned in this dataset, so this comparison
    does not establish that training causes activation.
    """
    activation = compute_activation(users, events)
    activation["training_status"] = np.where(
        activation["completed_training"], "Completed Training", "Did Not Complete Training"
    )
    grouped = activation.groupby("training_status").agg(
        eligible_users=("user_id", "count"), activated_users=("activated", "sum")
    ).reset_index()
    grouped["activation_rate_pct"] = round(100 * grouped["activated_users"] / grouped["eligible_users"], 1)
    return grouped


# ---------------------------------------------------------------------------
# Modeled time saved
# ---------------------------------------------------------------------------

def estimated_time_saved(events, groupby="feature_name"):
    """
    Sums estimated_minutes_saved for successful completion/export/generation
    events. DISCLAIMER: a modeled assumption from the synthetic data
    generator, never a measured or validated ROI figure.
    """
    value_events = events[
        events["event_type"].isin(VALUE_EVENT_TYPES)
        & events["successful_completion_flag"].fillna(False)
        & events["estimated_minutes_saved"].notna()
    ]
    grouped = value_events.groupby(groupby)["estimated_minutes_saved"].agg(
        successful_actions_with_estimate="count", total_estimated_minutes_saved="sum",
        avg_estimated_minutes_saved_per_action="mean",
    ).round(1)
    grouped["total_estimated_hours_saved"] = round(grouped["total_estimated_minutes_saved"] / 60.0, 1)
    grouped["disclaimer"] = TIME_SAVED_DISCLAIMER
    return grouped.reset_index().sort_values("total_estimated_minutes_saved", ascending=False)


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

def recommendation_rate(feedback, groupby=None):
    df = feedback.dropna(subset=["would_recommend_flag"])
    if groupby is None:
        return pd.Series({
            "feedback_submissions": len(df),
            "recommendation_rate_pct": round(100 * df["would_recommend_flag"].mean(), 1),
        })
    grouped = df.groupby(groupby).agg(
        feedback_submissions=("feedback_id", "count"), recommend_count=("would_recommend_flag", "sum")
    )
    grouped["recommendation_rate_pct"] = round(100 * grouped["recommend_count"] / grouped["feedback_submissions"], 1)
    return grouped.reset_index()


def barrier_ranking(feedback, users, groupby="business_unit"):
    """Ranks reported barriers (excluding 'No barrier reported') within each group."""
    merged = feedback.merge(users[["user_id", groupby]], on="user_id", how="left")
    merged = merged[merged["barrier_category"].notna() & (merged["barrier_category"] != "No barrier reported")]
    counts = merged.groupby([groupby, "barrier_category"]).size().rename("mentions").reset_index()
    counts["barrier_rank"] = counts.groupby(groupby)["mentions"].rank(method="min", ascending=False).astype(int)
    return counts.sort_values([groupby, "barrier_rank"])


if __name__ == "__main__":
    data = load_data()
    print("Loaded processed synthetic data:")
    for name, df in data.items():
        print(f"  {name}: {len(df):,} rows")

    print("\nOverall activation rate (synthetic):")
    print(activation_rate(data["users"], data["events"]))

    print("\nOverall training completion rate (synthetic):")
    print(training_completion_rate(data["users"]))

    print("\nOverall recommendation rate (synthetic):")
    print(recommendation_rate(data["feedback"]))

    print(f"\nReminder: {TIME_SAVED_DISCLAIMER}")
