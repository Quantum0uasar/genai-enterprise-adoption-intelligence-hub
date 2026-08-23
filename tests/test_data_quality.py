"""
Basic structural tests for the raw synthetic data files.

These tests validate that the generator produced files of the expected shape
and scale. They deliberately do NOT assert that the raw data is clean —
raw/*.csv is expected to contain duplicates, missing values, invalid records,
and inconsistent labels by design (see data/synthetic_data_dictionary.md).
The cleaning pipeline (src/transform_data.py, Phase 2) is what is expected to
fix those issues before analysis; these tests only guard the generator's
contract with the rest of the project.

Run with: pytest tests/test_data_quality.py -v
"""

import os

import pandas as pd
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")

EXPECTED_FILES = [
    "users.csv",
    "usage_events.csv",
    "feedback.csv",
    "training_sessions.csv",
    "feature_catalog.csv",
    "calendar.csv",
]


@pytest.fixture(scope="module")
def raw_frames():
    frames = {}
    for name in EXPECTED_FILES:
        path = os.path.join(RAW_DIR, name)
        frames[name] = pd.read_csv(path, dtype=str)
    return frames


def test_all_raw_files_exist():
    for name in EXPECTED_FILES:
        path = os.path.join(RAW_DIR, name)
        assert os.path.exists(path), f"Missing expected raw file: {name}"


def test_users_row_count(raw_frames):
    users = raw_frames["users.csv"]
    # 6,000 unique users plus a small number of intentional duplicate rows
    assert users["user_id"].nunique() == 6000
    assert len(users) >= 6000


def test_users_expected_columns(raw_frames):
    expected = {
        "user_id", "business_unit", "role", "region", "manager_level",
        "hire_date", "assigned_access_date", "rollout_wave",
        "training_assigned_date", "training_completed_date",
        "training_format", "manager_champion_flag", "eligible_for_access_flag",
    }
    assert expected.issubset(set(raw_frames["users.csv"].columns))


def test_usage_events_row_count_in_range(raw_frames):
    n = len(raw_frames["usage_events.csv"])
    assert 120_000 <= n <= 260_000, f"usage_events.csv has {n} rows, outside expected range"


def test_usage_events_expected_columns(raw_frames):
    expected = {
        "event_id", "user_id", "event_timestamp", "session_id", "feature_name",
        "event_type", "prompt_category", "output_exported_flag",
        "successful_completion_flag", "estimated_minutes_saved",
        "session_duration_seconds", "error_flag", "platform", "source_system",
    }
    assert expected.issubset(set(raw_frames["usage_events.csv"].columns))


def test_feedback_row_count_in_range(raw_frames):
    n = len(raw_frames["feedback.csv"])
    assert 5_000 <= n <= 12_500, f"feedback.csv has {n} rows, outside expected range"


def test_feedback_expected_columns(raw_frames):
    expected = {
        "feedback_id", "user_id", "feedback_timestamp", "rating_1_to_5",
        "sentiment_label", "barrier_category", "free_text_feedback",
        "feature_name", "would_recommend_flag",
    }
    assert expected.issubset(set(raw_frames["feedback.csv"].columns))


def test_feature_catalog_has_eight_features(raw_frames):
    catalog = raw_frames["feature_catalog.csv"]
    assert len(catalog) == 8
    assert catalog["feature_name"].nunique() == 8


def test_calendar_covers_24_weeks(raw_frames):
    calendar = raw_frames["calendar.csv"]
    assert calendar["week_number"].astype(int).max() == 24
    assert calendar["week_number"].astype(int).min() == 1
    assert len(calendar) == 24 * 7


def test_raw_data_contains_expected_quality_issues(raw_frames):
    """
    Confirms the generator actually injected the documented data-quality
    issues, so the Phase 2 cleaning pipeline has real, non-trivial work.
    """
    users = raw_frames["users.csv"]
    events = raw_frames["usage_events.csv"]
    feedback = raw_frames["feedback.csv"]

    # Duplicate rows/ids
    assert len(users) > users["user_id"].nunique()
    assert len(events) > events["event_id"].nunique()
    assert len(feedback) > feedback["feedback_id"].nunique()

    # Inconsistent business_unit labels
    canonical_bus = {
        "Retail Banking", "Commercial Banking", "Capital Markets",
        "Wealth Management", "Operations", "Technology",
        "Risk and Compliance", "Corporate Functions",
    }
    assert not set(users["business_unit"].unique()).issubset(canonical_bus)

    # Negative values that must be flagged/cleaned downstream
    durations = pd.to_numeric(events["session_duration_seconds"], errors="coerce")
    assert (durations < 0).sum() > 0

    minutes = pd.to_numeric(events["estimated_minutes_saved"], errors="coerce")
    assert (minutes < 0).sum() > 0

    # Missing values
    assert events["feature_name"].isna().sum() + (events["feature_name"] == "").sum() > 0

    # Out-of-range feedback ratings
    ratings = pd.to_numeric(feedback["rating_1_to_5"], errors="coerce")
    assert ((ratings < 1) | (ratings > 5)).sum() > 0
