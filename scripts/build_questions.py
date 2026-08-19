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
        #detail lines inherit the owner of the FSLI area they roll up to
        #(Aurilo owner mapping C1); fsli_area is resolved at ingest.
        owner = (owner_map.get(object["canonical_id"])
                 or owner_map.get(object.get("fsli_area"))
                 or owner_map["_default"])
        direction = "above" if object["vs_pre_fc_eur"]>0 else "below"
        #full name: it doubles as the @mention text once Aurilo supply the
        #Azure AD object IDs, so it has to match the directory entry exactly.
        question = (f"Hey {owner["name"]}, {object["name"]} came in "
                    f"€{abs(object["vs_pre_fc_eur"]):,.0f} {direction} Prior FC "
                    f"({object["vs_pre_fc_pct"]:+.1%}) — what was the reason behind?")
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
        out_dir = Path("output/questions").resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        # period-stamped file is history (never overwritten); _latest is a stable
        # pointer so n8n can read a fixed path without knowing the period.
        for out_path in (out_dir / f"{bu}_{questions['period']}.json", out_dir / f"{bu}_latest.json"):
            with open(out_path, "w", encoding="utf-8") as file:
                json.dump(questions, file, ensure_ascii=False, indent=2)
            print(f"Wrote {out_path}")
