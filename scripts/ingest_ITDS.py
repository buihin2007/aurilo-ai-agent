import openpyxl

wb = openpyxl.load_workbook("data/copy ITDS_PnL_officeConnect_1.1.xlsx", data_only = True)
ws = wb['closing_PnL']
source_cols = [3, 4, 5, 8, 11, 15, 16, 19, 22, 26, 27, 30, 33]
col_labels = ["P&L", "Month Actual", "Month Budget", "Month LY", "Month Prior FC","YTD Actual","YTD Budget","YTD LY", "YTD Prior FC","FY26 Actual","FY26 Budget","FY26 LY","FY26 Prior FC"]

#setting up the dataclass PnLLine
from dataclasses import dataclass
@dataclass
class PnLLine:
    name: str
    source_sheet: str  # e.g., "closing_PnL"
    source_row: int    # e.g., 10
    month_actual: float
    month_budget: float
    month_ly: float
    month_priorfc: float
    ytd_actual: float
    ytd_budget: float
    ytd_ly: float
    ytd_priorfc: float
    fy26_actual: float
    fy26_budget: float
    fy26_ly: float
    fy26_priorfc: float
#create PnLLine objects
pnlline_objects = []
for row_num in range(4, 41):
    
    col_pnl = ws.cell(row = row_num, column = 3).value
    pnl = PnLLine(
            name = str(col_pnl),
            source_sheet = "closing_PnL",
            source_row = row_num,
            month_actual = ws.cell(row = row_num, column = 4).value,
            month_budget = ws.cell(row = row_num, column = 5).value,
            month_ly = ws.cell(row = row_num, column = 8).value,
            month_priorfc = ws.cell(row = row_num, column = 11).value,
            ytd_actual = ws.cell(row = row_num, column = 15).value,
            ytd_budget = ws.cell(row = row_num, column = 16).value,
            ytd_ly = ws.cell(row = row_num, column = 19).value,
            ytd_priorfc = ws.cell(row = row_num, column = 22).value,
            fy26_actual = ws.cell(row = row_num, column = 26).value,
            fy26_budget = ws.cell(row = row_num, column = 27).value,
            fy26_ly = ws.cell(row = row_num, column = 30).value,
            fy26_priorfc = ws.cell(row = row_num, column = 33).value,
        )
    if col_pnl is not None and not str(col_pnl).endswith("%"):
        pnlline_objects.append(pnl)

#Converting objects into JSON-serializable format
import json
from dataclasses import asdict
data = {
    "period": "05-2026",
    "business_unit": "ITDS",
    "lines": [asdict(line)for line in pnlline_objects]
}

with open("output/variance.json", "w") as f:
    json.dump(data, f, indent=2)  
    
   


