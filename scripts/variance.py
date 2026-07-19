import json
from pathlib import Path

BU_PREFIXES = ["itds","ms","group"]

MATERIALITY_THRESHOLD = {"pnl_eur": 25000, "pnl_pct": 0.10, "gross_margin_eur":10000
                         , "expense_eur": 10000, "ebita_eur": 20000}
REQUIRED_CANONICAL ={"revenue", "cogs", "gross_margin", "opex", "ebita"}
GROSS_MARGIN_OBJECTS = {"gross_margin"}
EXPENSE_OBJECTS = {"cogs", "opex", "personnel", "other_opex","depreciation"}
EBITA_OBJECTS = {"ebita"}
NO_FLAG = {"bu_profit"} #repetition: bu_profit = ebita
RANK_LINE_TYPES = {"fsli"}
NUM_TOP_MOVERS = 10
def load_input(path):
    with open(path, encoding = "utf-8") as file:
        data = json.load(file)
    for key in {"period", "business_unit", "objects"}:
        if not data.get(key):
            raise ValueError(f"{path}: missing or empty field: '{key}'")
    found_canonical = set()
    for object in data["objects"]:
            found_canonical.add(object["canonical_id"])
    missing = REQUIRED_CANONICAL-found_canonical
    if missing:
            raise ValueError(f"{path}: missing required FSLIs: {missing}")
    return data
def compute(objects):
    for object in objects:
        cur_fc, pre_fc, budget = object["cur_fc"], object["pre_fc"], object["budget"]
        if cur_fc is None or pre_fc is None:
            object["vs_pre_fc_eur"] = None
            object["vs_pre_fc_pct"] = None
        else:
            object["vs_pre_fc_eur"] = cur_fc-pre_fc
            object["vs_pre_fc_pct"] = (cur_fc-pre_fc)/abs(pre_fc) if pre_fc !=0 else None
        if budget is None or cur_fc is None:
            object["vs_budget_eur"] = None
            object["vs_budget_pct"] = None
        else:
            object["vs_budget_eur"] = cur_fc-budget
            object["vs_budget_pct"] = (cur_fc-budget)/abs(budget) if budget !=0 else None
    return objects
def apply_flags(objects):
    for object in objects:
        var_eur = object["vs_pre_fc_eur"]
        var_pct = object["vs_pre_fc_pct"]
        can_id = object["canonical_id"]
        if can_id in NO_FLAG or var_eur is None:
            flagged = False
        else: 
            flagged = (abs(var_eur)> MATERIALITY_THRESHOLD["pnl_eur"]) or (var_pct is not None and abs(var_pct)>MATERIALITY_THRESHOLD["pnl_pct"])or (can_id in GROSS_MARGIN_OBJECTS and abs(var_eur)>MATERIALITY_THRESHOLD["gross_margin_eur"])  or (can_id in EXPENSE_OBJECTS and abs(var_eur)>MATERIALITY_THRESHOLD["expense_eur"])  or (can_id in EBITA_OBJECTS and abs(var_eur)> MATERIALITY_THRESHOLD["ebita_eur"])
        object["flagged"] = flagged
    return objects
def rank_movers(objects):
    list_to_rank =[]
    for object in objects:
        object["rank"] = None
        if object["flagged"] and object["line_type"] in RANK_LINE_TYPES:
            list_to_rank.append(object)
    ranked_list = sorted(list_to_rank, key=lambda o: abs(o["vs_pre_fc_eur"]), reverse=True)
    for i, object in enumerate(ranked_list[:NUM_TOP_MOVERS], start=1):
        object["rank"] = i
    return objects
def write_output(data, objects):
    ranked = sorted((object for object in objects if object["rank"] is not None),
                    key=lambda object: object["rank"])
    record = {
        "period": data["period"],
        "business_unit": data["business_unit"],
        "materiality": MATERIALITY_THRESHOLD,
        "top_movers": [object["name"] for object in ranked],
        "objects": objects,
    }
    bu = data["business_unit"].lower()
    output_path = f"output/variance_{bu}_{data['period']}.json"
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(record, file, ensure_ascii=False, indent=2)
    num_flagged = sum(1 for object in objects if object["flagged"])
    print(f"Wrote {output_path}: {len(objects)} objects, {num_flagged} flagged, {len(ranked)} ranked.")
    return output_path
def run(input_path):
    data = load_input(input_path)
    objects = rank_movers(apply_flags(compute(data["objects"])))
    return write_output(data, objects)

if __name__ == "__main__":
    # TODO: staleness guard once Aurilo confirms the monthly refresh schedule
    for bu in BU_PREFIXES:
        files = sorted(Path("output").glob(f"{bu}_*.json"), reverse=True)
        if not files:
            print(f"{bu}: no ingest file found, skipped.")
            continue
        print(f"{bu}: processing {files[0].name}")
        run(files[0])