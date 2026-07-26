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
#regular expression to match reporting period in form yyyy/mm
PERIOD_RE = re.compile(r"^\s*(\d{4}/\d{1,2}|\d{1,2}/\d{4})\s*$")
