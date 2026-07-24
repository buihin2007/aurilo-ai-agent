import openpyxl
from typing import Optional
import datetime
from pathlib import Path
from glossary_and_helpers import TAG_NAME, CANONICAL, BUDGET_TAG_RE, CODE_RE, PERIOD_RE
from openpyxl.utils import get_column_letter
import json
from dataclasses import asdict

#setting up the dataclass PnLLine
from dataclasses import dataclass
@dataclass
class PnLLine:
    #identity fields:
    name: str
    canonical_id: Optional[str]
    account_code: Optional[str]
    line_type: str
    period: str
    #figures-phase1:
    cur_fc: Optional[float]
    pre_fc: Optional[float]
    #figures-phase2: 
    budget: Optional[float]
    ly: Optional[float]
    ytd_actual: Optional[float]
    ytd_budget: Optional[float]
    fy_budget: Optional[float]
    #relation:
    parent: Optional[str]
    #for-audit-trail:
    source_file: str
    source_sheet: str
    source_row: int
    source_col_cur_fc: str #e.g: A, B, C, D
    source_col_pre_fc: str

#helper to parse period:
def parse_period(val):
    if isinstance(val, datetime.datetime):          
        return f"{val.year}-{val.month:02d}"
    a, b = str(val).strip().split("/")               
    year, month = (a, b) if len(a) == 4 else (b, a)  
    return f"{year}-{int(month):02d}"

#find master sheet:
def find_sheet(wb, target_name):
    matches = [s for s in wb.sheetnames if target_name.upper() in s.strip().upper()]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one sheet containing '{target_name}', found {matches}")
    return wb[matches[0]]
#find header rows:
def find_header_rows(ws):
    for row in range(1,16):
        count = 0
        for column in range(1, ws.max_column+1):
            if isinstance(ws.cell(row, column).value, datetime.datetime):
                count += 1
        if count >= 12:
            return (row, row-1, row+1) #month_header, label, data_start_from
    raise ValueError("Month header row not found")

#find label column:
def find_label_col(ws):
    most_string_col = 0
    label_col = None
    for column in range(1,5):
        string_counted = 0
        for row in range(1,ws.max_row+1):
            if isinstance(ws.cell(row,column).value, str):
                string_counted += 1
        if string_counted > most_string_col:
            most_string_col = string_counted
            label_col = column
    if label_col is None:
        raise ValueError("Label column not found")
    return label_col

#get reporting month:
def get_reporting_period(ws):
    cell = None
    for row in range(1,5):
        for column in range(1,5):
            scanning_cell = ws.cell(row, column).value
            if isinstance(scanning_cell, str) and PERIOD_RE.match(scanning_cell):
                cell = scanning_cell
                return cell
    raise ValueError("Reporting period cell not found")

#find month column with a given period, i.e.: "2026-05"
def find_month_col(ws, tag_header_row, month_header_row, tags_set, period,extra_re=None):
    year, month = period.split("-")
    year, month = int(year), int(month)
    for column in range(1, ws.max_column+1):
        tag = str(ws.cell(tag_header_row,column).value or "").strip().upper()
        if (tag in tags_set) or (extra_re is not None and extra_re.match(tag)):
            month_header = ws.cell(month_header_row, column).value
            if isinstance(month_header, datetime.datetime) and month_header.year == year and month_header.month == month:
                return column
    
    raise ValueError(f"No column with tag {tags_set} for {period}")

#loop to create PnLLine object
def create_pnl_object(ws, data_start_from, period, label_col, cur_fc_col, budget_col, pre_fc_col, source_file):
    pnl_objects = []
    seen_canonical = []
    for row in range(data_start_from, ws.max_row+1):
        label = ws.cell(row, label_col).value
        label_clean = str(label).strip()
        cur_fc = ws.cell(row, cur_fc_col).value
        pre_fc = ws.cell(row, pre_fc_col).value
        budget = ws.cell(row, budget_col).value
        line_type = None
        parent = None
        if label is None or label_clean == "":
            continue
        if str(label).strip().endswith("%"):
             continue 
        if cur_fc is None and pre_fc is None and budget is None:
            continue
        if "FTE" in label_clean.upper():
            continue
        canonical_id = CANONICAL.get(label_clean)
        if canonical_id in seen_canonical:
            canonical_id = None
        elif canonical_id:
            seen_canonical.append(canonical_id)
        m = CODE_RE.match(str(label).strip()) #matching with CODE_RE
        if m and len(m.group(1))==3:
                line_type = "group_account"
                parent = None
        elif m and len(m.group(1))==6:
                line_type = "gl_account"  #general ledger account
                parent = m.group(1)[:3]
        elif canonical_id:
                line_type = "fsli"
                parent = None
        else:
                line_type = "other"   
                parent = None 
        account_code = m.group(1) if m else None
        name = m.group(2) if m else str(label).strip()
        
        
        pnl_objects.append(PnLLine(
            name = name,
            canonical_id = canonical_id,
            account_code = account_code,
            line_type = line_type,
            period = period,
            cur_fc = cur_fc,
            pre_fc = pre_fc,
            budget = budget,
            ly = None, ytd_actual = None, ytd_budget = None, fy_budget =None,
            parent = parent,
            source_file = source_file,
            source_sheet = ws.title,
            source_row = row,
            source_col_cur_fc = get_column_letter(cur_fc_col),
            source_col_pre_fc = get_column_letter(pre_fc_col),

        ))
    return pnl_objects
#validation function:
def validate(pnl_objects, period):
    if not pnl_objects:
        raise ValueError(f"No PnL objects for period {period}.")
    if len(pnl_objects) < 65:
        raise ValueError(f"Only {len(pnl_objects)} lines parsed, layout may have changed.")
    for object in pnl_objects:
        if object.line_type == "fsli" and (object.cur_fc is None or object.pre_fc is None):
            raise ValueError(f"Error in cur_fc and pre_fc on object '{object.name}' (row {object.source_row}): cur_fc = {object.cur_fc}, pre_fc = {object.pre_fc}.")
    all_canonical_ids_required = {"revenue", "cogs", "gross_margin", "opex", "ebita"}
    all_canonical_ids_found = {object.canonical_id for object in pnl_objects}
    for canonical_id in all_canonical_ids_required:
        if canonical_id not in all_canonical_ids_found:
            raise ValueError(f"Missing FSLI: {canonical_id}.")
    if all(object.cur_fc == object.pre_fc for object in pnl_objects):
        raise ValueError("cur_fc == pre_fc on every line — CY and Prior FC may have refered to the same block.")
#writing into json file:
def write_json(pnl_objects, period):
    record = {
        "period": period,
        "business_unit": "ITDS",
        "objects": [asdict(object) for object in pnl_objects],
    }
    output_path = f"output/ingest/itds_{period}.json"
    Path("output/ingest").mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding = "utf-8") as file:
        json.dump(record, file, ensure_ascii=False, indent =2)
    print(f"Wrote {len(pnl_objects)} objects to {output_path}.")



if __name__ == "__main__":
    # load workbooks
    files = sorted(Path("data/itds").glob("*.xlsx"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError("No .xlsx file found in data/itds/ — place this month's ITDS export there first.")
    source_file = files[0].name
    wb = openpyxl.load_workbook(files[0], data_only=True)
    ws = find_sheet(wb, "master")
   
    # locate rows, column, find pre_fc, prior_fc, budget:
    month_row, tag_row, data_start_from = find_header_rows(ws)
    label_col = find_label_col(ws)
    period = parse_period(get_reporting_period(ws))
    # find columns
    cur_fc_col = find_month_col(ws, tag_row, month_row, TAG_NAME["cur_fc"], period)
    budget_col = find_month_col(ws, tag_row, month_row, TAG_NAME["budget"], period, BUDGET_TAG_RE)
    pre_fc_col = find_month_col(ws, tag_row, month_row, TAG_NAME["pre_fc"], period)
    pnl_objects = create_pnl_object(ws, data_start_from, period, label_col,
                                    cur_fc_col, budget_col, pre_fc_col, source_file)
    validate(pnl_objects, period)
    write_json(pnl_objects, period)

