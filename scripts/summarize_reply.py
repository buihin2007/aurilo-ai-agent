from pathlib import Path
import sys
import json

def load_reply_input(path):
    with open(path, encoding="utf-8") as file:
        reply_input = json.load(file)
    for key in {"period", "business_unit", "canonical_id", "name",
                "question", "reply_text", "owner_name", "owner_email"}:
        if not reply_input.get(key):
            raise ValueError(f"{path}: missing or empty field: '{key}'")
    return reply_input

def call_llm(question, reply_text):
    # TODO: replace with real Azure OpenAI (mini deployment) call once the API key/endpoint exist.
    # For now, pass the reply through unchanged so the rest of the pipeline is testable.
    return reply_text.strip()

def summarize_reply(reply_input):
    answer_clean = call_llm(reply_input["question"], reply_input["reply_text"])
    return {**reply_input, "answer_clean": answer_clean}

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python summarize_reply.py <path to reply input json>")
    reply_input_path = sys.argv[1]
    kb_entry = summarize_reply(load_reply_input(reply_input_path))
    bu = kb_entry["business_unit"].lower()
    Path("output/kb_entries").mkdir(parents=True, exist_ok=True)
    out_path = f"output/kb_entries/{bu}_{kb_entry['canonical_id']}_{kb_entry['period']}.json"
    with open(out_path, "w", encoding="utf-8") as file:
        json.dump(kb_entry, file, ensure_ascii=False, indent=2)
    print(f"Wrote {out_path}")
