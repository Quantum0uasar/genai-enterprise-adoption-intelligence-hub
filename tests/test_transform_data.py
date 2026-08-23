"""
Tests for the Phase 2 cleaning pipeline output (data/processed/*.csv).

Unlike tests/test_data_quality.py (which documents that the *raw* data
contains intentional issues), these tests assert that the *processed* data
no longer contains them, and that src/transform_data.py's documented
resolutions actually took effect.

Run with: pytest tests/test_transform_data.py -v
(Run `python src/transform_data.py` first if data/processed/ is empty.)
"""

import os

import pandas as pd
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")

EXPECTED_FILES = [
    "clean_users.csv",
    "clean_usage_events.csv",
    "clean_feedback.csv",
    "clean_training_sessions.csv",
    "clean_feature_catalog.csv",
    "clean_calendar.csv",
    "data_quality_issues.csv",
]

CANONICAL_BUSINESS_UNITS = {
    "Retail Banking", "Commercial Banking", "Capital Markets", "Wealth Management",
    "Operations", "Technology", "Risk and Compliance", "Corporate Functions",
}
CANONICAL_FEATURES = {
    "Chat and Research", "Knowledge Search", "Document Summarization", "Meeting Notes",
    "Prompt Library", "Drafting Assistant", "Data Analysis", "Code Assistant",
}


@pytest.fixture(scope="module")
def processed_frames():
    frames = {}
    for name in EXPECTED_FILES:
        path = os.path.join(PROCESSED_DIR, name)
        frames[name] = pd.read_csv(path)
    return frames


def test_all_processed_files_exist():
    for name in EXPECTED_FILES:
        assert os.path.exists(os.path.join(PROCESSED_DIR, name)), f"Missing: {name}"


def test_clean_users_has_unique_ids(processed_frames):
    users = processed_frames["clean_users.csv"]
    assert users["user_id"].nunique() == len(users) == 6000


def test_clean_users_business_unit_is_canonical(processed_frames):
    users = processed_frames["clean_users.csv"]
    assert set(users["business_unit"].unique()) <= CANONICAL_BUSINESS_UNITS


def test_clean_usage_events_has_unique_ids(processed_frames):
    events = processed_frames["clean_usage_events.csv"]
    assert events["event_id"].nunique() == len(events)


def test_clean_usage_events_no_negative_values(processed_frames):
    events = processed_frames["clean_usage_events.csv"]
    assert (events["session_duration_seconds"].dropna() >= 0).all()
    assert (events["estimated_minutes_saved"].dropna() >= 0).all()


def test_clean_usage_events_feature_name_is_canonical_or_null(processed_frames):
    events = processed_frames["clean_usage_events.csv"]
    observed = set(events["feature_name"].dropna().unique())
    assert observed <= CANONICAL_FEATURES


def test_clean_usage_events_no_events_before_access(processed_frames):
    events = processed_frames["clean_usage_events.csv"].copy()
    users = processed_frames["clean_users.csv"].copy()
    events["event_timestamp"] = pd.to_datetime(events["event_timestamp"])
    users["assigned_access_date"] = pd.to_datetime(users["assigned_access_date"])

    access_lookup = users.dropna(subset=["assigned_access_date"]).drop_duplicates(
        "user_id"
    ).set_index("user_id")["assigned_access_date"]
    merged = events.merge(access_lookup.rename("access_date"), left_on="user_id", right_index=True, how="left")
    violations = merged["access_date"].notna() & (
        merged["event_timestamp"].dt.normalize() < merged["access_date"]
    )
    assert violations.sum() == 0


def test_clean_usage_events_timestamps_all_parseable(processed_frames):
    events = processed_frames["clean_usage_events.csv"]
    parsed = pd.to_datetime(events["event_timestamp"], errors="coerce")
    assert parsed.notna().all()


def test_clean_feedback_has_unique_ids(processed_frames):
    feedback = processed_frames["clean_feedback.csv"]
    assert feedback["feedback_id"].nunique() == len(feedback)


def test_clean_feedback_ratings_in_range_or_null(processed_frames):
    feedback = processed_frames["clean_feedback.csv"]
    ratings = feedback["rating_1_to_5"].dropna()
    assert ratings.between(1, 5).all()


def test_data_quality_issues_log_has_expected_columns(processed_frames):
    issues = processed_frames["data_quality_issues.csv"]
    expected_cols = {"issue_type", "affected_record_count", "resolution", "status"}
    assert expected_cols.issubset(set(issues.columns))
    assert len(issues) > 0
    assert (issues["affected_record_count"] >= 0).all()


def test_data_quality_issues_log_documents_known_categories(processed_frames):
    issues = processed_frames["data_quality_issues.csv"]
    issue_types = " ".join(issues["issue_type"].tolist()).lower()
    for keyword in ["duplicate", "business_unit", "feature_name", "negative", "before"]:
        assert keyword in issue_types, f"Expected quality log to mention '{keyword}'"
