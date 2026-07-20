import json
#field allowed to feed the LLM: only for the pilot and respecting data privacy
ALLOWED = ["name", "canonical_id", "cur_fc", "pre_fc",
           "vs_pre_fc_eur", "vs_pre_fc_pct", "rank"]
def build_payload(variance_path):
    with open(variance_path, encoding = "utf-8") as file:
        record = json.load(file)
    movers = [object for object in record["objects"] if object["rank"] is not None]
    ranked_movers = sorted(movers, key = lambda o: o["rank"])
    objects = [{key: object[key] for key in ALLOWED} for object in ranked_movers]
    return {
        "period": record["period"],
        "business_unit": record["business_unit"],
        "materiality": record["materiality"],    
        "objects": objects,
    }
