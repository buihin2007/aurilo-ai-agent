from pathlib import Path
from glossary_and_helpers import group_by_owner, BU_PREFIXES
import json

def load_threads(path):
    with open(path, encoding = "utf-8") as file:
        threads = json.load(file)
    for key in {"period", "business_unit", "threads"}:
        if not threads.get(key):
            raise ValueError(f"{path}: missing or empty field: '{key}'")
    return threads
def build_reminders(threads_path):
    threads = load_threads(threads_path)
    unans_groups = group_by_owner([thread for thread in threads["threads"] if not thread["has_reply"]])
    reminders = []
    for email, unans_group in unans_groups.items():
        questions = "\n".join(f"- {line['question']}" for line in unans_group["lines"])
        reminder_text = f"Reminder — still waiting for your reply on:\n{questions}"
        reminders.append({
            "owner_name": unans_group["owner_name"],
            "owner_email": email,
            "reminder_text": reminder_text
        })
    return {
        "period": threads["period"],
        "business_unit": threads["business_unit"],
        "reminders": reminders
    }
if __name__ == "__main__":
    
    for bu in BU_PREFIXES:
        threads_files = sorted(Path("output/threads").glob(f"{bu}_*.json"), reverse=True)
        if not threads_files:
            print(f"{bu}: no threads file found, skipped.")
            continue
        reminders = build_reminders(threads_files[0])
        Path("output/reminders").mkdir(parents=True, exist_ok=True)
        out_path = f"output/reminders/{bu}_{reminders['period']}.json"
        with open(out_path, "w", encoding="utf-8") as file:
            json.dump(reminders, file, ensure_ascii=False, indent=2)
        print(f"Wrote {out_path}")