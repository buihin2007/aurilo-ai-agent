# Aurilo AI Agent

Aurilo AI Agent supports monthly Financial and Management Reporting by reading reporting files, checking the data, calculating key variances, identifying important drivers, and preparing draft management commentary for review.

The agent is designed to help finance users prepare monthly Business Review material faster while keeping every output traceable to the original source data.

## Project Status

**Prototype — early build.** Most of this README describes the *target* design. Only part of the pipeline runs today. Steps marked _(target design)_ below are not yet implemented.

**Working today:**

- `scripts/translate.py` — Finnish → English label translation. Checks `docs/glossary_finnish_english.xlsx` first (verified terms), falls back to Google Translate for the rest, and writes a `*_translated.xlsx` copy. _Note: the translation logic is implemented, but the script has no command-line entry point yet — `translate_file()` must be called manually. Running `python scripts/translate.py` currently does nothing on its own._
- `scripts/ingest_ITDS.py` — parses the ITDS file's `closing_PnL` sheet and writes `output/variance.json`. This file currently holds **raw figures only** (Actual / Budget / Last Year / Prior Forecast for month, YTD, and FY26). No variances, materiality flags, or source-cell references are computed yet, and column/row positions are hardcoded rather than scanned.

**Not built yet _(target design)_:** data validation, the variance calculation itself, insight selection, commentary drafting, PPTX export, the `run_monthly_report.py` orchestrator, and the Managed Services / Group ingest scripts.

> Known inconsistency: this README uses the period format `2026-05` (year-month, sortable). The current code emits `05-2026`. These will be reconciled to `2026-05`.

## What The Agent Does

- Reads monthly financial reporting Excel files.
- Checks whether required data is present and usable.
- Calculates Actual vs Budget, Actual vs Forecast, and Actual vs Last Year variances.
- Highlights material deviations and possible reporting risks.
- Produces draft management commentary.
- Shows the source data behind each figure and conclusion.
- Exports report-ready outputs for finance review.

The agent does not replace finance review. All commentary and outputs should be checked and approved by a responsible finance user before use in management reporting.

## Monthly User Workflow

### 1. Prepare The Input Files

Collect the monthly reporting files for the relevant reporting period.

Typical input files include:

- ITDS P&L Excel file
- Managed Services P&L Excel file
- Group management reporting Excel file
- previous Business Review material, if used for style or comparison

Use the latest approved files from the monthly reporting process. Do not use unfinished or unapproved working files unless the output is clearly treated as a draft.

### 2. Add Files To The Agent

Place the input files in the local input folder:

```text
data/
```

The agent reads files from this folder when the monthly workflow is run.

### 3. Run The Monthly Report Workflow

**Today** the pipeline runs as individual scripts, in order. Only translation and ITDS ingest are implemented:

```bash
# 1. Translate Finnish labels → *_translated.xlsx
#    (logic only — no CLI entry point yet; call translate_file() manually)

# 2. Parse the ITDS closing_PnL sheet → output/variance.json (raw figures only)
python scripts/ingest_ITDS.py
```

`ingest_ITDS.py` has no arguments — the input filename, sheet, and period are fixed inside the script. It reads `data/copy ITDS_PnL_officeConnect_1.1.xlsx` and overwrites `output/variance.json` on each run.

**Target design** — a single orchestrator runs the full pipeline for a chosen month and business unit:

```bash
python scripts/run_monthly_report.py --period 2026-05 --business-unit ITDS
```

```text
read input files
check data quality
calculate variances
select key insights
draft commentary
prepare output files
```

_The orchestrator, and every step after ingest, are not yet built._

### 4. Review Data Checks

Before using the commentary, review the validation result.

The agent should show whether:

- required P&L lines were found
- required Actual, Budget, Forecast, and Last Year values are present
- source references are available
- unusual values were detected
- any data issues block commentary generation

If validation fails, fix the input file or confirm the issue with the responsible finance owner before continuing.

### 5. Review Variance Analysis

**Today** `output/variance.json` contains **raw figures only** — for each P&L line, the Actual / Budget / Last Year / Prior Forecast values across month, YTD, and FY26, plus `source_sheet` and `source_row`. Despite the filename, no variances are calculated yet. You can eyeball Actual vs Budget by hand, but the agent does not compute or flag anything.

**Target design** _(not yet built)_ — the variance step should show, per line:

- Actual vs Budget variance
- Actual vs Forecast variance
- Actual vs Last Year variance
- absolute variance
- percentage variance
- materiality flag
- source cell reference

Use this step to confirm that the agent has identified the correct key movements for the month.

### 6. Review Key Insights

The agent selects the most important drivers from the variance analysis.

Typical insights include:

- largest negative drivers
- largest positive drivers
- material changes in Revenue, Gross Margin, EBITDA, or BU Profit
- unusual movements
- items requiring human explanation

The finance user should confirm whether the selected insights match the business reality of the month.

### 7. Review Draft Commentary

The agent prepares a draft commentary based on the selected insights.

The commentary should be reviewed for:

- factual correctness
- business context
- tone and wording
- missing explanations
- unnecessary or misleading statements

Each commentary point should be supported by source figures. If a statement cannot be traced to data or known business context, it should be edited or removed.

### 8. Edit And Approve

The finance user edits the draft commentary where needed.

Common edits may include:

- adding business reasons behind a variance
- correcting terminology
- shortening commentary for executive reporting
- adding context from sales, operations, or service owners
- removing low-confidence explanations

The final version should be approved by the responsible finance user before being used in Business Review material.

### 9. Export Outputs

After review, export the reporting outputs.

**Today** the pipeline produces exactly one file, overwritten each run:

```text
output/variance.json          # ITDS only, raw figures — see §5
```

**Target design** _(not yet built)_ — per-period, per-business-unit outputs:

```text
output/<period>_<business_unit>_variance.json
output/<period>_<business_unit>_insights.json
output/<period>_<business_unit>_commentary.md
output/<period>_<business_unit>_trace_table.csv
output/<period>_<business_unit>_business_review.pptx
```

The exact output depends on the enabled workflow.

## How To Read The Outputs

### Variance File

The variance file contains calculated differences between Actuals and comparison values such as Budget, Forecast, and Last Year.

Use it to verify the numbers behind the commentary.

### Insights File

The insights file contains the most important selected drivers for the reporting period.

Use it to understand what the agent considered material.

### Commentary File

The commentary file contains draft management text.

Use it as a starting point for the Business Review narrative.

### Trace Table

The trace table links figures and conclusions back to the source file, sheet, row, and cell.

Use it to audit where the numbers came from.

### PowerPoint Output

If PowerPoint export is enabled, the agent prepares a draft Business Review presentation.

Review the presentation before sharing it with management.

## Data Safety

Financial reporting data is confidential.

Do not commit the following files to GitHub:

- Excel reporting files
- PowerPoint reporting files
- exported reports containing real financial data
- `.env` files
- API keys
- client financial data

Use local folders for input and output files. Share exported reports only through approved Aurilo channels.

## Important Notes

- The agent creates draft outputs, not final approved reports.
- The finance user remains responsible for reviewing and approving all commentary.
- The agent should not invent explanations that are not supported by data or known business context.
- If data validation fails, the workflow should stop until the issue is resolved.
- Every financial figure used in commentary should be traceable to a source file.
