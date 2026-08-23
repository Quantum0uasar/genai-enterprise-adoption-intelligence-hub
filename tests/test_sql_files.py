"""
Structural checks on the SQL deliverables. These do NOT require a running
PostgreSQL instance — they confirm the files exist and contain the expected
schema objects/queries, so the test suite still gives useful signal in an
environment without a database. The actual SQL was executed and validated
against real PostgreSQL 16 during development — see sql/README_VALIDATION.md
for that run log; that is the authoritative "this SQL works" evidence, not
these tests.

Run with: pytest tests/test_sql_files.py -v
"""

import os

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQL_DIR = os.path.join(PROJECT_ROOT, "sql")


@pytest.fixture(scope="module")
def schema_sql():
    with open(os.path.join(SQL_DIR, "01_create_schema.sql")) as f:
        return f.read()


@pytest.fixture(scope="module")
def metrics_sql():
    with open(os.path.join(SQL_DIR, "02_adoption_metrics.sql")) as f:
        return f.read()


@pytest.fixture(scope="module")
def insights_sql():
    with open(os.path.join(SQL_DIR, "03_weekly_insights.sql")) as f:
        return f.read()


def test_sql_files_exist():
    for name in ["01_create_schema.sql", "02_adoption_metrics.sql", "03_weekly_insights.sql", "README_VALIDATION.md"]:
        assert os.path.exists(os.path.join(SQL_DIR, name)), f"Missing: {name}"


def test_schema_defines_all_star_schema_tables(schema_sql):
    expected_tables = [
        "dim_user", "dim_date", "dim_feature", "dim_business_unit", "dim_role",
        "fact_usage_events", "fact_feedback", "fact_training_attendance",
    ]
    for table in expected_tables:
        assert f"CREATE TABLE {table}" in schema_sql, f"Missing CREATE TABLE for {table}"


def test_schema_loads_from_processed_csvs(schema_sql):
    for fname in [
        "clean_users.csv", "clean_usage_events.csv", "clean_feedback.csv",
        "clean_training_sessions.csv", "clean_feature_catalog.csv", "clean_calendar.csv",
    ]:
        assert fname in schema_sql, f"Missing \\copy reference to {fname}"


def test_metrics_sql_covers_all_nine_queries(metrics_sql):
    expected_markers = [
        "QUERY 1", "QUERY 2", "QUERY 3", "QUERY 4", "QUERY 5",
        "QUERY 6", "QUERY 7", "QUERY 8", "QUERY 9",
    ]
    for marker in expected_markers:
        assert marker in metrics_sql, f"Missing {marker} in 02_adoption_metrics.sql"


def test_metrics_sql_time_saved_query_has_disclaimer(metrics_sql):
    assert "MODELED ESTIMATE" in metrics_sql
    assert "not validated ROI" in metrics_sql.lower() or "not validated roi" in metrics_sql.lower()


def test_insights_sql_covers_query_ten(insights_sql):
    assert "week_number" in insights_sql
    assert "business_unit_name" in insights_sql
    assert "disclaimer" in insights_sql.lower()


def test_no_sql_file_references_real_bank():
    all_sql = ""
    for name in ["01_create_schema.sql", "02_adoption_metrics.sql", "03_weekly_insights.sql"]:
        with open(os.path.join(SQL_DIR, name)) as f:
            all_sql += f.read().lower()
    for forbidden in ["rbc", "royal bank", "td bank", "toronto-dominion"]:
        assert forbidden not in all_sql
