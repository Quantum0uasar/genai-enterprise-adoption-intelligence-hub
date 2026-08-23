"""
Structural checks on the generated Excel workbook. Confirms the required
sheets, tables, and key formula cells exist. Does NOT re-run the LibreOffice
recalculation check (that's a slow, separate validation step performed
during development and documented in excel/excel_build_guide.md) — this
just confirms the shipped file has the shape it's supposed to have.

Run with: pytest tests/test_excel_workbook.py -v
(Requires openpyxl; skipped automatically if the workbook hasn't been built.)
"""

import os

import pytest

openpyxl = pytest.importorskip("openpyxl")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX_PATH = os.path.join(PROJECT_ROOT, "excel", "GenAI_Weekly_Adoption_Readout.xlsx")

EXPECTED_SHEETS = [
    "README", "Raw_Events", "Clean_Events", "Users", "Data_Quality_Log",
    "Metric_Calculations", "Pivot_Weekly_Adoption", "Pivot_Feature_Usage",
    "Pivot_Barriers", "Weekly_Readout", "Metric_Dictionary",
]


@pytest.fixture(scope="module")
def workbook():
    if not os.path.exists(XLSX_PATH):
        pytest.skip("Excel workbook not built yet — run python src/build_excel_workbook.py")
    return openpyxl.load_workbook(XLSX_PATH)


def test_workbook_has_all_required_sheets(workbook):
    assert workbook.sheetnames == EXPECTED_SHEETS


def test_metric_calculations_has_key_tables(workbook):
    ws = workbook["Metric_Calculations"]
    table_names = set(ws.tables.keys())
    assert {"tbl_BU", "tbl_Weekly", "tbl_Feature"}.issubset(table_names)


def test_metric_calculations_uses_safe_division_formulas(workbook):
    ws = workbook["Metric_Calculations"]
    formulas = [
        cell.value for row in ws.iter_rows() for cell in row
        if isinstance(cell.value, str) and cell.value.startswith("=")
    ]
    assert any("IFERROR" in f for f in formulas), "Expected at least one IFERROR formula"
    assert any("SUMIFS" in f for f in formulas), "Expected at least one SUMIFS formula"
    assert any("COUNTIFS" in f for f in formulas), "Expected at least one COUNTIFS formula"
    assert any("INDEX" in f and "MATCH" in f for f in formulas), "Expected at least one INDEX/MATCH formula"
    assert not any("XLOOKUP" in f for f in formulas), "XLOOKUP should not appear in live formulas (see excel_build_guide.md)"


def test_weekly_readout_has_native_charts(workbook):
    ws = workbook["Weekly_Readout"]
    assert len(ws._charts) >= 2, "Expected at least 2 native charts on Weekly_Readout"


def test_pivot_sheets_do_not_falsely_claim_native_pivot_tables(workbook):
    for name in ["Pivot_Weekly_Adoption", "Pivot_Feature_Usage", "Pivot_Barriers"]:
        ws = workbook[name]
        found_disclaimer = False
        for row in ws.iter_rows(min_row=1, max_row=5):
            for cell in row:
                if isinstance(cell.value, str) and "pivot-STYLE" in cell.value:
                    found_disclaimer = True
        assert found_disclaimer, f"{name} should disclose it is not a native PivotTable"


def test_data_quality_log_sheet_has_complete_table(workbook):
    ws = workbook["Data_Quality_Log"]
    assert "tbl_DQLog" in ws.tables
