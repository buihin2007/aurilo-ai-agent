# MVP Build Plan

This document describes the first practical build plan for the Aurilo AI Agent prototype.

The first MVP should focus on one complete workflow for the ITDS Excel file before expanding to Managed Services, Group reporting, RAG, PPTX generation, or UI work.

## Target MVP Workflow

```text
ITDS Excel
-> raw JSON
-> validation result
-> variance JSON
-> insights JSON
-> commentary Markdown
```

The goal is to prove that the agent can read a real Aurilo financial workbook, calculate reliable variances, identify the most important drivers, and produce a traceable commentary draft.

## Phase 1: Map The ITDS Excel Structure

### Purpose

Before writing more code, the team needs a clear map of the ITDS workbook. Excel is not a stable database, so the parser must be based on a known sheet, row, and column structure.

### What To Do

- Identify the input workbook used for the first MVP.
- Confirm the target sheet, currently expected to be `masterDataSheet`.
- Confirm which rows contain valid P&L lines or reporting labels.
- Confirm which rows should be skipped, such as empty rows, headers, helper rows, and percentage-only rows.
- Confirm how the sheet separates Actual, Budget, Last Year, and Prior Forecast data.
- Confirm how month columns are identified inside each scenario block.
- Confirm how the reporting period is identified.

### Expected Documentation Output

Create:

```text
docs/itds_data_map.md
```

Suggested content:

```text
Input file:
data/copy ITDS_PnL_officeConnect_1.1.xlsx

Sheet:
masterDataSheet

Rows and labels:
Identify the rows for required reporting lines such as Revenue, Gross Margin, EBITDA, BU Profit, PCaaS, Hardware, Software, Personnel Costs, and other material P&L items.
Skip empty rows, helper rows, headers, and rows that only contain percentages or ratios unless they are explicitly needed.

Columns:
Document how to find the target month inside each scenario block:
- Actual
- Budget
- Last Year
- Prior Forecast

For each required line, document the source cells used for:
- target month Actual
- target month Budget
- target month Last Year
- target month Prior Forecast
- YTD Actual
- YTD Budget
- FY Forecast / Actual
- FY Budget
```

### Done When

- The team knows exactly what the first parser should read.
- The mapping is documented in `docs/itds_data_map.md`.
- Any assumptions about rows, columns, and period handling are written down.

## Phase 2: Ingest ITDS Excel To Raw JSON

### Purpose

Convert the ITDS Excel sheet into a clean JSON format that later scripts can use. This phase should only extract data. It should not calculate variance or generate commentary.

### What To Build

Update or replace:

```text
scripts/ingest_ITDS.py
```

The script should:

- Open the ITDS workbook with `openpyxl` and `data_only=True`.
- Read the `masterDataSheet` sheet.
- Extract each valid P&L line.
- Extract Month, YTD, and FY values.
- Store each financial value together with its source cell reference.
- Write structured JSON to `output/`.

### Expected File Output

Create:

```text
output/itds_2026_05_raw.json
```

Example structure:

```json
{
  "period": "2026-05",
  "business_unit": "ITDS",
  "source_file": "copy ITDS_PnL_officeConnect_1.1.xlsx",
  "source_sheet": "masterDataSheet",
  "lines": [
    {
      "name": "Hardware, one-off",
      "source_row": 8,
      "month_actual": {
        "value": 8495869.04,
        "source_cell": "masterDataSheet!F4"
      },
      "month_budget": {
        "value": 8802785.24,
        "source_cell": "masterDataSheet!R4"
      }
    }
  ]
}
```

### Done When

- Running `python scripts/ingest_ITDS.py` creates a raw JSON file.
- Each extracted number includes both `value` and `source_cell`.
- The output contains no commentary and no calculated variance yet.

## Phase 3: Validate The Raw Data

### Purpose

Check whether the extracted data is trustworthy enough for variance calculation and commentary generation. If validation fails, the pipeline should stop before producing commentary.

### What To Build

Create:

```text
scripts/validate.py
```

The script should read:

```text
output/itds_2026_05_raw.json
```

It should check:

- Required P&L lines were found.
- Required values are not missing.
- Financial values are numeric.
- Source cell references exist.
- The reporting period is present.
- Obvious anomalies are flagged as warnings.

First-pass required lines can include:

```text
Revenue
Gross Margin
BU Profit
```

The exact labels should be adjusted to match the ITDS workbook.

### Expected File Output

Create:

```text
output/itds_2026_05_validation.json
```

Example passed result:

```json
{
  "status": "passed",
  "errors": [],
  "warnings": []
}
```

Example failed result:

```json
{
  "status": "failed",
  "errors": [
    "Missing month_budget for Gross Margin",
    "Missing source_cell for Revenue month_actual"
  ],
  "warnings": []
}
```

### Done When

- Running `python scripts/validate.py` creates a validation result file.
- Errors and warnings are clearly separated.
- Commentary generation is treated as blocked if validation status is `failed`.

## Phase 4: Calculate Variances

### Purpose

Calculate financial variances deterministically in Python. LLMs must not calculate financial figures.

### What To Build

Create:

```text
scripts/variance.py
```

The script should read:

```text
output/itds_2026_05_raw.json
```

It should calculate:

- Month Actual vs Month Budget
- Month Actual vs Month Last Year
- Month Actual vs Month Prior Forecast
- YTD Actual vs YTD Budget
- YTD Actual vs YTD Last Year
- YTD Actual vs YTD Prior Forecast
- FY Actual / Forecast vs FY Budget

For each comparison, calculate:

```text
absolute variance = actual - comparison_value
percentage variance = absolute variance / abs(comparison_value)
```

The first materiality rule can be:

```text
flagged = abs(variance_abs) > 100000 and abs(variance_pct) > 0.05
```

This threshold should later be confirmed with Aurilo stakeholders.

### Expected File Output

Create:

```text
output/itds_2026_05_variance.json
```

Example structure:

```json
{
  "period": "2026-05",
  "business_unit": "ITDS",
  "lines": [
    {
      "name": "Hardware, one-off",
      "month_actual": 8495869.04,
      "month_budget": 8802785.24,
      "vs_budget_abs": -306916.2,
      "vs_budget_pct": -0.0349,
      "vs_budget_flagged": false,
      "sources": {
        "month_actual": "masterDataSheet!F4",
        "month_budget": "masterDataSheet!R4"
      }
    }
  ]
}
```

### Done When

- Running `python scripts/variance.py` creates a variance JSON file.
- Every calculated variance is based on values from the raw JSON.
- Source cell references are preserved in the output.
- The script does not call an LLM.

## Phase 5: Select Key Insights

### Purpose

Select the most important facts from the variance output. This phase decides what is worth mentioning in management commentary.

Variance calculation answers:

```text
What changed?
```

Insight selection answers:

```text
What matters most?
```

Commentary generation answers:

```text
How should we explain it clearly?
```

### What To Build

Create:

```text
scripts/insights.py
```

The script should read:

```text
output/itds_2026_05_variance.json
```

It should select:

- Largest negative variances.
- Largest positive variances.
- Flagged material variances.
- Core metrics such as Revenue, Gross Margin, and BU Profit.
- Offsetting drivers where a negative variance is partly balanced by a positive one.

The first version can be rule-based. No LLM is required.

### Expected File Output

Create:

```text
output/itds_2026_05_insights.json
```

Example structure:

```json
{
  "period": "2026-05",
  "business_unit": "ITDS",
  "key_insights": [
    {
      "type": "negative_driver",
      "line": "Hardware, one-off",
      "comparison": "vs_budget",
      "variance_abs": -306916.2,
      "variance_pct": -0.0349,
      "source_cells": ["masterDataSheet!F4", "masterDataSheet!R4"]
    },
    {
      "type": "positive_offset",
      "line": "HWRS, Continuous services",
      "comparison": "vs_budget",
      "variance_abs": 69192.03,
      "variance_pct": 0.4245,
      "source_cells": ["masterDataSheet!F6", "masterDataSheet!R6"]
    }
  ]
}
```

### Done When

- Running `python scripts/insights.py` creates an insights JSON file.
- The file contains a small number of important findings, not every P&L line.
- Each insight includes evidence and source cells.

## Phase 6: Generate Commentary Draft

### Purpose

Generate a first-draft management commentary from the selected insights. The commentary should be traceable and reviewable by finance users.

### What To Build

Create:

```text
scripts/commentary.py
```

The script should read:

```text
output/itds_2026_05_insights.json
```

The first version should use a deterministic template. An LLM can be added later once the data pipeline is stable.

### Expected File Output

Create:

```text
output/itds_2026_05_commentary.md
```

Example structure:

```markdown
# ITDS Commentary Draft - 2026-05

## Draft Commentary

In May 2026, ITDS performance was mainly affected by weaker Hardware one-off sales. Hardware one-off was EUR 0.31M below budget. This was partly offset by stronger HWRS Continuous services.

## Evidence

- Hardware, one-off: Actual EUR 8.50M vs Budget EUR 8.80M, variance EUR -0.31M, source cells masterDataSheet!F4 and masterDataSheet!R4.
- HWRS, Continuous services: Actual EUR 0.23M vs Budget EUR 0.16M, variance EUR +0.07M, source cells masterDataSheet!F6 and masterDataSheet!R6.

## Review Notes

- This is a draft for finance review.
- Business reasons should be confirmed by the responsible controller.
- AI or template-generated commentary must not be published without human approval.
```

### Done When

- Running `python scripts/commentary.py` creates a readable Markdown commentary draft.
- The commentary is based only on selected insights.
- The output includes an evidence section.
- The output clearly states that human review is required.

## Recommended Build Order

Implement the MVP in this exact order:

```text
1. docs/itds_data_map.md
2. scripts/ingest_ITDS.py
3. scripts/validate.py
4. scripts/variance.py
5. scripts/insights.py
6. scripts/commentary.py
```

Do not start with RAG, n8n, PPTX generation, UI, Managed Services, or Group reporting. Those are later extensions.

## First MVP Success Criteria

The MVP is successful when the team can run:

```bash
python scripts/ingest_ITDS.py
python scripts/validate.py
python scripts/variance.py
python scripts/insights.py
python scripts/commentary.py
```

And receive:

```text
output/itds_2026_05_raw.json
output/itds_2026_05_validation.json
output/itds_2026_05_variance.json
output/itds_2026_05_insights.json
output/itds_2026_05_commentary.md
```

At that point, the project has a complete minimum workflow:

```text
Read Excel -> check data -> calculate variance -> select insights -> draft commentary
```
