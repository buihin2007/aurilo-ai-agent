# Aurilo AI Agent — Project Context

## What this project is

An AI agent that automates monthly financial commentary for Aurilo Group (Finnish IT company — Tietokeskus/Enfo brands). The agent reads Excel exports from Workday Adaptive Planning, calculates variances, and generates English commentary via LLM as a draft for Finance review. Draft delivery format (file, email, channel link — and whether it needs to be a formatted document at all) is an open question with Aurilo (see `Aurilo_Dependencies_and_Open_Questions.docx` §D); not committing to a report-generation library until that's answered.

**Stack:** Python (data processing) + n8n (orchestration + AI agents) + ChromaDB (RAG)
**Scope:** Prototype only — runs locally on tech lead's laptop (internal decision — disclosed to Aurilo in the dependency document, awaiting explicit data-policy confirmation), not production-ready
**Data:** Real Aurilo data, processed locally. Only aggregated figures sent to LLM API.

---

## ⚡ ERP migration & format v2 (June 2026) — READ THIS FIRST

In June 2026 Aurilo moved to a **new ERP**; the entire **chart of accounts changed** and all Excel exports were rebuilt on a new template ("format v2"). The old-format files (May 2026 and earlier) are **obsolete**. Everything below describes format v2 unless explicitly marked LEGACY.

**Confirmations received from Aurilo (email, 17 Jul 2026) — treat as authoritative:**

1. **FSLI renames confirmed** (same scope, just renamed — see Crosswalk below). Verified numerically: March 2026 (closed month) reconciles exactly on revenue; other lines differ only ~€1.5k (minor account reclassifications between COGS and Non-Operating Income).
2. **New CoA confirmed**: 3-digit account groups (`400 Purchases`) + 6-digit leaf GL accounts (`400000 Purchases hardware`). Build on the new codes.
3. **Operative EBITA is the line the brief §9 "EBITA > €20k" rule refers to.** At BU level, `Operative EBITA` == `Business Unit Profit` (same figure, Adaptive structure). Group-level: `Aurilo Operative EBITA = MS BU Profit + ITDS BU Profit − Group Functions BU Profit`; **OTI (One-Time Items) are excluded** from Operative EBITA.
4. **Template dialects will be unified** by Aurilo (standalone-BU dialect vs Group-workbook dialect — see Anatomy below). Until then, handle both via aliases.
5. **History is self-contained**: LY columns hold 2025 figures restated under the new CoA. Old-format files are no longer needed.
6. **BU standalone files are the source of truth** (not the Group workbook). Group workbook is currently in **thousands of euros** (will be changed to euros by Aurilo); BU files are in euros. ITDS standalone is "more accurate" (has Business Unit Profit / Direct Margin lines the Group workbook lacks).
7. **Prior FC semantics CONFIRMED** (was the long-standing ~80% open question, now closed): if reporting month is June, Prior FC holds **actuals through May** and the remaining months hold the **previous forecast**. CY holds actuals for closed months + the latest revised forecast for open months.
8. **Indentation bug in ITDS "COGS Accounts" zone acknowledged** — Aurilo may fix the template; until/unless they do, derive hierarchy from account-code structure (code-based fix is our default).
9. **Stability going forward**: no major structural changes planned; minor changes possible over time, not monthly. → Absorb minor drift via alias/profile config + fail-loud validation.

**New entities:** `Group F` = Group Functions, Aurilo's third BU (admin/support: Finance, HR, IT — expenses only). `OTI` = One-Time Items (adjustments excluded from Operative EBITA, e.g. M&A costs).

---

## Current pilot scope (3-week ITDS pilot)

Per the scope response `Aurilo_Closing_Variance_Agent_Scope_and_Dependencies.docx` (v1.0, 8 Jul 2026) and the follow-up meeting `Meeting_Notes_070726.docx`, the deliverable is the **client-defined Minimum Viable Pilot** (brief Section 15) for a **single business unit — ITDS only**.

**In scope now (ITDS pilot):**
1. One business unit — ITDS, standalone file, sheet `master` (format v2).
2. P&L **CY (Current Forecast) vs Prior FC** — the primary comparison. Semantics of both columns are **confirmed** (see ERP-migration item 7). BUD is ingested as informational (no flagging on it).
3. **Materiality thresholds from the brief §9**: absolute P&L variance > €25k, variance % > 10%, per-line rules (gross-margin €10k, expense €10k, EBITA €20k — EBITA rule applies to the `Operative EBITA` line, confirmed). OR logic — any breached rule flags the line. Output = full flagged list + highlighted top 5–10 by absolute magnitude.
4. Teams for questions and reminders (blocked on Teams bot access — dependency doc sent).
5. SharePoint List as first knowledge base (blocked on owner mapping + KB store).
6. Finance review before comments are used — agent produces **draft only**, no auto-publish.

**Explicitly OUT of scope (Phase 2):** MS, Group, Group F, OTI processing; customer / cost-centre / service-area / project dimensions; Business Controller validation gate and confidence-based routing (brief §7–8); governance (brief §14); budget/LY-based flagging.

**Blocking dependencies from Aurilo** (detailed in `Aurilo_Dependencies_and_Open_Questions.docx`):
| Dependency | Needed for | Status |
|---|---|---|
| Internal LLM access (2 deployments: mini + flagship; embedding flagged for Phase 2) | Draft commentary | requested |
| Teams: service account + delegated channel permissions (post + read, polling, no inbound) | MVP §15.4 questions & reminders | requested |
| Owner mapping (6 areas + default contact) + SharePoint List (7-column schema) | MVP §15.5 | requested |

**Business decisions still pending from client:** named Finance reviewer; monthly draft delivery channel; monthly data-refresh owner/timing/location.

---

## Input files (in `data/<bu>/` — never commit to git)

Each BU has its own subfolder (`data/itds/`, `data/ms/`, `data/group/`) so ingest scripts glob `*.xlsx` scoped to their BU without risk of picking up another BU's file. Each ingest script's `__main__` picks the most-recently-modified `.xlsx` in its BU folder (`key=lambda f: f.stat().st_mtime, reverse=True`) — place the new month's export in the right subfolder before running; old exports can stay (only the newest by mtime is read).

**Current (format v2, June 2026 onward):**
| File | Folder | Unit | Sheet | Role |
|---|---|---|---|---|
| `copy NEW_ITDS_PnL_officeConnect_v1.xlsx` | `data/itds/` | ITDS | `master` | **pilot source of truth** |
| `MS P&L - Office Connect_NEW.xlsx` | `data/ms/` | MS | `MASTER` | Phase 2 |
| `copy Aurilo Group office connect.xlsx` | `data/group/` | all BUs | `Master Group/ITDS/MS/Group F/OTI` | reference/cross-check only (NOT authoritative; currently in k€; has precomputed `Differences` variance block usable as an oracle) |

**LEGACY (format v1, May 2026 and earlier) — do not build on; keep only for historical reconciliation:**
`copy ITDS_PnL_officeConnect_1.1.xlsx` (+ `_translated`), `copy MS P&L - Office Connect.xlsx`, `copy Management report 2026 pohja Group ja Group Functions.xlsx`.

**Always open with `data_only=True`.**

---

## Canonical model & FSLI crosswalk

Internal pipeline keys on **canonical IDs owned by us** — never on source labels. Source labels are resolved to canonical IDs at ingest via the crosswalk. This is the insurance layer against future CoA/format changes.

| canonical_id | LEGACY label (v1) | Current label (v2) | Confirmed |
|---|---|---|---|
| `revenue` | Revenue | Total Revenue | ✅ (March reconciles exactly) |
| `other_income` | Other Income | Non-Operating Income | ✅ (~€1.5k reclass, expected) |
| `cogs` | Materials and services | Cost of Goods Sold | ✅ |
| `gross_margin` | Gross Margin | Gross Margin | ✅ |
| `opex` | Other Operational Expenses | Operative Expenses | ✅ |
| `personnel` | Personnel Costs | Personnel Expenses | (name shift, same role) |
| `depreciation` | Depreciation | Depreciations and Amortizations | (name shift, same role) |
| `ebita` | — (proxied by BU Profit) | **Operative EBITA** | ✅ §9 rule target |
| `bu_profit` | Business Unit Profit | Business Unit Profit | == `ebita` at BU level |

New v2-only lines (no legacy counterpart): `Direct Margin`, `New Customer Acquisition`.

---

## Format v2 template anatomy (`master` sheet)

```
Row 1:  "Reporting day"   + datetime (e.g. 2026-06-30)
Row 2:  "Reporting month" + month number (e.g. 6)
Row 3:  "YYYY/MM" string  + "Reporting period" label   ← value sits LEFT of its label
Row 4:  SCENARIO TAG per column:  LY | CY | BUD | Prior FC | MTD | YTD | FY | Quarter | Half
Row 5:  month header (real datetimes) + FY/summary labels
Row 6+: data rows
```

- **Scenario blocks by column tag (row 4)** — no block-header labels anymore. LY = 2025 (12 months, restated), CY = 2026, BUD = 2026, Prior FC = 2026, each ending with an FY column. Then precomputed summary blocks: MTD (CY/BUD/LY/PriorFC for the reporting month), YTD, FY, Quarter, Half.
- **Label column varies**: ITDS standalone = column **B** (col A empty); MS standalone and Group workbook = column **A**. Detect dynamically (column with most strings among cols 1–3).
- **Two dialects until Aurilo unifies** (aliases required):
  - Standalone BU: tags `LY / CY / BUD / Prior FC`, summary = MTD/YTD/FY/Quarter/Half.
  - Group workbook: tags `LY / CY / Prio fct / Bud26` (year-stamped! match `Bud\d\d` by pattern), block order differs (forecast before budget), summary = old-style `KEY FIGURES` (`Prior FCT`) + `Quarterly figures` + `Differences` (precomputed To Bud/To LY/To Prior FCT variances, € and %).
  - Alias sets: prior-forecast ∈ {`Prior FC`, `Prio fct`, `Prior FCT`, `PREVIOUS FORECAST`}; budget ∈ {`BUD`, `Bud\d\d`, `BUDGET`, `Budget`}.
- **Row zones** (ITDS master, ~135 rows): P&L summary FSLIs (≈6–23) → Revenue/COGS/GM splits by offering (≈25–50) → account detail sections with headers `COGS Accounts`, `PEX accounts`, `OPEX accounts`, `Depreciation accounts` (≈52–129) → FTE (≈131–135). Row numbers are indicative — locate by scanning, never hardcode.
- **Hierarchy comes from account codes, NOT indent**: 6-digit code = leaf GL account, 3-digit code = account group (parent of same-prefix 6-digit codes), no code = FSLI / zone header / split line. Indent is **unreliable** (COGS Accounts zone has 18 coded accounts at indent 0). Indent may still be consulted in the P&L summary zone only.
- **Line typing matters** (account dimension mixes member types): FSLI (flag/rank targets), account group, leaf GL account, calculated `%` lines (exclude), statistical FTE lines (exclude from monetary variance), split/dimensional lines, section headers (parse anchors only).
- **Units**: BU standalone files in euros. Group workbook in thousands (k€) until Aurilo changes it — scale-check in validation if it is ever read.
- Labels are **natively English** in v2 — no translation step needed. `translate.py` is retained as a fallback ONLY if Finnish labels ever reappear (check before running: Google-translating English text is wasteful and risky).

### How to locate values — never hardcode positions

1. Month header row = row with the most datetime cells (v2: row 5, with ~48).
2. Tag row = month header row − 1; data starts at month header row + 1 (skip metadata/empty).
3. A figure column = intersection of tag (via alias match on row 4) and target month (datetime year+month match on row 5).
4. Reporting month: label-anchored scan (`Reporting period` / `Reporting month`, case-insensitive) checking cells on BOTH sides of the label; fallback = pattern scan for `MM/YYYY`-shaped string or lone datetime in the top-left region. `Reporting day` datetime (row 1) is the most robust single anchor.

---

## Core data model

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class PnLLine:
    # identity
    name: str                   # label as it appears in the v2 file (English)
    canonical_id: Optional[str] # crosswalk-resolved stable ID (None for unmapped detail lines)
    account_code: Optional[str] # 3- or 6-digit code if present (regex ^\d{3,6}\s)
    line_type: str              # "fsli" | "group_account" | "gl_account" | "other"
    period: str                 # "2026-06"
    # figures (pilot)
    cur_fc: Optional[float]     # CY column for the reporting month — CONFIRMED semantics
    pre_fc: Optional[float]     # Prior FC column — CONFIRMED semantics
    budget: Optional[float]     # BUD column — informational, never drives flagging
    # Phase 2 placeholders
    ly: Optional[float]
    ytd_actual: Optional[float]
    ytd_budget: Optional[float]
    fy_budget: Optional[float]
    # hierarchy
    parent: Optional[str]       # account-group CODE prefix (semantic grouping key) — NOT guaranteed
                                # to match a parsed row (e.g. group 470 has no row); never dereference
                                # without a guard. is_subtotal was dropped: use line_type == "fsli".
    # audit — non-negotiable
    source_file: str
    source_sheet: str           # "master"
    source_row: int
    source_col_cur_fc: str
    source_col_pre_fc: str
```

Every figure carries its source cell reference. `name_fi` was dropped for v2 (files are natively English); it remains in legacy v1 JSONs only.

---

## Variance engine rules

**Primary comparison: `cur_fc` vs `pre_fc`** (CY vs Prior FC — semantics confirmed). Budget/LY comparisons: compute if data present, but pilot flagging is driven only by the forecast comparison.

```python
vs_pre_fc_eur = cur_fc - pre_fc
vs_pre_fc_pct = (cur_fc - pre_fc) / abs(pre_fc) if pre_fc else None   # ← pilot primary
vs_budget_eur / vs_budget_pct — informational when budget present
```

**Flagging — brief §9 thresholds, OR logic (any breached rule flags):**

```python
MATERIALITY_THRESHOLD = {
    "pnl_eur": 25_000, "pnl_pct": 0.10,
    "gross_margin_eur": 10_000, "expense_eur": 10_000, "ebita_eur": 20_000,
}
# line-type rules key on canonical_id (as implemented in variance.py):
GROSS_MARGIN_OBJECTS = {"gross_margin"}
EXPENSE_OBJECTS      = {"cogs", "opex", "personnel", "other_opex", "depreciation"}
EBITA_OBJECTS        = {"ebita"}   # Operative EBITA — confirmed §9 target
NO_FLAG              = {"bu_profit"}   # == ebita at BU level; flagging both duplicates the mover
```

- Flag/rank **`ebita` only, not `bu_profit`** — they are identical at BU level (confirmed); `NO_FLAG` suppresses the duplicate.
- Customer-revenue €15k and recurring-variance (≥2 consecutive months) rules are Phase 2.
- **Output ranking:** flagged **FSLI lines only** (`RANK_LINE_TYPES = {"fsli"}`) by `abs(vs_pre_fc_eur)`, top `NUM_TOP_MOVERS = 10` → `top_movers` (names, rank order) + per-line `rank` (None off the podium). Detail lines keep their `flagged` value but are never ranked.
- **Known noise, CONFIRMED by Aurilo (22 Jul 2026, Finance rep):** the 10% rule with no size floor flags many small detail accounts (64/107 flagged @ 2026-06; e.g. €954 / −24%). Aurilo's answer to E2: "all outliers are equally important and will therefore be reviewed manually if AI does not handle them" — no de-minimis floor. §9 runs exactly as written, permanently — the de-minimis floor idea is rejected, not just parked. Top movers are unaffected either way (FSLI-only).

---

## Validation rules (run before variance engine, fail loud)

- Reporting month not resolvable → raise.
- Target month column not found in the CY block or the Prior FC block → raise.
- `cur_fc` or `pre_fc` is None on an FSLI line → raise.
- Required FSLIs missing (by canonical_id: revenue, cogs, gross_margin, opex, ebita) → raise.
- Parsed line count below sanity floor → raise (v2 baseline: 107 lines @ 2026-06 → floor 65; legacy v1 baseline was 99/60).
- **Semantic reconciliation (format-independent safety net):** for closed months, cross-check a couple of FSLIs against the Group workbook's precomputed `Differences` block (scale-adjusted) when available; and `cur_fc ≠ pre_fc` on at least some lines (guards against resolving both to the same block).
- Unit-scale guard if reading the Group workbook: values ÷1000 vs BU file → convert or raise.
- **DEFERRED — expected-period (staleness) guard:** variance `__main__` picks the latest `{bu}_*.json` by filename sort; if ingest failed that month, it silently reprocesses the previous period. Today's mitigation: the loop prints the period being processed (human check). Once Aurilo confirms the monthly refresh schedule (owner/day — open question in `Aurilo_Dependencies_and_Open_Questions.docx` §D, plus the expected-period rule §E6), add a hard `latest period == expected period` check. TODO marker sits in `variance.py __main__`.

---

## Output format (`variance_<bu>_<period>.json`)

```json
{
  "period": "2026-06",
  "business_unit": "ITDS",
  "materiality": { "pnl_eur": 25000, "pnl_pct": 0.10, "gross_margin_eur": 10000, "expense_eur": 10000, "ebita_eur": 20000 },
  "top_movers": ["Cost of Goods Sold", "Total Revenue"],
  "objects": [
    {
      "name": "Total Revenue",
      "canonical_id": "revenue",
      "cur_fc": 8369966.06,
      "pre_fc": 8290000.0,
      "vs_pre_fc_eur": 79966.06,
      "vs_pre_fc_pct": 0.0096,
      "flagged": true,
      "rank": 2,
      "source_cell_cur_fc": "master!U6",
      "source_cell_pre_fc": "master!AT6"
    }
  ]
}
```

Ingest writes `output/itds_<period>.json` (same `objects` key); files are period-stamped, never overwritten — history accumulates for Phase-2 recurring-variance detection.

---

## Scripts & run order

```
scripts/
├── translate.py          ← FALLBACK ONLY (v2 files are natively English; run only if Finnish labels reappear)
├── glossary.py           ← shared crosswalk & format profile: TAG_NAME aliases, CANONICAL, CODE_RE, PERIOD_RE
├── ingest_ITDS.py        ← CURRENT (rewritten in place for format v2, 18 Jul): parses `master` sheet
│                            → output/itds_<period>.json (107 lines @ 2026-06). v1 lives in git history.
├── variance.py           ← DONE (19 Jul): variance engine, consumes the JSON contract (format-agnostic).
│                            run() per input file; __main__ loops BU_PREFIXES, picks latest {bu}_*.json,
│                            skips BUs without ingest → output/variance_{bu}_{period}.json
└── (Phase 2: ingest_ms_v2.py, ingest_group_v2.py)
```

Monthly run order (pilot): `ingest_ITDS.py` → `variance.py`. No translation step.

Architecture rule: **adapters are consumables, the canonical layer is the asset.** Business logic (variance, commentary, KB, Teams) consumes only the JSON contract / canonical IDs and must never read Excel or source labels directly. A future format/ERP change costs one new adapter + one crosswalk column — nothing else.

---

## LEGACY: format v1 notes (May 2026 and earlier — for reference only)

- Sheet `masterDataSheet`; label col A; block-header labels (`BUDGET`, `PREVIOUS FORECAST`, `KEY FIGURES`) on the row above the month row; Actuals+FC block spanned 2025+2026; hierarchy via indent (reliable in v1); Finnish labels requiring `translate.py` (glossary `docs/glossary_finnish_english.xlsx` takes priority over auto-translate — "Käyttökate" must map to "EBITDA", not Google's guess).
- v1 ingest (`ingest_ITDS.py`) is complete and produced `output/itds_2026-05.json` (99 lines, validated). Do not extend it; format is dead.
- Old 4-digit Finnish CoA (3654, 4000…) has **no usable mapping** to the new 3/6-digit CoA below FSLI level — cross-month history at GL-account level is not possible across the ERP boundary; FSLI level reconciles (see Crosswalk).

---

## What NOT to do

- Do not use `pandas` for parsing — it loses cell coordinates. Use `openpyxl` cell-by-cell.
- Do not open files without `data_only=True`.
- Do not commit anything in `data/` (or client `.docx` files) to git.
- Do not send raw Finnish labels or customer/counterparty names to the LLM API.
- LLM payloads must be **whitelist-built** (explicit list of allowed fields), never blacklist-filtered: `source_*` fields and any line whose label contains an external counterparty name never leave the machine. The filter lives in the LLM payload builder, not in ingest/variance.
- Do not hardcode row/column positions — locate by scanning anchors (tags, datetimes, labels) with alias sets.
- Do not trust indent for hierarchy in v2 account-detail zones — derive from account-code structure.
- Do not key business logic on source labels — key on `canonical_id`.
- Do not read figures from the Group workbook without unit conversion (k€) while it remains unconverted.

---

## Reference docs

| File | Purpose |
|---|---|
| `Aurilo_Dependencies_and_Open_Questions.docx` | **master doc for the joint IT+Finance meeting (v1.2)** — access deps (LLM, Teams, owner mapping, KB) + open data/process/methodology questions (account→FSLI mapping, DM/NCA & OTI, variance §9 decisions, template housekeeping). Absorbed the former `Aurilo_Finance_Meeting_Questions.docx`. |
| `Aurilo_Closing_Variance_Agent_Scope_and_Dependencies.docx` | scope response (v1.0, 8 Jul 2026) |
| `Closing_Variance_AI_Agent_Brief.docx` | client brief — §9 thresholds, §15 MVP definition |
| `Meeting_Notes_070726.docx` | 7 Jul meeting outcomes |
| `docs/glossary_finnish_english.xlsx` | FI→EN glossary (legacy/fallback) |
| `docs/*.md` | itds_excel_guide, financial_policy, business_review_template, system_architecture, data_pipeline, project_plan (NOTE: written for format v1 — verify against v2 before relying on them) |
