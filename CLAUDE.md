# Aurilo AI Agent — Project Context

## What this project is

An AI agent that automates monthly financial commentary for Aurilo Group (Finnish IT company — Tietokeskus/Enfo brands). The agent reads Excel exports from Workday Adaptive Planning, calculates variances, generates English commentary via LLM, and produces a draft Business Review PPTX.

**Stack:** Python (data processing) + n8n (orchestration + AI agents) + ChromaDB (RAG) + python-pptx (report output)
**Scope:** Prototype only — runs locally on tech lead's laptop, not production-ready
**Data:** Real Aurilo data, processed locally. Only aggregated figures sent to LLM API.

---

## Repository structure

```
aurilo-ai-agent/
├── data/               ← Aurilo Excel files (gitignored — never commit)
├── scripts/
│   ├── ingest.py       ← Excel parser (openpyxl, cell-by-cell)
│   └── variance.py     ← Variance engine (deterministic arithmetic)
├── output/             ← variance.json output
├── docs/               ← Reference markdown files (guides, policy, template)
├── .claude/commands/   ← Custom Claude Code slash commands
├── .env                ← API keys (gitignored)
├── .gitignore
├── requirements.txt
└── CLAUDE.md           ← This file
```

---

## Input files (in `data/` — never commit to git)

| File | Business unit | Key sheets |
|---|---|---|
| `ITDS_PnL_officeConnect_1.1.xlsx` | IT Delivery Services | `closing_PnL`, `brKPIdashboard`, `monthlyActuals`, `masterDataSheet` |
| `MS P&L - Office Connect.xlsx` | Managed Services | equivalent sheets — verify on first open |
| `Management report...xlsx` | Group level | P&L + balance sheet + cash flow |

**Always open with `data_only=True`:**
```python
wb = openpyxl.load_workbook("data/ITDS_PnL_officeConnect_1.1.xlsx", data_only=True)
```

---

## Core data model

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class PnLLine:
    name: str               # English label (translated from Finnish)
    name_fi: str            # Original Finnish label from file
    account_code: str       # Column A value
    actual: Optional[float]
    budget: Optional[float]
    ly: Optional[float]     # Last Year actual
    fct: Optional[float]    # Previous Forecast
    ytd_actual: Optional[float]
    ytd_budget: Optional[float]
    fy_fct: Optional[float]
    fy_budget: Optional[float]
    source_sheet: str       # e.g. "closing_PnL"
    source_row: int         # Excel row number
    source_col_actual: str  # Column letter for Actual, e.g. "C"
```

Every figure carries its source cell reference (e.g. `closing_PnL!C10`). This is non-negotiable — it enables the full audit trail.

---

## `closing_PnL` column layout (ITDS)

Scan for the header row — do not hardcode row number. The header row is the first row where column 3 contains "Actual" or "Toteuma".

| Column index | Content |
|---|---|
| 1 (A) | Account code |
| 2 (B) | Finnish label |
| 3 (C) | Actual (current month) |
| 4 (D) | Budget |
| 5 (E) | Previous Forecast |
| 6 (F) | Last Year Actual |
| 7 (G) | YTD Actual |
| 8 (H) | YTD Budget |
| 9 (I) | FY Forecast |
| 10 (J) | FY Budget |

**Verify these on first open** — OfficeConnect occasionally shifts columns by 1–2 positions.

---

## Key Finnish → English labels

| Finnish | English |
|---|---|
| Liikevaihto | Net Revenue |
| Myyntikate | Gross Profit |
| Henkilöstökulut | Personnel Costs |
| Käyttökate | EBITDA |
| Poistot | Depreciation & Amortisation |
| Liiketulos | Operating Profit (EBIT) |

Full glossary: `docs/glossary_finnish_english.xlsx`

---

## Variance engine rules

Three comparisons per P&L line:

```python
vs_budget_abs = actual - budget
vs_budget_pct = (actual - budget) / abs(budget) if budget else None

vs_ly_abs = actual - ly
vs_ly_pct = (actual - ly) / abs(ly) if ly else None

vs_fct_abs = actual - fct
vs_fct_pct = (actual - fct) / abs(fct) if fct else None
```

A line is **flagged** if: `abs(vs_budget_abs) > 100_000 AND abs(vs_budget_pct) > 0.05`
(Both thresholds must be breached simultaneously — confirm exact values with Aurilo.)

---

## Validation rules (run before variance engine)

Stop the pipeline and raise an exception if:
- Any of Actual / Budget / LY is missing on a material P&L line
- Column C header does not match the expected closing month
- BU totals do not reconcile to Group total within €10k tolerance
- Any single line shows Actual > 10× prior month Actual

---

## Output format (`variance.json`)

```json
{
  "period": "2026-03",
  "business_unit": "ITDS",
  "lines": [
    {
      "name": "Net Revenue",
      "name_fi": "Liikevaihto",
      "account_code": "4100",
      "actual": 4821000,
      "budget": 5100000,
      "ly": 4650000,
      "fct": 4900000,
      "vs_budget_abs": -279000,
      "vs_budget_pct": -0.0547,
      "vs_ly_abs": 171000,
      "vs_ly_pct": 0.0368,
      "vs_fct_abs": -79000,
      "vs_fct_pct": -0.0161,
      "flagged": true,
      "source_cell": "closing_PnL!C10"
    }
  ]
}
```

---

## Build order

1. `scripts/ingest.py` — parser for `closing_PnL` (start here)
2. `scripts/ingest.py` — extend to `masterDataSheet`
3. `scripts/variance.py` — variance engine consuming ingest output
4. Validation layer — add to ingest.py before variance runs
5. MS parser — reuse ingest.py with adjusted sheet names
6. Group parser — add balance sheet and cross-BU reconciliation

---

## What NOT to do

- Do not use `pandas` for parsing — it loses cell coordinates. Use `openpyxl` cell-by-cell.
- Do not open the file without `data_only=True` — formula strings instead of values.
- Do not commit anything in `data/` to git.
- Do not send raw Finnish labels or customer names to the LLM API.
- Do not hardcode column positions — always scan for the header row first.

---

## Reference docs (in `docs/`)

| File | Purpose |
|---|---|
| `itds_excel_guide.md` | Detailed ITDS sheet inventory, column mapping, parsing pitfalls |
| `ms_group_excel_guide.md` | MS and Group file structure (needs verification) |
| `financial_policy.md` | Variance thresholds, commentary standards, Finnish glossary |
| `business_review_template.md` | PPTX slide structure and placeholder map |
| `system_architecture.md` | Full 6-component architecture |
| `data_pipeline.md` | Non-AI pipeline steps (Steps 1–4) |
| `project_plan_aurilo_ai_agent.md` | 10-week project plan, milestones, team roles |
