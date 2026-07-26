import json
from pathlib import Path
from glossary_and_helpers import BU_PREFIXES, get_ranked_movers
#field allowed to feed the LLM: only for the pilot and respecting data privacy
ALLOWED = ["name", "canonical_id", "cur_fc", "pre_fc",
           "vs_pre_fc_eur", "vs_pre_fc_pct", "rank"]

def load_kb_entries(bu, period):
    kb_by_canonical = {}
    for file in Path("output/kb_entries").glob(f"{bu}_*_{period}.json"):
        with open(file, encoding="utf-8") as f:
            entry = json.load(f)
        kb_by_canonical[entry["canonical_id"]] = entry
    return kb_by_canonical

def build_payload(variance_path):
    record, ranked_movers = get_ranked_movers(variance_path)
    bu, period = record["business_unit"].lower(), record["period"]
    kb_by_canonical = load_kb_entries(bu, period)
    allowed_objects = []
    for object in ranked_movers:
        entry = {key: object[key] for key in ALLOWED}
        kb_entry = kb_by_canonical.get(object["canonical_id"])
        entry["answer_clean"] = kb_entry["answer_clean"] if kb_entry else None
        entry["needs_review"] = kb_entry["needs_review"] if kb_entry else None
        allowed_objects.append(entry)
    return {
        "period": record["period"],
        "business_unit": record["business_unit"],
        "materiality": record["materiality"],
        "all_answered": all(o["answer_clean"] is not None for o in allowed_objects),
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