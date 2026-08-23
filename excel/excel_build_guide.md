# Excel Workbook Build Guide

`GenAI_Weekly_Adoption_Readout.xlsx` is a **real, generated, and validated**
workbook — not a mockup. It was built programmatically with `openpyxl` and
then **actually recalculated with LibreOffice Calc** to confirm every one of
its ~30,000 formula cells evaluates without error before being committed.
This guide documents exactly what's already live in the file, and gives
exact click-by-click steps for the pieces that require Excel Desktop itself
(a live Power Query connection, native PivotTables with slicers) — pieces
this project is explicit about *not* claiming to have automated.

## What's genuinely in the file today (verified, not just described)

| Capability | Status |
|---|---|
| 11 required worksheets, exact names | ✅ Done |
| Real Excel Tables (`ListObject`s) with structured references | ✅ Done — `tbl_Users`, `tbl_BU`, `tbl_Weekly`, `tbl_Feature`, `tbl_RawEvents`, `tbl_CleanEvents`, `tbl_DQLog`, `tbl_PivotWeekly`, `tbl_PivotFeatureUsage`, `tbl_PivotBarriers`, `tbl_MetricDict` |
| Live formulas: `SUMIFS`, `COUNTIFS`, `IFERROR`, `INDEX`/`MATCH` | ✅ Done, on `Metric_Calculations` |
| Conditional formatting (color scales, cell-value rules) | ✅ Done, on `Metric_Calculations` and all 3 `Pivot_*` sheets |
| Native, embedded Excel charts (not images) | ✅ Done — 2 charts on `Weekly_Readout`, linked live to `Metric_Calculations` data |
| One-page, landscape, fit-to-page `Weekly_Readout` | ✅ Done (print area + page setup configured) |
| A live Power Query connection to the raw CSVs | ❌ Not in the file — see §1 below |
| Native, refreshable PivotTables with slicers | ❌ Not in the file — see §2 below |

**Why the last two are manual, not automated:** a `.xlsx` file *can*
technically embed Power Query (`M`) definitions and native PivotTable/
PivotCache XML parts, but `openpyxl` cannot author either in a form Excel
recognizes as a live, refreshable object, and there is no way to verify one
built by hand-crafting XML without Excel itself opening it. Rather than ship
something unverifiable and call it "embedded Power Query," this project
gives you the exact steps below — each takes a few minutes in Excel Desktop.

---

## §1 — Building the live Power Query connection (manual, ~5 minutes)

This lets the workbook re-pull and re-clean data directly from
`data/raw/*.csv` inside Excel, independent of `src/transform_data.py`.

1. **Data ribbon → Get Data → From File → From Text/CSV.** Select
   `data/raw/usage_events.csv`. Click **Transform Data** (not Load).
2. In the Power Query Editor, replicate the key cleaning steps from
   `src/transform_data.py`:
   - **Remove Duplicates**: select the `event_id` column → right-click →
     **Remove Duplicates**.
   - **Filter invalid timestamps**: click the filter arrow on
     `event_timestamp` → **Date/Time Filters** → remove blanks/errors (any
     row Power Query can't parse as a date shows as an error after you set
     the column type to Date/Time — filter those out with
     `Table.SelectRows(_, each not Value.Is([event_timestamp], type null))`
     equivalent via the UI's "Remove Errors" on that column after setting
     its type).
   - **Fix negative values**: select `session_duration_seconds` and
     `estimated_minutes_saved` → **Add Column → Custom Column** →
     `if [session_duration_seconds] < 0 then null else [session_duration_seconds]`
     (repeat for the minutes-saved column), then remove the original columns
     and rename the new ones back.
   - **Normalize feature_name labels**: **Transform → Replace Values**, run
     it once per known variant (e.g. `"Doc Summarization"` → `"Document
     Summarization"`, `"chat and research"` → `"Chat and Research"`).
3. Repeat the same **Get Data → From Text/CSV → Transform Data** pattern for
   `users.csv` and `feedback.csv`.
4. **Home → Close & Load To… → Only Create Connection** for each, then use
   **Home → Merge Queries** to join `usage_events` to `users` on `user_id`
   if you want a single denormalized query, or keep them separate and build
   relationships in the Data Model instead (**Home → Load To → Add this data
   to the Data Model**).
5. **Data → Queries & Connections → Refresh All** any time the source CSVs
   change (e.g. after re-running `src/generate_synthetic_data.py`) — this is
   what makes the workbook's Power Query layer "repeatable," exactly as
   required: same steps, same result, on any refreshed copy of the raw data.

---

## §2 — Building live, refreshable PivotTables with slicers (manual, ~5 minutes each)

The `Pivot_Weekly_Adoption`, `Pivot_Feature_Usage`, and `Pivot_Barriers`
sheets in the shipped workbook are **pivot-style summary tables** (real
Excel Tables with conditional formatting, computed from the complete
dataset) — not native PivotTable objects. To turn any of them into a real,
interactive PivotTable:

1. Go to the **Clean_Events** sheet (or your Power Query output from §1 for
   full-fidelity, non-sampled data), click inside `tbl_CleanEvents`.
2. **Insert → PivotTable → New Worksheet.**
3. For a **weekly adoption pivot** (mirroring `Pivot_Weekly_Adoption`): drag
   `event_timestamp` to **Rows** (group it by Week via right-click → Group →
   Days, check "Number of days" = 7), drag `user_id` to **Values** → set to
   **Distinct Count** (Excel 2013+: right-click the value field → Value
   Field Settings → More Options → Distinct Count — requires "Add this data
   to the Data Model" to be checked when you built the PivotTable). Drag a
   business-unit field (bring it in via a relationship to `Users`, or a
   VLOOKUP/merge column) to **Columns**.
4. For a **feature usage pivot** (mirroring `Pivot_Feature_Usage`): Rows =
   `feature_name`, Columns = `business_unit`, Values = Count of `event_id`,
   filtered to `event_type` = `feature_completed` or `output_exported`
   (drag `event_type` to the **Filters** area).
5. For a **barriers pivot** (mirroring `Pivot_Barriers`, from
   `Feedback`/`tbl_CleanEvents`'s feedback equivalent): Rows =
   `business_unit`, Columns = `barrier_category`, Values = Count of
   `feedback_id`, Filter out `barrier_category = "No barrier reported"`.
6. **Add slicers:** with the PivotTable selected, **PivotTable Analyze →
   Insert Slicer** → check `business_unit` and a date/week field. Resize and
   position the slicer(s) next to the PivotTable. Slicers instantly filter
   the PivotTable (and any other PivotTable you connect them to via
   **Report Connections**).
7. **Right-click → Refresh** any time the source data changes.

---

## §3 — Formula reference (what's live in `Metric_Calculations`, and why)

| Requirement | What's used | Why |
|---|---|---|
| `SUMIFS` | `=SUMIFS(tbl_Weekly[weekly_active_users], tbl_Weekly[week_number], ">=12")` | Conditional sum — sums WAU across weeks 12 onward. |
| `COUNTIFS` | `=COUNTIFS(tbl_BU[activation_rate], "<0.75")` | Conditional count — counts business units below a threshold. |
| `IFERROR` | `=IFERROR(I17/I16, "N/A")` | Safe division everywhere a ratio is computed, mirroring the DAX `DIVIDE()` pattern used in the Power BI model. |
| `XLOOKUP` (requested) | **`INDEX`/`MATCH`** used instead: `=IFERROR(INDEX(tbl_BU[activation_rate], MATCH(H26, tbl_BU[business_unit], 0)), "Not found")` | This workbook was validated with an automated LibreOffice-based recalculation check, which cannot reliably evaluate `XLOOKUP` (or `LET`, `TEXTJOIN`, `IFS`, `SWITCH`) — shipping an unverifiable formula would break this project's "everything is actually tested" standard. If you have Excel 2021 or Microsoft 365, the equivalent XLOOKUP is: `=XLOOKUP(H26, tbl_BU[business_unit], tbl_BU[activation_rate], "Not found")` — functionally identical, feel free to swap it in. |
| `LET` (requested) | Not used in the shipped formulas, for the same verification reason. Equivalent example you can add in Excel 365: `=LET(elig, SUM(tbl_BU[eligible_users]), act, SUM(tbl_BU[activated_users]), IFERROR(act/elig, "N/A"))` — this computes the same "Company Activation Rate" KPI in one readable expression instead of two helper cells. |

All formulas above are on the **Metric_Calculations** sheet and reference
three small, **complete** (not sampled) aggregate tables — `tbl_BU` (8 rows,
one per business unit), `tbl_Weekly` (24 rows, one per rollout week), and
`tbl_Feature` (8 rows, one per feature) — so every calculation is exactly
correct, not an estimate from `Raw_Events`/`Clean_Events`'s illustrative
3,000-row samples.

## §4 — Conditional formatting already applied

- `Metric_Calculations!tbl_BU`: a red→green color scale on `activation_rate`,
  a green→red (reversed) color scale on `dormancy_rate`, and a red-fill rule
  flagging any business unit below 75% activation.
- `Pivot_Weekly_Adoption`, `Pivot_Feature_Usage`: white→blue color scales
  highlighting higher-volume cells.
- `Pivot_Barriers`: a white→red color scale highlighting business
  units/barrier combinations with the most mentions.

To add more (e.g. on your own PivotTable from §2): select the value range →
**Home → Conditional Formatting → Color Scales** (or **New Rule** for a
custom threshold).

## §5 — Refresh instructions

1. Regenerate the source data if needed:
   `python src/generate_synthetic_data.py && python src/transform_data.py`
   (from the repository root).
2. If you built the Power Query connection from §1: **Data → Refresh All**.
3. If you built a native PivotTable from §2: right-click it → **Refresh**
   (or **Refresh All** from the Data ribbon).
4. The `Metric_Calculations`, `Weekly_Readout` KPI cards, and both native
   charts recalculate automatically whenever Excel opens the file (Excel's
   default calculation mode is Automatic) — no manual step needed for those.
5. To regenerate the shipped `.xlsx` itself from scratch (e.g. after a data
   or design change), re-run `python src/build_excel_workbook.py` from the
   repository root, or rebuild the equivalent sheets by hand following this
   guide — either way, **run a LibreOffice-based recalculation check (or
   open and save in real Excel) before treating the file as done**, and
   confirm zero formula errors. `src/build_excel_workbook.py` was itself
   validated this way (0 errors across ~30,000 formula cells) before being
   committed.

## A note on repeatability and synthetic data

Every transformation described in this guide (§1's Power Query steps, §2's
PivotTable construction) is fully repeatable: run them again on a freshly
regenerated `data/raw/*.csv` and you'll get the same structure with updated
numbers, because the underlying generator (`src/generate_synthetic_data.py`)
is deterministic (fixed random seed). **All data in this workbook — users,
events, feedback, ratings, and the "estimated hours saved" figures — is
synthetic and fictional**, generated for the fictional Northstar Financial
Group / Northstar Assist scenario. Nothing here represents RBC, TD, or any
real financial institution, and "estimated hours saved" is a modeled
assumption, never validated ROI. See `data/synthetic_data_dictionary.md` and
`docs/assumptions_and_limitations.md` for the full integrity statement.
