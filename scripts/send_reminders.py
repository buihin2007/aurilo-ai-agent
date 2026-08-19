from pathlib import Path
from glossary_and_helpers import BU_PREFIXES
import json

def load_threads(path):
    with open(path, encoding = "utf-8") as file:
        threads = json.load(file)
    for key in {"period", "business_unit", "threads"}:
        if not threads.get(key):
            raise ValueError(f"{path}: missing or empty field: '{key}'")
    for thread in threads["threads"]:
        for key in ("message_id", "has_reply"):
            if key not in thread:
                raise ValueError(f"{path}: thread '{thread.get('name')}' missing field: '{key}'")
    return threads
def build_reminders(threads_path):
    threads = load_threads(threads_path)
    reminders = []
    #one reminder per unanswered line, posted as a reply inside that line's own
    #Teams conversation — a reply belongs to exactly one message_id, so these
    #cannot be grouped per owner. Replying in-thread is also what lets the poller
    #pick the answer up: GET /messages/{id}/replies only sees replies under {id}.
    for thread in threads["threads"]:
        if thread["has_reply"]:
            continue
        reminders.append({
            "canonical_id": thread["canonical_id"],
            "name": thread["name"],
            "question": thread["question"],
            "owner_name": thread["owner_name"],
            "owner_email": thread["owner_email"],
            "message_id": thread["message_id"],
            "reminder_text": (f"Reminder — {thread['owner_name']}, still waiting for your "
                              f"reply on {thread['name']}."),
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