# glossary shared by all BU ingests
import re
import json

#prefixes
BU_PREFIXES = ["itds","ms","group"]

#shared helper for payload and questions, return record and rank movers
def get_ranked_movers(variance_path):
    with open(variance_path, encoding="utf-8") as file:
        record = json.load(file)
    movers = [o for o in record["objects"] if o["rank"] is not None]
    return record, sorted(movers, key=lambda o: o["rank"])
#all possible name of some tags:
TAG_NAME = {   
    "cur_fc": {"CY"},
    "pre_fc": {"PRIOR FC", "PRIO FCT", "PRIOR FCT"},   
    "budget": {"BUD", "BUDGET"},                        
    "ly": {"LY"},
}
#group owners to remind:
def group_by_owner(questions):
    groups = {}
    for q in questions:
        email = q["owner_email"]
        groups.setdefault(email, {"owner_name": q["owner_name"], "lines": []})
        groups[email]["lines"].append(q)
    return groups
#match Bud26 and so on:
BUDGET_TAG_RE = re.compile(r"^BUD\d\d$")   

#converting label into a stable name to a stable reference id
CANONICAL = {
    "Total Revenue": "revenue",
    "Non-Operating Income": "other_income",
    "Cost of Goods Sold": "cogs",
    "Gross Margin": "gross_margin",
    "Operative Expenses": "opex",
    "Operating expenses": "opex",         
    "Personnel Expenses": "personnel",
    "Other Operating Expenses": "other_opex",
    "Depreciations and Amortizations": "depreciation",
    "Operative EBITA": "ebita",
    "Business Unit Profit": "bu_profit",
    "Direct Margin": "direct_margin",           
    "New Customer Acquisition": "new_customer_acquisition",  
}
#regular expression to match account code(3 or 6 digit)
CODE_RE = re.compile(r"^(\d{3,6})\s+(.+)$")

# --- account hierarchy from Adaptive's account master (Aurilo, 08 Aug 2026) ---
# "Accounts (6)" holds every GL account with a "Rolls Up To" parent. Walking that
# chain upwards lands on a format-v2 FSLI label, e.g.
#   400 Purchases > Materials and supplies > Cost of Goods Sold
# This replaces inferring hierarchy from the account-code prefix, and is what lets
# a detail line inherit the owner of its FSLI area (Aurilo owner mapping C1).
ACCOUNT_MASTER_DIR = "data"
ACCOUNT_MASTER_PATTERN = "Accounts*.xlsx"
_HEADER_ROW = 4          # row 1-3 are export metadata; headers sit on row 4
_MAX_WALK = 20           # guard against a cyclic "Rolls Up To" chain

def _read_account_rows(path):
    import openpyxl
    workbook = openpyxl.load_workbook(path, data_only=True)
    sheet = workbook[workbook.sheetnames[0]]
    header = [str(c).strip() if c else "" for c in
              next(sheet.iter_rows(min_row=_HEADER_ROW, max_row=_HEADER_ROW, values_only=True))]
    for column in ("Name", "Code", "Rolls Up To"):
        if column not in header:
            return []
    name_i, code_i, up_i = (header.index(c) for c in ("Name", "Code", "Rolls Up To"))
    rows = []
    for row in sheet.iter_rows(min_row=_HEADER_ROW + 1, values_only=True):
        if not row[name_i]:
            continue
        rows.append((str(row[name_i]).strip(),
                     str(row[code_i]).strip() if row[code_i] else "",
                     str(row[up_i]).strip() if row[up_i] else ""))
    return rows

def load_account_area_map(directory=ACCOUNT_MASTER_DIR):
    """Return (by_code, by_name): account code / account name -> canonical_id of
    the FSLI it rolls up to.

    Entries that never reach a CANONICAL label (balance-sheet accounts, unmapped
    branches) are simply absent — callers fall back to their own default. The
    by_name map catches statement lines the export prints without a code, e.g.
    "Salaries and wages" or "External services".
    """
    from pathlib import Path
    parent_of, code_of = {}, {}
    for path in sorted(Path(directory).glob(ACCOUNT_MASTER_PATTERN)):
        for name, code, rolls_up_to in _read_account_rows(path):
            parent_of[name] = rolls_up_to
            if code:
                code_of[name] = code
    by_code, by_name = {}, {}
    for name in parent_of:
        current, seen = name, set()
        for _ in range(_MAX_WALK):
            if current in CANONICAL:
                area = CANONICAL[current]
                by_name[_strip_code(name)] = area
                if name in code_of:
                    by_code[code_of[name]] = area
                break
            if current in seen:
                break                      # cycle in the master data
            seen.add(current)
            current = parent_of.get(current, "")
            if not current:
                break
    return by_code, by_name

def _strip_code(label):
    """'500 Salaries' -> 'salaries'; used to match export labels to master names."""
    match = CODE_RE.match(label)
    return (match.group(2) if match else label).strip().lower()
#regular expression to match reporting period in form yyyy/mm
PERIOD_RE = re.compile(r"^\s*(\d{4}/\d{1,2}|\d{1,2}/\d{4})\s*$")
