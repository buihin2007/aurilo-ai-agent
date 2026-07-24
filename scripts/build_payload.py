import json
from pathlib import Path
from glossary_and_helpers import BU_PREFIXES, get_ranked_movers
#field allowed to feed the LLM: only for the pilot and respecting data privacy
ALLOWED = ["name", "canonical_id", "cur_fc", "pre_fc",
           "vs_pre_fc_eur", "vs_pre_fc_pct", "rank"]
def build_payload(variance_path):
    record, ranked_movers = get_ranked_movers(variance_path)
    allowed_objects = [{key: object[key] for key in ALLOWED} for object in ranked_movers]
    return {
        "period": record["period"],
        "business_unit": record["business_unit"],
        "materiality": record["materiality"],    
        "allowed_objects": allowed_objects,
        
    }
if __name__ == "__main__":
    for bu in BU_PREFIXES:
        files = sorted(Path("output/variance").glob(f"{bu}_*.json"), reverse=True)
        if not files:
            print(f"{bu}: no variance file found, skipped.")
            continue
        payload = build_payload(files[0])
        Path("output/payload").mkdir(parents=True, exist_ok=True)
        out_path = f"output/payload/{bu}_{payload['period']}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"Wrote {out_path}")