from pathlib import Path
import sys
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# Real key/endpoint live in .env (already git-ignored) — never hardcode here.
# PILOT ONLY: pointed at DeepSeek for the blind test. When Aurilo provide an
# Azure OpenAI deployment, this becomes AzureOpenAI(api_key, api_version,
# azure_endpoint) and the model becomes their deployment name.
load_dotenv()

def require_env(name):
    """Fail with the variable name rather than letting the provider return an
    opaque error later — n8n does not surface stdout, only the exit code."""
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"missing or empty environment variable: '{name}' (check .env)")
    return value

def get_client():
    return OpenAI(
        api_key=require_env("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )

def load_reply_input(path):
    with open(path, encoding="utf-8") as file:
        reply_input = json.load(file)
    for key in {"period", "business_unit", "canonical_id", "name",
                "question", "reply_text", "owner_name", "owner_email"}:
        if not reply_input.get(key):
            raise ValueError(f"{path}: missing or empty field: '{key}'")
    return reply_input

def call_llm(question, reply_text):
    response = get_client().chat.completions.create(
        model=require_env("DEEPSEEK_MINI_MODEL"),
        messages=[
            {"role": "system", "content": (
                "You review a Finance owner's reply explaining a P&L variance. "
                "Return JSON with two fields: \"answer_clean\" (a short, factual "
                "one-sentence summary of the reply, no speculation — wrap the "
                "single key driver phrase, e.g. the root cause, in **markdown "
                "bold**) and \"is_relevant\" (true if the reply actually answers "
                "the question asked, false if it looks off-topic or unrelated)."
            )},
            {"role": "user", "content": f"Question: {question}\nReply: {reply_text}"},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)

def summarize_reply(reply_input):
    result = call_llm(reply_input["question"], reply_input["reply_text"])
    return {
        **reply_input,
        "answer_clean": result["answer_clean"],
        "needs_review": not result["is_relevant"],
    }

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
