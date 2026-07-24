from pathlib import Path
import json
from glossary_and_helpers import BU_PREFIXES, get_ranked_movers

def load_owner_mapping(path):
    with open(path, encoding ="utf-8") as file:
        owner_map = json.load(file)
    return owner_map
def build_questions(variance_path, owner_mapping_path):
    owner_map = load_owner_mapping(owner_mapping_path)
    record,ranked_movers = get_ranked_movers(variance_path)
    questions = []
    for object in ranked_movers: 
        owner = owner_map.get(object["canonical_id"],owner_map["_default"])
        direction = "above" if object["vs_pre_fc_eur"]>0 else "below"
        question = (f"{object["name"]} was €{abs(object["vs_pre_fc_eur"]):,.0f} {direction}"
                    f" Prior FC ({object["vs_pre_fc_pct"]:+.1%}) - what was the reason behind?")
        questions.append({
            "canonical_id": object["canonical_id"],
            "name": object["name"],
            "owner_name": owner["name"],
            "owner_email": owner["email"],
            "question": question
        })
    return {
        "period": record["period"],
        "business_unit": record["business_unit"],
        "questions": questions,
    }
if __name__ == "__main__":
    OWNER_MAPPING_PATH = "data/itds/owner_mapping.json"
    for bu in BU_PREFIXES:
        variance_files = sorted(Path("output/variance").glob(f"{bu}_*.json"), reverse=True)
        if not variance_files:
            print(f"{bu}: no variance file found, skipped.")
            continue
        questions = build_questions(variance_files[0], OWNER_MAPPING_PATH)
        Path("output/questions").mkdir(parents=True, exist_ok=True)
        out_path = f"output/questions/{bu}_{questions['period']}.json"
        with open(out_path, "w", encoding="utf-8") as file:
            json.dump(questions, file, ensure_ascii=False, indent=2)
        print(f"Wrote {out_path}")
