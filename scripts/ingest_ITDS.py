import openpyxl
from typing import Optional
import datetime
import re
from openpyxl.utils import get_column_letter
import json
from dataclasses import asdict

#regular expression to separate account code (4 digit) and name
CODE_RE = re.compile(r"^(\d{4,5})\s+(.+)$")


#setting up the dataclass PnLLine
from dataclasses import dataclass
@dataclass
class PnLLine:
    #identity fields:
    name: str
    name_fi: str 
    account_code: Optional[str]
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
    indent_level: int
    is_subtotal: bool
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
#find header rows:
def find_header_rows(ws):
    best_row = None
    best_count = 0
    for row in range(1,16):
        count = 0
        for column in range(1, ws.max_column+1):
            
            if isinstance(ws.cell(row, column).value, datetime.datetime):
                count += 1
        if count > best_count:
            best_row = row
            best_count = count
    if best_count >= 12:
        return (best_row, best_row-1, best_row+1) #month_header, label, data_start_from
    raise ValueError("Month header row not found")
#get reporting month:
def get_reporting_month(ws):
    cell = None
    for row in range(1,3):
        for column in range(1,5):
            scanning_cell = ws.cell(row, column).value
            if isinstance(scanning_cell, str) and "/" in scanning_cell:
                cell = scanning_cell
                return cell
    raise ValueError("REPORTING MONTH cell not found")
#find block bounds for actual, fc, budget, pre fc, and key fig:
def find_block_bounds(ws, label_row):
    budget_start_col = None
    pre_fc_start_col = None
    key_fig_start_col = None
    
    for column in range (1, ws.max_column+1):
        cell_label = ws.cell(label_row, column).value
        if "BUDGET" in str(cell_label).upper():
            budget_start_col = column
        elif "PREVIOUS FORECAST" in str(cell_label).upper():
            pre_fc_start_col = column
        elif "KEY FIGURES" in str(cell_label).upper():
            key_fig_start_col = column
    #check for ValueError:
    labels= {budget_start_col: "BUDGET",  pre_fc_start_col: "PREVIOUS FORECAST", key_fig_start_col: "KEY FIGURES"}
    for label in labels:
        if label is None:
            raise ValueError(f"Label {labels.get(label)} not found")
    #returning type shi
    act_to_fc_col = (2, budget_start_col-1)
    budget_col = (budget_start_col, pre_fc_start_col-1)
    pre_fc_col = (pre_fc_start_col, key_fig_start_col-1)
    return act_to_fc_col, budget_col, pre_fc_col
#find month column with a given period, i.e.: "2026-05"
def find_month_col(ws, month_header_row, block, period):
    year, month = period.split("-")
    year, month = int(year), int(month)
    start_col, end_col = block
    for column in range(start_col, end_col+1):
        cell_value = ws.cell(month_header_row, column).value
        if isinstance(cell_value, datetime.datetime) and cell_value.year == year and cell_value.month == month:
            return column
    raise ValueError(f"Month {period} not found in columns {start_col}-{end_col}")

#loop to create PnLLine object
def create_pnl_object(ws, ws_ori, data_start_from, period, cur_fc_col, budget_col, pre_fc_col, source_file):
    pnl_objects = []
    current_parent = None
    for row in range(data_start_from, ws.max_row+1):
        label = ws.cell(row, 1).value
        if label is None or str(label).strip() == "":
            continue
        if str(label).strip() == "FTE":
              break
        if str(label).strip().endswith("%"):
             continue 
        label_fi = ws_ori.cell(row, 1).value
        m = CODE_RE.match(str(label).strip()) #matching with CODE_RE above
        m_fi = CODE_RE.match(str(label_fi).strip()) 
        account_code = m.group(1) if m else None
        name = m.group(2) if m else str(label).strip()
        name_fi = m_fi.group(2) if m_fi else str(label_fi).strip()
        indent = int(ws.cell(row, 1).alignment.indent or 0)
        is_subtotal = (indent ==0)
        if is_subtotal:
            parent = None
            current_parent = str(label).strip()
        else:
            parent = current_parent
        pnl_objects.append(PnLLine(
            name = name,
            name_fi = name_fi,
            account_code = account_code,
            period = period,
            cur_fc = ws.cell(row, cur_fc_col).value,
            pre_fc = ws.cell(row, pre_fc_col).value,
            budget = ws.cell(row, budget_col).value,
            ly = None, ytd_actual = None, ytd_budget = None, fy_budget = None,
            indent_level=indent,
            is_subtotal = is_subtotal,
            parent = parent,
            source_file = source_file,
            source_sheet = "masterDataSheet",
            source_row = row,
            source_col_cur_fc = get_column_letter(cur_fc_col),
            source_col_pre_fc = get_column_letter(pre_fc_col),

        ))
    return pnl_objects
#validation function:
def validate(pnl_objects, period):
    if not pnl_objects:
        raise ValueError(f"No PnL objects for period {period}.")
    if len(pnl_objects) < 60:
        raise ValueError(f"{len(pnl_objects)} out of 50 lines parsed, layout may have changed.")
    for object in pnl_objects:
        if not object.name_fi or object.name_fi == None:
            raise ValueError(f"name_fi missing at row {object.source_row}, original and translated files maybe inconsistent.")
        if object.is_subtotal and (object.cur_fc is None or object.pre_fc is None):
            raise ValueError(f"Error in cur_fc and pre_fc on object '{object.name}' (row {object.source_row}): cur_fc = {object.cur_fc}, pre_fc = {object.pre_fc}.")
    important_subtotals = {"Revenue", "Gross Margin", "Personnel Costs", "Business Unit Profit"}
    all_subtotals = {object.name for object in pnl_objects}
    for subtotal in important_subtotals:
        if subtotal not in all_subtotals:
            raise ValueError(f"Missing subtotal {subtotal}.")
#writing into json file:
def write_json(pnl_objects, period):
    record = {
        "period": period,
        "business_unit": "ITDS",
        "objects": [asdict(object) for object in pnl_objects],
    }
    output_path = f"output/itds_{period}.json"
    with open(output_path, "w", encoding = "utf-8") as file:
        json.dump(record, file, ensure_ascii=False, indent =2)
    print(f"Wrote {len(pnl_objects)} objects to {output_path}.")



if __name__ == "__main__":
    # load workbooks
    wb = openpyxl.load_workbook("data/copy ITDS_PnL_officeConnect_1.1_translated.xlsx", data_only=True)
    ws = wb['masterDataSheet']
    wb_ori = openpyxl.load_workbook("data/copy ITDS_PnL_officeConnect_1.1.xlsx", data_only=True)
    ws_ori = wb_ori['masterDataSheet']

    # locate rows
    month_row, label_row, data_start_from = find_header_rows(ws)
    period = parse_period(get_reporting_month(ws))
    act_to_fc_block, budget_block, pre_fc_block = find_block_bounds(ws, label_row)
    # find columns
    rep_month_cur_fc_col = find_month_col(ws, month_row, act_to_fc_block, period)
    rep_month_budget_col = find_month_col(ws, month_row, budget_block, period)
    rep_month_pre_fc_col = find_month_col(ws, month_row, pre_fc_block, period)
    pnl_objects = create_pnl_object(ws, ws_ori, data_start_from, period, rep_month_cur_fc_col, rep_month_budget_col, rep_month_pre_fc_col, "copy ITDS_PnL_officeConnect_1.1.xlsx")
    #validate before writing
    validate(pnl_objects, period)
    write_json(pnl_objects, period)

