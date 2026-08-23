"""
GenAI Enterprise Adoption Intelligence Hub
Builds excel/GenAI_Weekly_Adoption_Readout.xlsx from the cleaned processed
data. Re-run this after regenerating data/processed/ to refresh the
workbook with new numbers (see excel/excel_build_guide.md §5).

IMPORTANT: after running this script, validate it before treating the
output as done — e.g. with the xlsx skill's recalc.py (LibreOffice-based
formula recalculation check) or by opening and saving in real Excel. Ship
only if it reports zero formula errors.

Formula constraints followed here (see excel/excel_build_guide.md §3 for why):
- No XLOOKUP / LET / TEXTJOIN / CONCAT / IFS / SWITCH / MAXIFS / MINIFS /
  SORT / FILTER / UNIQUE / SEQUENCE anywhere in the live workbook — these
  cannot be reliably recalculated/verified by a LibreOffice-based
  recalculation check, so shipping them risks an unverifiable or
  silently-wrong formula. INDEX/MATCH is used in place of XLOOKUP
  (functionally equivalent).
- Rates are stored as fractions (0-1) with a percentage number format.

SYNTHETIC DATA ONLY — see data/synthetic_data_dictionary.md and
docs/assumptions_and_limitations.md.
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from src import analysis as ga

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.formatting.rule import ColorScaleRule, CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
OUT_PATH = os.path.join(PROJECT_ROOT, "excel", "GenAI_Weekly_Adoption_Readout.xlsx")

NAVY = "1B3A6B"
BLUE = "2F5F9E"
LIGHT_GRAY = "F2F4F7"
WHITE = "FFFFFF"
RED = "A3324A"
FONT_NAME = "Arial"

# ---------------------------------------------------------------------------
# 1. Load and prepare data
# ---------------------------------------------------------------------------
data = ga.load_data(PROCESSED_DIR)
users, events, feedback, calendar = data["users"], data["events"], data["feedback"], data["calendar"]

act = ga.activation_rate(users, events, groupby="business_unit")
ttv = ga.median_time_to_value(users, events)
train = ga.training_completion_rate(users, groupby="business_unit")
dorm = ga.dormant_users(users, events)

bu_metrics = (
    act.merge(ttv, on="business_unit", how="left")
    .merge(train, on="business_unit", how="left")
    .merge(dorm.drop(columns=["activated_users"]), on="business_unit", how="left")
)
bu_metrics["activation_rate"] = bu_metrics["activation_rate_pct"] / 100.0
bu_metrics["training_completion_rate"] = bu_metrics["training_completion_rate_pct"] / 100.0
bu_metrics["dormancy_rate"] = bu_metrics["dormancy_rate_pct"] / 100.0
bu_metrics = bu_metrics[[
    "business_unit", "eligible_users", "activated_users", "activation_rate",
    "median_hours_to_value", "training_completion_rate", "dormancy_rate",
]].round(4)

weekly_metrics = ga.weekly_active_users(events, calendar)[["week_number", "week_start_date", "weekly_active_users"]].copy()
weekly_metrics["week_start_date"] = pd.to_datetime(weekly_metrics["week_start_date"]).dt.date

feat = ga.feature_adoption_rate(users, events)
saved = ga.estimated_time_saved(events)
feature_metrics = feat.merge(saved[["feature_name", "total_estimated_hours_saved"]], on="feature_name", how="left")
feature_metrics["feature_adoption_rate"] = feature_metrics["feature_adoption_rate_pct"] / 100.0
feature_metrics = feature_metrics[["feature_name", "eligible_users", "adopted_users", "feature_adoption_rate", "total_estimated_hours_saved"]].round(2)

barrier_merged = feedback.merge(users[["user_id", "business_unit"]], on="user_id", how="left")
barrier_merged = barrier_merged[barrier_merged["barrier_category"].notna() & (barrier_merged["barrier_category"] != "No barrier reported")]
barrier_matrix = barrier_merged.pivot_table(index="business_unit", columns="barrier_category", values="feedback_id", aggfunc="count", fill_value=0)
barrier_matrix = barrier_matrix.reset_index()

feature_events = events[events["event_type"].isin(["feature_completed", "output_exported"])].merge(
    users[["user_id", "business_unit"]], on="user_id", how="left"
)
feature_usage_matrix = feature_events.pivot_table(index="feature_name", columns="business_unit", values="event_id", aggfunc="count", fill_value=0)
feature_usage_matrix = feature_usage_matrix.reset_index()

wau_by_bu = ga.weekly_active_users(events, calendar, users=users, groupby="business_unit")
weekly_bu_matrix = wau_by_bu.pivot_table(index="week_number", columns="business_unit", values="weekly_active_users", fill_value=0)
weekly_bu_matrix = weekly_bu_matrix.reset_index()

quality_log = pd.read_csv(os.path.join(PROCESSED_DIR, "data_quality_issues.csv"))

raw_events_sample = pd.read_csv(os.path.join(RAW_DIR, "usage_events.csv")).sample(n=3000, random_state=42).sort_values("event_timestamp")
clean_events_sample = events.sample(n=3000, random_state=42).sort_values("event_timestamp").copy()
clean_events_sample["event_timestamp"] = clean_events_sample["event_timestamp"].astype(str)

users_out = users.copy()
for col in ["hire_date", "assigned_access_date", "training_assigned_date", "training_completed_date"]:
    users_out[col] = pd.to_datetime(users_out[col]).dt.date

METRIC_DICT_ROWS = [
    ("Eligible Users", "Count of users assigned access AND eligible_for_access_flag=TRUE", "N/A", "As of reporting date", "Base population for all adoption metrics", "A few users have an access date but are flagged ineligible (entitlement lag) — correctly excluded"),
    ("Activation Rate", "Activated eligible users", "Eligible users", "Point-in-time (first 14 days post-access)", "Distinguishes access from real use", "Designed, association-based definition — not a validated causal model"),
    ("Weekly Active Users (WAU)", "Distinct users with >=1 meaningful action", "N/A", "Per calendar week", "Standard weekly adoption pulse", "Treats all meaningful actions equally regardless of depth"),
    ("MAU (28-day)", "Distinct users with >=1 meaningful action", "N/A", "Trailing 28 days", "Less noisy active-base measure than WAU", "Rolling window can mask a recent sharp change"),
    ("Stickiness (WAU/MAU)", "WAU", "MAU (28-day)", "Weekly, vs trailing 28-day MAU", "Proxy for engagement depth", "NOT a complete measure of value delivered"),
    ("Feature Adoption Rate", "Distinct users who completed/exported a feature", "Distinct eligible users", "Cumulative to date", "Which features drive completed use", "Denominator is ALL eligible users, not the feature's target persona"),
    ("Median Time-to-Value (hrs)", "Hours from access to first successful value event", "N/A (median across users)", "Once per user", "Speed of onboarding to real outcomes", "Only computed for users who reached a first successful action"),
    ("Retention (weekly cohort)", "Cohort users active in cohort_week + N", "Cohort size", "Weeks 0-8 post cohort start", "Does engagement hold up over time", "Cohort = week of first meaningful action, a simpler proxy than full activation"),
    ("Dormancy Rate", "Activated users with no action in trailing 28 days", "Activated users", "Rolling 28 days as of reference date", "Re-engagement target list", "Sensitive to the chosen reference date"),
    ("Training Completion Rate", "Users with training_completed_date", "Users with training_assigned_date", "Cumulative to date", "Enablement team completion KPI", "Captures completion only, not training quality"),
    ("Estimated Time Saved", "Sum of estimated_minutes_saved on successful value events", "N/A (or per user/feature average)", "Cumulative to date", "Directional signal of feature-level value", "MODELED ASSUMPTION — not validated ROI, never a real productivity claim"),
    ("Recommendation Rate", "Feedback with would_recommend_flag=TRUE", "All feedback with a non-null flag", "Cumulative, or by week/BU", "Simple NPS-style sentiment pulse", "Feedback is self-selected, may not represent the full population evenly"),
]

TOP_INSIGHTS = [
    "Technology and Capital Markets activate earliest and deepest; Risk and Compliance starts slowest on WAU but shows the fastest median time-to-value and lowest dormancy once activated (synthetic pattern).",
    "Retail Banking and Operations carry the largest eligible populations but the lowest activation rates, both associated (not proven causal) with lower training completion in this dataset.",
    "Knowledge Search and Document Summarization show the broadest adoption; Code Assistant and Data Analysis remain concentrated among technical roles, as designed.",
]
TOP_ACTIONS = [
    ("Retail Banking / Operations", "Launch a manager-championed, role-specific refresher on Knowledge Search and Document Summarization", "Enablement", "Activation rate +5pts within 4 weeks"),
    ("Risk and Compliance", "Publish 3 additional approved-use-case examples to reduce 'unsure what's allowed' barrier mentions", "Business Champion", "Barrier mention share -10pts within 3 weeks"),
    ("Company-wide", "Promote Prompt Library in onboarding, given its association with higher activation/retention in this dataset", "Product", "Prompt Library adoption +8pts within 4 weeks"),
]

print("Data prep complete:")
print("  bu_metrics:", bu_metrics.shape)
print("  weekly_metrics:", weekly_metrics.shape)
print("  feature_metrics:", feature_metrics.shape)
print("  barrier_matrix:", barrier_matrix.shape)
print("  feature_usage_matrix:", feature_usage_matrix.shape)
print("  weekly_bu_matrix:", weekly_bu_matrix.shape)
print("  quality_log:", quality_log.shape)
print("  raw_events_sample:", raw_events_sample.shape)
print("  clean_events_sample:", clean_events_sample.shape)
print("  users_out:", users_out.shape)


# ---------------------------------------------------------------------------
# 2. Workbook + shared styling helpers
# ---------------------------------------------------------------------------
wb = Workbook()
wb.remove(wb.active)

TITLE_FONT = Font(name=FONT_NAME, size=16, bold=True, color=NAVY)
SUBTITLE_FONT = Font(name=FONT_NAME, size=10, italic=True, color="555555")
HEADER_FONT = Font(name=FONT_NAME, size=10, bold=True, color=WHITE)
HEADER_FILL = PatternFill("solid", fgColor=NAVY)
BODY_FONT = Font(name=FONT_NAME, size=10)
DISCLAIMER_FONT = Font(name=FONT_NAME, size=10, italic=True, bold=True, color=RED)
KPI_LABEL_FONT = Font(name=FONT_NAME, size=9, color="555555")
KPI_VALUE_FONT = Font(name=FONT_NAME, size=20, bold=True, color=NAVY)
INPUT_FILL = PatternFill("solid", fgColor="FFFF99")
THIN_BORDER = Border(*(Side(style="thin", color="D0D0D0"),) * 4)

TABLE_STYLE = TableStyleInfo(
    name="TableStyleMedium2", showFirstColumn=False, showLastColumn=False,
    showRowStripes=True, showColumnStripes=False,
)


def style_header_row(ws, row, n_cols):
    for c in range(1, n_cols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def autosize(ws, n_cols, min_width=10, max_width=42):
    for c in range(1, n_cols + 1):
        col_letter = get_column_letter(c)
        max_len = min_width
        for cell in ws[col_letter]:
            if cell.value is not None:
                max_len = max(max_len, min(len(str(cell.value)) + 2, max_width))
        ws.column_dimensions[col_letter].width = max_len


def write_df_as_table(ws, df, start_row, start_col, table_name, style=TABLE_STYLE, date_cols=None):
    """Writes a DataFrame starting at (start_row, start_col) and wraps it in a
    real openpyxl Table (a native Excel Table object)."""
    date_cols = date_cols or []
    n_rows, n_cols = df.shape
    for j, col in enumerate(df.columns):
        ws.cell(row=start_row, column=start_col + j, value=str(col))
    for i, row in enumerate(df.itertuples(index=False)):
        for j, val in enumerate(row):
            cell = ws.cell(row=start_row + 1 + i, column=start_col + j)
            if pd.isna(val):
                cell.value = None
            elif df.columns[j] in date_cols:
                cell.value = val
                cell.number_format = "yyyy-mm-dd"
            elif isinstance(val, (bool,)):
                cell.value = val
            elif isinstance(val, float) and "rate" in df.columns[j].lower():
                cell.value = val
                cell.number_format = "0.0%"
            else:
                cell.value = val
    style_header_row(ws, start_row, n_cols)
    end_row = start_row + n_rows
    end_col = start_col + n_cols - 1
    ref = f"{get_column_letter(start_col)}{start_row}:{get_column_letter(end_col)}{end_row}"
    tbl = Table(displayName=table_name, ref=ref)
    tbl.tableStyleInfo = style
    ws.add_table(tbl)
    autosize(ws, end_col)
    ws.freeze_panes = ws.cell(row=start_row + 1, column=start_col).coordinate
    return start_row, start_col, end_row, end_col


def col_ref(table_name, col_name):
    return f"{table_name}[{col_name}]"


# ---------------------------------------------------------------------------
# 3. README
# ---------------------------------------------------------------------------
ws = wb.create_sheet("README")
ws["B2"] = "GenAI Enterprise Adoption Intelligence Hub"
ws["B2"].font = TITLE_FONT
ws["B3"] = "GenAI_Weekly_Adoption_Readout.xlsx — companion Excel workbook"
ws["B3"].font = SUBTITLE_FONT
ws["B5"] = ("SYNTHETIC PORTFOLIO DATA. Northstar Financial Group and Northstar Assist are fictional. "
            "No real company, employee, or ROI figure is represented anywhere in this workbook. "
            "'Estimated hours saved' is a modeled assumption from the data generator, not validated ROI.")
ws["B5"].font = DISCLAIMER_FONT
ws["B5"].alignment = Alignment(wrap_text=True)
ws.merge_cells("B5:H7")

readme_rows = [
    ("Sheet", "What it contains", "Live/formula-driven?"),
    ("README", "This overview.", "Static"),
    ("Raw_Events", "A random sample of 3,000 of the 238,617 raw usage events, including the intentional data-quality issues (nulls, negative values, label variants, duplicates) — for before/after illustration only.", "Static extract"),
    ("Clean_Events", "A random sample of 3,000 of the 236,960 cleaned usage events (post src/transform_data.py).", "Static extract"),
    ("Users", "The full cleaned roster of 6,000 synthetic users.", "Static extract (complete, not sampled)"),
    ("Data_Quality_Log", "The full data_quality_issues.csv log (19 findings) from the cleaning pipeline.", "Static extract (complete)"),
    ("Metric_Calculations", "Complete (non-sampled) business-unit, weekly, and feature aggregate tables, plus headline KPI formulas using SUMIFS / COUNTIFS / IFERROR / INDEX-MATCH.", "LIVE FORMULAS"),
    ("Pivot_Weekly_Adoption", "A pivot-style WAU-by-week-by-business-unit summary table (see note below).", "Static computed summary"),
    ("Pivot_Feature_Usage", "A pivot-style feature-by-business-unit usage summary table.", "Static computed summary"),
    ("Pivot_Barriers", "A pivot-style barrier-by-business-unit mention-count summary table, with conditional formatting.", "Static computed summary"),
    ("Weekly_Readout", "The one-page leadership readout: KPI cards, two native Excel charts, top 3 insights, top 3 recommended actions.", "LIVE (KPI cells + charts link to Metric_Calculations)"),
    ("Metric_Dictionary", "Numerator / denominator / timeframe / purpose / caveat for every metric in this workbook.", "Static reference"),
]
for i, row in enumerate(readme_rows):
    r = 9 + i
    for j, val in enumerate(row):
        cell = ws.cell(row=r, column=2 + j, value=val)
        cell.font = HEADER_FONT if i == 0 else BODY_FONT
        cell.fill = HEADER_FILL if i == 0 else PatternFill("solid", fgColor=WHITE)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
for j in range(3):
    ws.column_dimensions[get_column_letter(2 + j)].width = [22, 80, 34][j]

note_row = 9 + len(readme_rows) + 2
ws.cell(row=note_row, column=2, value=(
    "IMPORTANT — what is and isn't automated in this file: the three Pivot_* sheets are "
    "pivot-STYLE summary tables computed in Python/pandas, not native Excel PivotTable objects "
    "with slicers — openpyxl cannot author a real PivotCache/PivotTable that Excel recognizes as "
    "interactive. This workbook also does not contain a live Power Query connection to the raw "
    "CSVs. Both are fully achievable manually in Excel Desktop in a few minutes — see "
    "excel/excel_build_guide.md for exact click-by-click steps, including how to turn "
    "Clean_Events into a real refreshable PivotTable with slicers."
)).font = Font(name=FONT_NAME, size=10, italic=True, color=RED)
ws.cell(row=note_row, column=2).alignment = Alignment(wrap_text=True)
ws.merge_cells(start_row=note_row, start_column=2, end_row=note_row + 4, end_column=8)

note_row2 = note_row + 6
ws.cell(row=note_row2, column=2, value=(
    "Formula note: XLOOKUP, LET, and several Excel-365-only functions are intentionally not used "
    "in this workbook's live formulas — the automated recalculation check used to validate this "
    "file could not verify them reliably. INDEX/MATCH is used in place of XLOOKUP (fully "
    "equivalent). If you have Excel 365, feel free to swap in XLOOKUP/LET — the build guide shows "
    "the equivalent syntax."
)).font = Font(name=FONT_NAME, size=9, italic=True, color="555555")
ws.cell(row=note_row2, column=2).alignment = Alignment(wrap_text=True)
ws.merge_cells(start_row=note_row2, start_column=2, end_row=note_row2 + 3, end_column=8)

ws.sheet_view.showGridLines = False


# ---------------------------------------------------------------------------
# 4. Raw_Events / Clean_Events / Users / Data_Quality_Log
# ---------------------------------------------------------------------------
ws = wb.create_sheet("Raw_Events")
ws["B1"] = "Raw_Events — illustrative sample (3,000 of 238,617 total raw rows)"
ws["B1"].font = TITLE_FONT
ws["B2"] = ("Sample only — includes intentional data-quality issues (nulls, negative values, "
            "inconsistent labels, duplicates). Full raw dataset: data/raw/usage_events.csv.")
ws["B2"].font = SUBTITLE_FONT
raw_cols = list(raw_events_sample.columns)
write_df_as_table(ws, raw_events_sample.reset_index(drop=True), start_row=4, start_col=2, table_name="tbl_RawEvents")

ws = wb.create_sheet("Clean_Events")
ws["B1"] = "Clean_Events — illustrative sample (3,000 of 236,960 total cleaned rows)"
ws["B1"].font = TITLE_FONT
ws["B2"] = "Sample only, post src/transform_data.py. Full cleaned dataset: data/processed/clean_usage_events.csv."
ws["B2"].font = SUBTITLE_FONT
write_df_as_table(ws, clean_events_sample.reset_index(drop=True), start_row=4, start_col=2, table_name="tbl_CleanEvents")

ws = wb.create_sheet("Users")
ws["B1"] = "Users — complete cleaned roster (6,000 of 6,000, not sampled)"
ws["B1"].font = TITLE_FONT
ws["B2"] = "Source: data/processed/clean_users.csv"
ws["B2"].font = SUBTITLE_FONT
write_df_as_table(
    ws, users_out.reset_index(drop=True), start_row=4, start_col=2, table_name="tbl_Users",
    date_cols=["hire_date", "assigned_access_date", "training_assigned_date", "training_completed_date"],
)

ws = wb.create_sheet("Data_Quality_Log")
ws["B1"] = "Data_Quality_Log — complete (19 of 19 findings, not sampled)"
ws["B1"].font = TITLE_FONT
ws["B2"] = "Source: data/processed/data_quality_issues.csv, produced by src/transform_data.py"
ws["B2"].font = SUBTITLE_FONT
write_df_as_table(ws, quality_log.reset_index(drop=True), start_row=4, start_col=2, table_name="tbl_DQLog")


print("Sheets 1-5 (README, Raw_Events, Clean_Events, Users, Data_Quality_Log) written.")


# ---------------------------------------------------------------------------
# 5. Metric_Calculations — complete (non-sampled) aggregate tables + live formulas
# ---------------------------------------------------------------------------
ws = wb.create_sheet("Metric_Calculations")
ws["B1"] = "Metric_Calculations — complete aggregate tables and live formulas"
ws["B1"].font = TITLE_FONT
ws["B2"] = ("Unlike Raw_Events/Clean_Events, the tables below are COMPLETE (all 8 business units, "
            "all 24 weeks, all 8 features) — every formula on this sheet is a real, correct "
            "calculation, not an estimate from a sample.")
ws["B2"].font = SUBTITLE_FONT
ws["B2"].alignment = Alignment(wrap_text=True)
ws.merge_cells("B2:J2")

ws["B4"] = "Business Unit Metrics (complete, 8 rows)"
ws["B4"].font = Font(name=FONT_NAME, size=12, bold=True, color=NAVY)
bu_start_row, bu_start_col, bu_end_row, bu_end_col = write_df_as_table(
    ws, bu_metrics.reset_index(drop=True), start_row=5, start_col=2, table_name="tbl_BU"
)

weekly_start_row = 5
weekly_start_col = bu_end_col + 2
ws.cell(row=4, column=weekly_start_col, value="Weekly Metrics (complete, 24 rows)").font = Font(name=FONT_NAME, size=12, bold=True, color=NAVY)
w_r0, w_c0, w_r1, w_c1 = write_df_as_table(
    ws, weekly_metrics.reset_index(drop=True), start_row=weekly_start_row, start_col=weekly_start_col,
    table_name="tbl_Weekly", date_cols=["week_start_date"],
)

feature_start_row = bu_end_row + 3
ws.cell(row=feature_start_row - 1, column=2, value="Feature Metrics (complete, 8 rows)").font = Font(name=FONT_NAME, size=12, bold=True, color=NAVY)
f_r0, f_c0, f_r1, f_c1 = write_df_as_table(
    ws, feature_metrics.reset_index(drop=True), start_row=feature_start_row, start_col=2, table_name="tbl_Feature"
)

# --- Headline KPIs (live formulas) ---
kpi_header_row = feature_start_row - 1
kpi_col = f_c1 + 2
ws.cell(row=kpi_header_row, column=kpi_col, value="Headline KPIs (live formulas)").font = Font(name=FONT_NAME, size=12, bold=True, color=NAVY)

kpi_label_col = kpi_col
kpi_value_col = kpi_col + 1

def kpi_row(r, label, formula_or_value, number_format=None, is_formula=True):
    ws.cell(row=r, column=kpi_label_col, value=label).font = BODY_FONT
    cell = ws.cell(row=r, column=kpi_value_col)
    cell.value = formula_or_value
    cell.font = Font(name=FONT_NAME, size=10, bold=True, color=BLUE)
    if number_format:
        cell.number_format = number_format
    return r + 1

r = kpi_header_row + 1
r = kpi_row(r, "Total Eligible Users (SUM)", f"=SUM({col_ref('tbl_BU','eligible_users')})")
r = kpi_row(r, "Total Activated Users (SUM)", f"=SUM({col_ref('tbl_BU','activated_users')})")
elig_cell = f"{get_column_letter(kpi_value_col)}{kpi_header_row + 1}"
act_cell = f"{get_column_letter(kpi_value_col)}{kpi_header_row + 2}"
r = kpi_row(r, "Company Activation Rate (IFERROR)", f"=IFERROR({act_cell}/{elig_cell},\"N/A\")", "0.0%")
r = kpi_row(r, "Avg. Training Completion Rate (AVERAGE)", f"=AVERAGE({col_ref('tbl_BU','training_completion_rate')})", "0.0%")
r = kpi_row(r, "# Business Units Below 75% Activation (COUNTIFS)", f"=COUNTIFS({col_ref('tbl_BU','activation_rate')},\"<0.75\")")
r = kpi_row(r, "Total WAU, Weeks 12+ (SUMIFS)", f"=SUMIFS({col_ref('tbl_Weekly','weekly_active_users')},{col_ref('tbl_Weekly','week_number')},\">=12\")")
r = kpi_row(r, "# Features Above 50% Adoption (COUNTIFS)", f"=COUNTIFS({col_ref('tbl_Feature','feature_adoption_rate')},\">0.5\")")
r = kpi_row(r, "Total Estimated Hours Saved (SUM, modeled)", f"=SUM({col_ref('tbl_Feature','total_estimated_hours_saved')})", "#,##0")

r += 1
ws.cell(row=r, column=kpi_label_col, value="Lookup a business unit (INDEX/MATCH):").font = Font(name=FONT_NAME, size=10, bold=True)
r += 1
ws.cell(row=r, column=kpi_label_col, value="Business unit name (edit me):").font = BODY_FONT
input_cell = ws.cell(row=r, column=kpi_value_col, value="Retail Banking")
input_cell.fill = INPUT_FILL
input_cell.font = Font(name=FONT_NAME, size=10, bold=True)
input_cell_ref = f"{get_column_letter(kpi_value_col)}{r}"
r += 1
r = kpi_row(
    r, "-> Activation Rate (INDEX/MATCH + IFERROR)",
    f"=IFERROR(INDEX({col_ref('tbl_BU','activation_rate')},MATCH({input_cell_ref},{col_ref('tbl_BU','business_unit')},0)),\"Not found\")",
    "0.0%",
)
r = kpi_row(
    r, "-> Median Time to Value, hrs (INDEX/MATCH)",
    f"=IFERROR(INDEX({col_ref('tbl_BU','median_hours_to_value')},MATCH({input_cell_ref},{col_ref('tbl_BU','business_unit')},0)),\"Not found\")",
    "0.0",
)
r = kpi_row(
    r, "-> Dormancy Rate (INDEX/MATCH)",
    f"=IFERROR(INDEX({col_ref('tbl_BU','dormancy_rate')},MATCH({input_cell_ref},{col_ref('tbl_BU','business_unit')},0)),\"Not found\")",
    "0.0%",
)

r += 1
ws.cell(row=r, column=kpi_label_col, value=(
    "Note: XLOOKUP is the modern equivalent of the INDEX/MATCH formulas above and works "
    "identically in Excel 2021/365. INDEX/MATCH is used here for broader compatibility and "
    "because it was verifiable in this project's automated build-validation environment — "
    "see excel_build_guide.md."
)).font = Font(name=FONT_NAME, size=9, italic=True, color="555555")
ws.cell(row=r, column=kpi_label_col).alignment = Alignment(wrap_text=True)
ws.merge_cells(start_row=r, start_column=kpi_label_col, end_row=r + 3, end_column=kpi_label_col + 1)

# Conditional formatting on BU metrics
ws.conditional_formatting.add(
    f"{get_column_letter(bu_start_col + 3)}{bu_start_row + 1}:{get_column_letter(bu_start_col + 3)}{bu_end_row}",
    ColorScaleRule(start_type="min", start_color="F8696B", end_type="max", end_color="63BE7B"),
)  # activation_rate column
ws.conditional_formatting.add(
    f"{get_column_letter(bu_start_col + 6)}{bu_start_row + 1}:{get_column_letter(bu_start_col + 6)}{bu_end_row}",
    ColorScaleRule(start_type="min", start_color="63BE7B", end_type="max", end_color="F8696B"),
)  # dormancy_rate column (reversed: high dormancy = red)
ws.conditional_formatting.add(
    f"{get_column_letter(bu_start_col + 3)}{bu_start_row + 1}:{get_column_letter(bu_start_col + 3)}{bu_end_row}",
    CellIsRule(operator="lessThan", formula=["0.75"], fill=PatternFill("solid", fgColor="FFC7CE")),
)

ws.sheet_view.showGridLines = False

print("Metric_Calculations written.")


# ---------------------------------------------------------------------------
# 6. Pivot-style summary sheets (NOT native PivotTables — see README/guide)
# ---------------------------------------------------------------------------
def add_pivot_note(ws, text):
    ws["B2"] = text
    ws["B2"].font = Font(name=FONT_NAME, size=9, italic=True, color=RED)
    ws["B2"].alignment = Alignment(wrap_text=True)
    ws.merge_cells("B2:K3")


PIVOT_NOTE = (
    "This is a pivot-STYLE summary table computed in Python from the COMPLETE dataset (not "
    "sampled) — not a native Excel PivotTable object. openpyxl cannot author a real "
    "PivotCache/PivotTable that Excel recognizes as interactive/refreshable/sliceable. "
    "See excel_build_guide.md to build the live, refreshable version with slicers yourself."
)

ws = wb.create_sheet("Pivot_Weekly_Adoption")
ws["B1"] = "Pivot_Weekly_Adoption — WAU by week x business unit"
ws["B1"].font = TITLE_FONT
add_pivot_note(ws, PIVOT_NOTE)
wk_r0, wk_c0, wk_r1, wk_c1 = write_df_as_table(ws, weekly_bu_matrix.reset_index(drop=True), start_row=5, start_col=2, table_name="tbl_PivotWeekly")
for c in range(wk_c0 + 1, wk_c1 + 1):
    col_letter = get_column_letter(c)
    ws.conditional_formatting.add(
        f"{col_letter}{wk_r0 + 1}:{col_letter}{wk_r1}",
        ColorScaleRule(start_type="min", start_color="FFFFFF", end_type="max", end_color=BLUE),
    )
ws.sheet_view.showGridLines = False

ws = wb.create_sheet("Pivot_Feature_Usage")
ws["B1"] = "Pivot_Feature_Usage — completed/exported feature usage by business unit"
ws["B1"].font = TITLE_FONT
add_pivot_note(ws, PIVOT_NOTE)
fu_r0, fu_c0, fu_r1, fu_c1 = write_df_as_table(ws, feature_usage_matrix.reset_index(drop=True), start_row=5, start_col=2, table_name="tbl_PivotFeatureUsage")
for c in range(fu_c0 + 1, fu_c1 + 1):
    col_letter = get_column_letter(c)
    ws.conditional_formatting.add(
        f"{col_letter}{fu_r0 + 1}:{col_letter}{fu_r1}",
        ColorScaleRule(start_type="min", start_color="FFFFFF", end_type="max", end_color=BLUE),
    )
ws.sheet_view.showGridLines = False

ws = wb.create_sheet("Pivot_Barriers")
ws["B1"] = "Pivot_Barriers — feedback barrier mentions by business unit (excludes 'No barrier reported')"
ws["B1"].font = TITLE_FONT
add_pivot_note(ws, PIVOT_NOTE)
br_r0, br_c0, br_r1, br_c1 = write_df_as_table(ws, barrier_matrix.reset_index(drop=True), start_row=5, start_col=2, table_name="tbl_PivotBarriers")
for c in range(br_c0 + 1, br_c1 + 1):
    col_letter = get_column_letter(c)
    ws.conditional_formatting.add(
        f"{col_letter}{br_r0 + 1}:{col_letter}{br_r1}",
        ColorScaleRule(start_type="min", start_color="FFFFFF", end_type="max", end_color=RED),
    )
ws.sheet_view.showGridLines = False

print("Pivot_* sheets written.")


# ---------------------------------------------------------------------------
# 7. Weekly_Readout — one-page leadership readout (KPI cards + 2 native charts)
# ---------------------------------------------------------------------------
ws = wb.create_sheet("Weekly_Readout")
ws.sheet_view.showGridLines = False
ws["B2"] = "GenAI Adoption Weekly Readout — Week 24 (Synthetic)"
ws["B2"].font = TITLE_FONT
ws["B3"] = "Northstar Financial Group / Northstar Assist — fictional scenario, synthetic data"
ws["B3"].font = SUBTITLE_FONT
ws["B4"] = "SYNTHETIC PORTFOLIO DATA. Estimated time saved is modeled, not validated ROI. No causal claims."
ws["B4"].font = DISCLAIMER_FONT

kpi_specs = [
    ("Eligible Users", f"='Metric_Calculations'!{elig_cell}", None),
    ("Activated Users", f"='Metric_Calculations'!{act_cell}", None),
    ("Company Activation Rate", f"='Metric_Calculations'!{get_column_letter(kpi_value_col)}{kpi_header_row + 3}", "0.0%"),
    ("Total Estimated Hours Saved (modeled)", f"='Metric_Calculations'!{get_column_letter(kpi_value_col)}{kpi_header_row + 8}", "#,##0"),
]
kpi_start_col = 2
for i, (label, formula, fmt) in enumerate(kpi_specs):
    c0 = kpi_start_col + i * 3
    ws.merge_cells(start_row=6, start_column=c0, end_row=6, end_column=c0 + 1)
    lbl_cell = ws.cell(row=6, column=c0, value=label)
    lbl_cell.font = KPI_LABEL_FONT
    lbl_cell.fill = PatternFill("solid", fgColor=LIGHT_GRAY)
    lbl_cell.alignment = Alignment(horizontal="center", wrap_text=True)
    ws.merge_cells(start_row=7, start_column=c0, end_row=8, end_column=c0 + 1)
    val_cell = ws.cell(row=7, column=c0, value=formula)
    val_cell.font = KPI_VALUE_FONT
    val_cell.fill = PatternFill("solid", fgColor=LIGHT_GRAY)
    val_cell.alignment = Alignment(horizontal="center", vertical="center")
    if fmt:
        val_cell.number_format = fmt

# --- Chart 1: WAU trend (native LineChart, sourced from Metric_Calculations!tbl_Weekly) ---
line_chart = LineChart()
line_chart.title = "Weekly Active Users — 24-Week Rollout (synthetic)"
line_chart.style = 2
line_chart.y_axis.title = "WAU"
line_chart.x_axis.title = "Week"
mc_ws = wb["Metric_Calculations"]
wau_values_ref = Reference(mc_ws, min_col=weekly_start_col + 2, min_row=weekly_start_row, max_row=w_r1)
wau_cats_ref = Reference(mc_ws, min_col=weekly_start_col, min_row=weekly_start_row + 1, max_row=w_r1)
line_chart.add_data(wau_values_ref, titles_from_data=True)
line_chart.set_categories(wau_cats_ref)
line_chart.width = 18
line_chart.height = 9
ws.add_chart(line_chart, "B11")

# --- Chart 2: Activation rate by business unit (native BarChart) ---
bar_chart = BarChart()
bar_chart.type = "bar"
bar_chart.title = "Activation Rate by Business Unit (synthetic)"
bar_chart.y_axis.title = "Business Unit"
bar_chart.x_axis.title = "Activation Rate"
act_values_ref = Reference(mc_ws, min_col=bu_start_col + 3, min_row=bu_start_row, max_row=bu_end_row)
act_cats_ref = Reference(mc_ws, min_col=bu_start_col, min_row=bu_start_row + 1, max_row=bu_end_row)
bar_chart.add_data(act_values_ref, titles_from_data=True)
bar_chart.set_categories(act_cats_ref)
bar_chart.width = 18
bar_chart.height = 9
ws.add_chart(bar_chart, "L11")

# --- Top insights / actions ---
insight_row = 30
ws.cell(row=insight_row, column=2, value="Top 3 Insights (synthetic — associations, not causal claims)").font = Font(name=FONT_NAME, size=12, bold=True, color=NAVY)
for i, text in enumerate(TOP_INSIGHTS):
    cell = ws.cell(row=insight_row + 1 + i, column=2, value=f"{i + 1}. {text}")
    cell.font = BODY_FONT
    cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=insight_row + 1 + i, start_column=2, end_row=insight_row + 1 + i, end_column=11)
    ws.row_dimensions[insight_row + 1 + i].height = 30

action_row = insight_row + 1 + len(TOP_INSIGHTS) + 2
ws.cell(row=action_row, column=2, value="Top 3 Recommended Actions").font = Font(name=FONT_NAME, size=12, bold=True, color=NAVY)
action_header_row = action_row + 1
for j, h in enumerate(["Segment", "Recommended Action", "Owner", "Expected Measurement"]):
    cell = ws.cell(row=action_header_row, column=2 + j, value=h)
    cell.font = HEADER_FONT
    cell.fill = HEADER_FILL
for i, (segment, action, owner, measure) in enumerate(TOP_ACTIONS):
    r = action_header_row + 1 + i
    for j, val in enumerate([segment, action, owner, measure]):
        cell = ws.cell(row=r, column=2 + j, value=val)
        cell.font = BODY_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[r].height = 30
for j, w in enumerate([20, 55, 16, 30]):
    ws.column_dimensions[get_column_letter(2 + j)].width = w

# Print setup: make this genuinely a one-page landscape printable readout.
ws.page_setup.orientation = "landscape"
ws.page_setup.fitToWidth = 1
ws.page_setup.fitToHeight = 1
ws.sheet_properties.pageSetUpPr.fitToPage = True
last_print_row = action_header_row + 1 + len(TOP_ACTIONS)
ws.print_area = f"A1:P{last_print_row}"

print("Weekly_Readout written.")


# ---------------------------------------------------------------------------
# 8. Metric_Dictionary
# ---------------------------------------------------------------------------
ws = wb.create_sheet("Metric_Dictionary")
ws["B1"] = "Metric_Dictionary"
ws["B1"].font = TITLE_FONT
ws["B2"] = "Full definitions with worked examples: docs/metric_dictionary.md"
ws["B2"].font = SUBTITLE_FONT
metric_df = pd.DataFrame(METRIC_DICT_ROWS, columns=["Metric", "Numerator", "Denominator", "Timeframe", "Purpose", "Caveat"])
write_df_as_table(ws, metric_df, start_row=4, start_col=2, table_name="tbl_MetricDict")
for row in ws.iter_rows(min_row=5, max_row=4 + len(metric_df), min_col=2, max_col=7):
    for cell in row:
        cell.alignment = Alignment(wrap_text=True, vertical="top")
ws.column_dimensions["C"].width = 45
ws.column_dimensions["D"].width = 30
ws.column_dimensions["G"].width = 45
ws.sheet_view.showGridLines = False

print("Metric_Dictionary written.")

# ---------------------------------------------------------------------------
# 9. Sheet order + save
# ---------------------------------------------------------------------------
order = [
    "README", "Raw_Events", "Clean_Events", "Users", "Data_Quality_Log",
    "Metric_Calculations", "Pivot_Weekly_Adoption", "Pivot_Feature_Usage",
    "Pivot_Barriers", "Weekly_Readout", "Metric_Dictionary",
]
wb._sheets = [wb[name] for name in order]
wb.active = 0

wb.save(OUT_PATH)
print(f"Final save -> {OUT_PATH}")
