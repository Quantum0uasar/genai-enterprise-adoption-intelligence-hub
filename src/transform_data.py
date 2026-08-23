"""
GenAI Enterprise Adoption Intelligence Hub
Data cleaning / transformation pipeline.

Reads the raw synthetic CSVs in data/raw/ (which intentionally contain
duplicates, missing values, inconsistent labels, and a small number of
invalid records — see data/synthetic_data_dictionary.md), applies documented
cleaning rules, and writes clean CSVs to data/processed/ plus a
data_quality_issues.csv / .md log of exactly what was found and how it was
handled.

Design principle: every corrective action taken here is logged with an
affected-record count and a resolution. Nothing is silently dropped, and no
missing value is invented — legitimate missingness (e.g. a user who never
completed training) is retained as null and documented, not manufactured.

SYNTHETIC DATA ONLY. See data/synthetic_data_dictionary.md and
docs/assumptions_and_limitations.md for the integrity statement.

Run with:
    python src/transform_data.py
"""

import os
from datetime import datetime

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")

# ---------------------------------------------------------------------------
# Canonical reference values (derived from the known business scenario, not
# from the generator internals — a real pipeline would source these from a
# reference/lookup table).
# ---------------------------------------------------------------------------
CANONICAL_BUSINESS_UNITS = [
    "Retail Banking", "Commercial Banking", "Capital Markets", "Wealth Management",
    "Operations", "Technology", "Risk and Compliance", "Corporate Functions",
]
BUSINESS_UNIT_LABEL_MAP = {
    "retail banking": "Retail Banking",
    "retail  banking": "Retail Banking",
    "risk & compliance": "Risk and Compliance",
    "risk and compliance": "Risk and Compliance",
    "tech": "Technology",
    "technology": "Technology",
}

CANONICAL_FEATURES = [
    "Chat and Research", "Knowledge Search", "Document Summarization", "Meeting Notes",
    "Prompt Library", "Drafting Assistant", "Data Analysis", "Code Assistant",
]
FEATURE_LABEL_MAP = {
    "chat and research": "Chat and Research",
    "chat & research": "Chat and Research",
    "doc summarization": "Document Summarization",
    "document summarization": "Document Summarization",
    "knowledge search": "Knowledge Search",
}

# Log accumulator: list of dicts -> becomes data_quality_issues.csv
ISSUE_LOG = []


def log_issue(issue_type, affected_record_count, resolution, status):
    ISSUE_LOG.append({
        "issue_type": issue_type,
        "affected_record_count": int(affected_record_count),
        "resolution": resolution,
        "status": status,
    })


def standardize_columns(df):
    df = df.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


def normalize_label(series, canonical_values, label_map):
    """Lowercase/strip, map known variants to canonical, leave unmatched as-is
    (flagged separately by the caller if they don't land in canonical_values)."""
    def _norm(v):
        if pd.isna(v) or str(v).strip() == "":
            return v
        key = str(v).strip().lower()
        if key in label_map:
            return label_map[key]
        for canon in canonical_values:
            if key == canon.lower():
                return canon
        return str(v).strip()
    return series.apply(_norm)


def to_bool(series):
    def _b(v):
        if pd.isna(v):
            return pd.NA
        s = str(v).strip().lower()
        if s in ("true", "1", "yes"):
            return True
        if s in ("false", "0", "no"):
            return False
        return pd.NA
    return series.apply(_b)


def parse_dates_safely(series, fmt="%Y-%m-%d"):
    """Returns (parsed_series, n_invalid) where invalid/blank become NaT."""
    parsed = pd.to_datetime(series, format=fmt, errors="coerce")
    non_blank_input = series.notna() & (series.astype(str).str.strip() != "")
    n_invalid = int((non_blank_input & parsed.isna()).sum())
    return parsed, n_invalid


def parse_timestamps_safely(series):
    parsed = pd.to_datetime(series, format="%Y-%m-%d %H:%M:%S", errors="coerce")
    non_blank_input = series.notna() & (series.astype(str).str.strip() != "")
    n_invalid = int((non_blank_input & parsed.isna()).sum())
    return parsed, n_invalid


# ---------------------------------------------------------------------------
# 1. Users
# ---------------------------------------------------------------------------

def clean_users():
    df = standardize_columns(pd.read_csv(os.path.join(RAW_DIR, "users.csv"), dtype=str))
    n_raw = len(df)

    n_dupe_rows = n_raw - df["user_id"].nunique()
    df = df.drop_duplicates(subset="user_id", keep="first").reset_index(drop=True)
    if n_dupe_rows > 0:
        log_issue(
            "Duplicate user_id rows in users.csv", n_dupe_rows,
            "Removed exact-duplicate rows, keeping the first occurrence of each user_id.",
            "Resolved",
        )

    n_bu_variants = int((~df["business_unit"].isin(CANONICAL_BUSINESS_UNITS)).sum())
    df["business_unit"] = normalize_label(df["business_unit"], CANONICAL_BUSINESS_UNITS, BUSINESS_UNIT_LABEL_MAP)
    if n_bu_variants > 0:
        log_issue(
            "Inconsistent business_unit label variants in users.csv", n_bu_variants,
            "Normalized case/whitespace/abbreviation variants (e.g. 'RETAIL BANKING', "
            "'TECH', 'Risk & Compliance') to the 8 canonical business unit names.",
            "Resolved",
        )
    n_unmapped_bu = int((~df["business_unit"].isin(CANONICAL_BUSINESS_UNITS)).sum())
    if n_unmapped_bu > 0:
        log_issue(
            "business_unit values not in canonical list after normalization", n_unmapped_bu,
            "Retained as-is for manual review; not dropped or guessed.",
            "Accepted",
        )

    df["role"] = df["role"].str.strip()
    df["region"] = df["region"].str.strip()
    df["manager_level"] = df["manager_level"].str.strip()
    df["training_format"] = df["training_format"].str.strip()

    df["hire_date"], n_bad_hire = parse_dates_safely(df["hire_date"])
    df["assigned_access_date"], n_bad_access = parse_dates_safely(df["assigned_access_date"])
    df["training_assigned_date"], n_bad_train_assigned = parse_dates_safely(df["training_assigned_date"])
    df["training_completed_date"], n_bad_train_completed = parse_dates_safely(df["training_completed_date"])
    for label, n in [
        ("hire_date", n_bad_hire), ("assigned_access_date", n_bad_access),
        ("training_assigned_date", n_bad_train_assigned), ("training_completed_date", n_bad_train_completed),
    ]:
        if n > 0:
            log_issue(
                f"Unparseable non-blank {label} values in users.csv", n,
                "Coerced to null (NaT); could not be safely interpreted as a date.",
                "Resolved",
            )

    n_missing_access = int(df["assigned_access_date"].isna().sum())
    if n_missing_access > 0:
        log_issue(
            "Missing assigned_access_date in users.csv", n_missing_access,
            "Retained as null. These are predominantly users flagged "
            "eligible_for_access_flag=False who never received an access date; "
            "such users are excluded from any usage-dependent metric downstream.",
            "Accepted",
        )

    df["manager_champion_flag"] = to_bool(df["manager_champion_flag"])
    df["eligible_for_access_flag"] = to_bool(df["eligible_for_access_flag"])
    n_missing_champion = int(df["manager_champion_flag"].isna().sum())
    if n_missing_champion > 0:
        log_issue(
            "Missing manager_champion_flag in users.csv", n_missing_champion,
            "Retained as null (unknown) rather than assumed False; excluded from "
            "champion-specific breakdowns but included in all other metrics.",
            "Accepted",
        )

    df["rollout_wave"] = pd.to_numeric(df["rollout_wave"], errors="coerce").astype("Int64")

    # Sanity check: training_completed_date should not precede training_assigned_date.
    bad_order = df["training_completed_date"].notna() & df["training_assigned_date"].notna() & (
        df["training_completed_date"] < df["training_assigned_date"]
    )
    n_bad_order = int(bad_order.sum())
    if n_bad_order > 0:
        df.loc[bad_order, "training_completed_date"] = pd.NaT
        log_issue(
            "training_completed_date earlier than training_assigned_date in users.csv", n_bad_order,
            "Nulled the implausible completion date; assignment date retained.",
            "Resolved",
        )
    else:
        log_issue(
            "training_completed_date earlier than training_assigned_date in users.csv", 0,
            "Validated — no records found violating this business rule.",
            "Validated (no issue found)",
        )

    return df


# ---------------------------------------------------------------------------
# 2. Usage events
# ---------------------------------------------------------------------------

def clean_usage_events(clean_users_df):
    df = standardize_columns(pd.read_csv(os.path.join(RAW_DIR, "usage_events.csv"), dtype=str))
    n_raw = len(df)

    n_dupe_rows = n_raw - df["event_id"].nunique()
    df = df.drop_duplicates(subset="event_id", keep="first").reset_index(drop=True)
    if n_dupe_rows > 0:
        log_issue(
            "Duplicate event_id rows in usage_events.csv", n_dupe_rows,
            "Removed exact-duplicate rows (simulated at-least-once delivery), keeping "
            "the first occurrence of each event_id.",
            "Resolved",
        )

    df["event_timestamp"], n_bad_ts = parse_timestamps_safely(df["event_timestamp"])
    n_before_drop = len(df)
    df = df[df["event_timestamp"].notna()].reset_index(drop=True)
    n_quarantined_ts = n_before_drop - len(df)
    if n_quarantined_ts > 0:
        log_issue(
            "Invalid/unparseable event_timestamp in usage_events.csv", n_quarantined_ts,
            "Quarantined (removed from clean output) — timestamp is required to place "
            "an event in a rollout week and could not be safely recovered.",
            "Resolved",
        )

    n_feature_variants = int((~df["feature_name"].fillna("").isin(CANONICAL_FEATURES + [""])).sum())
    df["feature_name"] = normalize_label(df["feature_name"], CANONICAL_FEATURES, FEATURE_LABEL_MAP)
    df["feature_name"] = df["feature_name"].replace("", np.nan)
    if n_feature_variants > 0:
        log_issue(
            "Inconsistent feature_name label variants in usage_events.csv", n_feature_variants,
            "Normalized case/whitespace/abbreviation variants (e.g. 'Doc Summarization', "
            "'chat and research') to the 8 canonical feature names.",
            "Resolved",
        )

    n_missing_feature = int(df["feature_name"].isna().sum())
    if n_missing_feature > 0:
        log_issue(
            "Missing feature_name in usage_events.csv", n_missing_feature,
            "Retained as null; excluded from feature-level adoption metrics but "
            "included in overall activity/engagement counts.",
            "Accepted",
        )

    for col in ["output_exported_flag", "successful_completion_flag", "error_flag"]:
        df[col] = to_bool(df[col])

    df["session_duration_seconds"] = pd.to_numeric(df["session_duration_seconds"], errors="coerce")
    df["estimated_minutes_saved"] = pd.to_numeric(df["estimated_minutes_saved"], errors="coerce")

    n_neg_duration = int((df["session_duration_seconds"] < 0).sum())
    if n_neg_duration > 0:
        df.loc[df["session_duration_seconds"] < 0, "session_duration_seconds"] = np.nan
        log_issue(
            "Negative session_duration_seconds in usage_events.csv", n_neg_duration,
            "Nulled the impossible negative value. The event record itself is kept "
            "(event_type, feature_name, etc. remain usable) but its duration is "
            "excluded from duration-based aggregations.",
            "Resolved",
        )

    n_neg_minutes = int((df["estimated_minutes_saved"] < 0).sum())
    if n_neg_minutes > 0:
        df.loc[df["estimated_minutes_saved"] < 0, "estimated_minutes_saved"] = np.nan
        log_issue(
            "Negative estimated_minutes_saved in usage_events.csv", n_neg_minutes,
            "Nulled the impossible negative value; excluded from the modeled "
            "time-saved aggregation. This field is a modeled estimate in all cases, "
            "never a measured value.",
            "Resolved",
        )

    # Validate events occur on/after the user's assigned_access_date.
    access_lookup = clean_users_df.drop_duplicates(subset="user_id").set_index("user_id")["assigned_access_date"]
    df["_access_date"] = df["user_id"].map(access_lookup)
    has_access = df["_access_date"].notna()
    pre_access = has_access & (df["event_timestamp"].dt.normalize() < df["_access_date"])
    n_pre_access = int(pre_access.sum())
    if n_pre_access > 0:
        log_issue(
            "usage_events records timestamped before the user's assigned_access_date", n_pre_access,
            "Removed — violates the business rule that usage can only occur after "
            "access is granted; timestamp or access-date data for these rows cannot "
            "be trusted.",
            "Resolved",
        )
        df = df[~pre_access].reset_index(drop=True)

    # Events for users with no access date on record at all (orphaned / access
    # data missing) cannot be validated against the business rule — flag, don't drop.
    n_no_access_on_file = int(df["_access_date"].isna().sum())
    if n_no_access_on_file > 0:
        log_issue(
            "usage_events records for users with no assigned_access_date on file", n_no_access_on_file,
            "Retained — cannot validate against the access-date business rule "
            "because the source access date is missing (see the corresponding "
            "users.csv missing-value issue); flagged for awareness only.",
            "Accepted",
        )

    df = df.drop(columns=["_access_date"])

    # Validate events fall within the known 24-week rollout window (per
    # calendar.csv). Any event dated after the rollout's last calendar day
    # cannot be placed in dim_date and indicates a timestamp problem upstream.
    calendar_raw = pd.read_csv(os.path.join(RAW_DIR, "calendar.csv"), dtype=str)
    rollout_end = pd.to_datetime(calendar_raw["date"]).max()
    beyond_rollout = df["event_timestamp"].dt.normalize() > rollout_end
    n_beyond_rollout = int(beyond_rollout.sum())
    if n_beyond_rollout > 0:
        log_issue(
            f"usage_events records timestamped after the rollout end date ({rollout_end.date()})",
            n_beyond_rollout,
            "Removed — falls outside the 24-week rollout window represented in "
            "calendar.csv, so the event cannot be assigned a valid date-dimension key.",
            "Resolved",
        )
        df = df[~beyond_rollout].reset_index(drop=True)
    else:
        log_issue(
            "usage_events records timestamped after the rollout end date", 0,
            "Validated — no records found beyond the rollout window.",
            "Validated (no issue found)",
        )

    df["platform"] = df["platform"].str.strip()
    df["event_type"] = df["event_type"].str.strip()

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 3. Feedback
# ---------------------------------------------------------------------------

def clean_feedback():
    df = standardize_columns(pd.read_csv(os.path.join(RAW_DIR, "feedback.csv"), dtype=str))
    n_raw = len(df)

    n_dupe_rows = n_raw - df["feedback_id"].nunique()
    df = df.drop_duplicates(subset="feedback_id", keep="first").reset_index(drop=True)
    if n_dupe_rows > 0:
        log_issue(
            "Duplicate feedback_id rows in feedback.csv", n_dupe_rows,
            "Removed exact-duplicate rows, keeping the first occurrence of each feedback_id.",
            "Resolved",
        )

    df["feedback_timestamp"], n_bad_ts = parse_timestamps_safely(df["feedback_timestamp"])
    n_before = len(df)
    df = df[df["feedback_timestamp"].notna()].reset_index(drop=True)
    n_quarantined_ts = n_before - len(df)
    if n_quarantined_ts > 0:
        log_issue(
            "Invalid/unparseable feedback_timestamp in feedback.csv", n_quarantined_ts,
            "Quarantined (removed from clean output) — timestamp could not be parsed.",
            "Resolved",
        )
    else:
        log_issue(
            "Invalid/unparseable feedback_timestamp in feedback.csv", 0,
            "Validated — all feedback timestamps parsed successfully.",
            "Validated (no issue found)",
        )

    df["rating_1_to_5"] = pd.to_numeric(df["rating_1_to_5"], errors="coerce")
    invalid_rating = df["rating_1_to_5"].notna() & (~df["rating_1_to_5"].between(1, 5))
    n_invalid_rating = int(invalid_rating.sum())
    if n_invalid_rating > 0:
        df.loc[invalid_rating, "rating_1_to_5"] = np.nan
        log_issue(
            "Out-of-range rating_1_to_5 in feedback.csv", n_invalid_rating,
            "Nulled ratings outside the valid 1-5 scale; sentiment_label, "
            "barrier_category, and free_text_feedback for these rows are retained "
            "since they remain informative.",
            "Resolved",
        )

    n_feature_variants = int((~df["feature_name"].fillna("").isin(CANONICAL_FEATURES + [""])).sum())
    df["feature_name"] = normalize_label(df["feature_name"], CANONICAL_FEATURES, FEATURE_LABEL_MAP)
    df["feature_name"] = df["feature_name"].replace("", np.nan)
    if n_feature_variants > 0:
        log_issue(
            "Inconsistent feature_name label variants in feedback.csv", n_feature_variants,
            "Normalized to canonical feature names.",
            "Resolved",
        )

    n_missing_feature = int(df["feature_name"].isna().sum())
    if n_missing_feature > 0:
        log_issue(
            "Missing feature_name in feedback.csv", n_missing_feature,
            "Retained as null — this is expected for general feedback not tied to "
            "a specific feature; excluded from feature-level satisfaction cuts only.",
            "Accepted",
        )

    n_missing_text = int((df["free_text_feedback"].isna() | (df["free_text_feedback"].str.strip() == "")).sum())
    df["free_text_feedback"] = df["free_text_feedback"].replace("", np.nan)
    if n_missing_text > 0:
        log_issue(
            "Missing free_text_feedback in feedback.csv", n_missing_text,
            "Retained as null — the user submitted a rating/barrier without free text; "
            "not fabricated.",
            "Accepted",
        )

    df["would_recommend_flag"] = to_bool(df["would_recommend_flag"])
    df["sentiment_label"] = df["sentiment_label"].str.strip()
    df["barrier_category"] = df["barrier_category"].str.strip()

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 4. Training sessions / feature catalog / calendar (lighter validation only)
# ---------------------------------------------------------------------------

def clean_training_sessions():
    df = standardize_columns(pd.read_csv(os.path.join(RAW_DIR, "training_sessions.csv"), dtype=str))
    df["session_date"], n_bad = parse_dates_safely(df["session_date"])
    for col in ["registered_count", "attended_count", "completion_count"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    df["business_unit"] = normalize_label(df["business_unit"], CANONICAL_BUSINESS_UNITS, BUSINESS_UNIT_LABEL_MAP)

    bad_attend = df["attended_count"] > df["registered_count"]
    bad_complete = df["completion_count"] > df["attended_count"]
    n_bad = int(bad_attend.sum() + bad_complete.sum())
    if n_bad > 0:
        log_issue(
            "training_sessions.csv rows with attended/completed exceeding registered/attended", n_bad,
            "Flagged for manual review; values retained as-is (not fabricated a fix).",
            "Accepted",
        )
    else:
        log_issue(
            "training_sessions.csv attendance/completion logical consistency", 0,
            "Validated — attended_count <= registered_count and completion_count <= "
            "attended_count hold for all rows.",
            "Validated (no issue found)",
        )
    return df


def clean_feature_catalog():
    df = standardize_columns(pd.read_csv(os.path.join(RAW_DIR, "feature_catalog.csv"), dtype=str))
    df["release_date"], _ = parse_dates_safely(df["release_date"])
    df["core_feature_flag"] = to_bool(df["core_feature_flag"])
    return df


def clean_calendar():
    df = standardize_columns(pd.read_csv(os.path.join(RAW_DIR, "calendar.csv"), dtype=str))
    df["date"], _ = parse_dates_safely(df["date"])
    df["week_start_date"], _ = parse_dates_safely(df["week_start_date"])
    for col in ["week_number", "month", "quarter", "year"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    return df


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def write_quality_summary_markdown(issues_df, path):
    lines = [
        "# Data Quality Summary",
        "",
        f"Generated by `src/transform_data.py` on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.",
        "",
        "All figures below describe the fictional, synthetic Northstar Financial "
        "Group dataset only. See `data/synthetic_data_dictionary.md` and "
        "`docs/assumptions_and_limitations.md` for the full integrity statement.",
        "",
        "| Issue type | Affected records | Resolution | Status |",
        "|---|---:|---|---|",
    ]
    for _, row in issues_df.iterrows():
        lines.append(
            f"| {row['issue_type']} | {row['affected_record_count']:,} | {row['resolution']} | {row['status']} |"
        )
    lines.append("")
    lines.append(f"**Total logged findings:** {len(issues_df)}  ")
    lines.append(f"**Total affected records across all issues:** {issues_df['affected_record_count'].sum():,}")
    lines.append("")
    lines.append(
        "Note: a single record can appear in more than one issue category (e.g. a "
        "duplicate row that also has a normalized label), so affected-record counts "
        "are not mutually exclusive and should not be summed to estimate total "
        "unique bad records."
    )
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    print("Cleaning users.csv ...")
    clean_users_df = clean_users()

    print("Cleaning usage_events.csv ...")
    clean_events_df = clean_usage_events(clean_users_df)

    print("Cleaning feedback.csv ...")
    clean_feedback_df = clean_feedback()

    print("Cleaning training_sessions.csv ...")
    clean_training_df = clean_training_sessions()

    print("Cleaning feature_catalog.csv ...")
    clean_feature_catalog_df = clean_feature_catalog()

    print("Cleaning calendar.csv ...")
    clean_calendar_df = clean_calendar()

    outputs = {
        "clean_users.csv": clean_users_df,
        "clean_usage_events.csv": clean_events_df,
        "clean_feedback.csv": clean_feedback_df,
        "clean_training_sessions.csv": clean_training_df,
        "clean_feature_catalog.csv": clean_feature_catalog_df,
        "clean_calendar.csv": clean_calendar_df,
    }
    for filename, df in outputs.items():
        path = os.path.join(PROCESSED_DIR, filename)
        df.to_csv(path, index=False)
        print(f"  wrote {filename}: {len(df):,} rows -> {path}")

    issues_df = pd.DataFrame(ISSUE_LOG, columns=["issue_type", "affected_record_count", "resolution", "status"])
    issues_path = os.path.join(PROCESSED_DIR, "data_quality_issues.csv")
    issues_df.to_csv(issues_path, index=False)
    print(f"  wrote data_quality_issues.csv: {len(issues_df):,} logged findings -> {issues_path}")

    summary_path = os.path.join(PROCESSED_DIR, "data_quality_summary.md")
    write_quality_summary_markdown(issues_df, summary_path)
    print(f"  wrote data_quality_summary.md -> {summary_path}")

    print("\n=== Cleaning summary (synthetic data only) ===")
    print(f"clean_users.csv: {len(clean_users_df):,} rows (unique users)")
    print(f"clean_usage_events.csv: {len(clean_events_df):,} rows")
    print(f"clean_feedback.csv: {len(clean_feedback_df):,} rows")
    print(f"Logged data-quality findings: {len(issues_df):,}")
    print("\nAll data remains synthetic and fictional (Northstar Financial Group).")


if __name__ == "__main__":
    main()
