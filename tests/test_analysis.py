"""
Sanity tests for src/analysis.py metric functions, run against the real
processed synthetic dataset (data/processed/*.csv).

These are not attempts to validate the "correctness" of a synthetic
scenario (there is no ground truth to check against) — they check that each
metric function runs, returns a sane shape, and stays within logically
required bounds (e.g. a rate is between 0 and 100, a count is non-negative).

Run with: pytest tests/test_analysis.py -v
(Requires data/processed/*.csv to exist — run src/generate_synthetic_data.py
and src/transform_data.py first.)
"""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import analysis as ga  # noqa: E402


@pytest.fixture(scope="module")
def data():
    return ga.load_data()


def test_load_data_returns_all_tables(data):
    expected_keys = {"users", "events", "feedback", "training", "features", "calendar"}
    assert expected_keys == set(data.keys())
    assert len(data["users"]) == 6000


def test_eligible_users_is_subset_of_users(data):
    eligible = ga.get_eligible_users(data["users"])
    assert len(eligible) <= len(data["users"])
    assert eligible["eligible_for_access_flag"].all()
    assert eligible["assigned_access_date"].notna().all()


def test_activation_rate_overall_in_valid_range(data):
    result = ga.activation_rate(data["users"], data["events"])
    assert 0 <= result["activation_rate_pct"] <= 100
    assert result["activated_users"] <= result["eligible_users"]


def test_activation_rate_by_business_unit_sums_consistently(data):
    result = ga.activation_rate(data["users"], data["events"], groupby="business_unit")
    assert len(result) == 8
    assert (result["activation_rate_pct"].between(0, 100)).all()
    assert (result["activated_users"] <= result["eligible_users"]).all()


def test_weekly_active_users_covers_all_24_weeks(data):
    wau = ga.weekly_active_users(data["events"], data["calendar"])
    assert set(wau["week_number"]) == set(range(1, 25))
    assert (wau["weekly_active_users"] > 0).all()


def test_weekly_active_users_by_segment_requires_users_arg(data):
    with pytest.raises(ValueError):
        ga.weekly_active_users(data["events"], data["calendar"], groupby="business_unit")

    wau_bu = ga.weekly_active_users(data["events"], data["calendar"], users=data["users"], groupby="business_unit")
    assert len(wau_bu) == 24 * 8


def test_mau_28d_is_positive_and_bounded(data):
    mau = ga.mau_28d(data["events"])
    assert 0 < mau <= 6000


def test_feature_adoption_rate_ungrouped_has_nonzero_adoption(data):
    result = ga.feature_adoption_rate(data["users"], data["events"])
    assert len(result) == 8
    assert (result["adopted_users"] > 0).all()
    assert (result["feature_adoption_rate_pct"].between(0, 100)).all()


def test_median_time_to_value_is_positive(data):
    result = ga.median_time_to_value(data["users"], data["events"])
    assert (result["median_hours_to_value"] > 0).all()
    assert len(result) == 8


def test_retention_cohorts_week_zero_is_100_pct(data):
    result = ga.retention_cohorts(data["events"], data["calendar"])
    week_zero = result[result["weeks_since_activation"] == 0]
    assert (week_zero["retention_rate_pct"] == 100.0).all()


def test_dormant_users_rate_bounded(data):
    result = ga.dormant_users(data["users"], data["events"])
    assert (result["dormancy_rate_pct"].between(0, 100)).all()
    assert (result["dormant_users"] <= result["activated_users"]).all()


def test_training_completion_rate_bounded(data):
    result = ga.training_completion_rate(data["users"])
    assert 0 <= result["training_completion_rate_pct"] <= 100


def test_training_vs_activation_shows_two_rows(data):
    result = ga.training_vs_activation(data["users"], data["events"])
    assert set(result["training_status"]) == {"Completed Training", "Did Not Complete Training"}
    assert (result["activation_rate_pct"].between(0, 100)).all()


def test_estimated_time_saved_is_nonnegative(data):
    result = ga.estimated_time_saved(data["events"])
    assert (result["total_estimated_minutes_saved"] >= 0).all()
    assert (result["disclaimer"] == ga.TIME_SAVED_DISCLAIMER).all()


def test_recommendation_rate_bounded(data):
    result = ga.recommendation_rate(data["feedback"])
    assert 0 <= result["recommendation_rate_pct"] <= 100


def test_barrier_ranking_ranks_start_at_one(data):
    result = ga.barrier_ranking(data["feedback"], data["users"])
    assert result.groupby("business_unit")["barrier_rank"].min().eq(1).all()
