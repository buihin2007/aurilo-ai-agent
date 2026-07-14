import openpyxl
from typing import Optional
import datetime



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

if __name__ == "__main__":
    # load workbooks
    wb = openpyxl.load_workbook("data/copy ITDS_PnL_officeConnect_1.1_translated.xlsx", data_only=True)
    ws = wb['masterDataSheet']

    # locate everything dynamically
    month_row, label_row, data_start_from = find_header_rows(ws)
    period = parse_period(get_reporting_month(ws))
    act_to_fc_block, budget_block, pre_fc_block = find_block_bounds(ws, label_row)

    rep_month_cur_fc_col = find_month_col(ws, month_row, act_to_fc_block, period)
    rep_month_budget_col = find_month_col(ws, month_row, budget_block, period)
    rep_month_pre_fc_col = find_month_col(ws, month_row, pre_fc_block, period)

    print(period, rep_month_cur_fc_col, rep_month_budget_col, rep_month_pre_fc_col) 


    