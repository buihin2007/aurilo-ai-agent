import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from glossary_and_helpers import BU_PREFIXES

def bold_md_to_html(text, color="#1B4B4A"):
    return re.sub(
        r"\*\*(.+?)\*\*",
        rf'<strong style="color:{color};">\1</strong>',
        text,
    )

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

# Email-safe CSS: no custom properties, no color-mix, no CSS grid/flexbox —
# Outlook's rendering engine does not support any of those. Layout uses
# plain HTML <table>s only. Flat hex values throughout.
HTML_TEMPLATE = """
<div style="max-width:1180px;margin:0 auto;font-family:Arial,Helvetica,sans-serif;background:#FFFFFF;border:1px solid #E1E0D9;border-top:3px solid #1B4B4A;border-radius:4px;padding:28px 30px 26px;color:#14181C;">

  <table width="100%" cellpadding="0" cellspacing="0"><tr>
    <td valign="top" style="width:1%;white-space:nowrap;">
      <p style="font-size:11px;font-weight:bold;letter-spacing:1px;text-transform:uppercase;color:#1B4B4A;margin:0 0 6px;white-space:nowrap;">Aurilo Group — __BU__</p>
      <h1 style="font-size:21px;font-weight:bold;margin:0 0 4px;white-space:nowrap;">Closing Variance Commentary
        <span style="display:inline-block;font-size:10px;font-weight:bold;letter-spacing:1px;text-transform:uppercase;color:#A9790C;background:#F7F0DE;border:1px solid #A9790C;border-radius:3px;padding:2px 7px;margin-left:8px;">Draft</span>
      </h1>
      <p style="font-size:13px;color:#5B6066;margin:0 0 16px;">__PERIOD_LABEL__ · Current Forecast vs Prior FC</p>
      <p style="font-size:11.5px;color:#5B6066;margin:0;">
        <span style="display:inline-block;width:10px;height:10px;background:#A8412F;border-radius:2px;margin-right:5px;"></span>below Prior FC&nbsp;&nbsp;
        <span style="display:inline-block;width:10px;height:10px;background:#2F7A52;border-radius:2px;margin-right:5px;"></span>above Prior FC
      </p>
    </td>
    <td width="32" style="width:32px;"></td>
    <td valign="top" style="padding-top:2px;">
      <p style="font-size:10px;font-weight:bold;letter-spacing:.5px;text-transform:uppercase;color:#5B6066;margin:0 0 6px;">Summary</p>
      <p style="font-size:13px;line-height:1.5;color:#14181C;margin:0;">__SUMMARY__</p>
    </td>
  </tr></table>

  <table style="width:100%;border-collapse:collapse;font-size:13px;margin-top:20px;">
    <thead>
      <tr>
        <th align="left" style="font-size:10px;font-weight:bold;letter-spacing:.5px;text-transform:uppercase;color:#5B6066;padding:8px 10px 8px 0;border-bottom:1px solid #E1E0D9;">Line</th>
        <th align="right" style="font-size:10px;font-weight:bold;letter-spacing:.5px;text-transform:uppercase;color:#5B6066;padding:8px 10px;border-bottom:1px solid #E1E0D9;">Prior FC</th>
        <th align="center" style="font-size:10px;font-weight:bold;letter-spacing:.5px;text-transform:uppercase;color:#5B6066;padding:8px 10px;border-bottom:1px solid #E1E0D9;">vs Prior FC</th>
        <th align="right" style="font-size:10px;font-weight:bold;letter-spacing:.5px;text-transform:uppercase;color:#5B6066;padding:8px 10px;border-bottom:1px solid #E1E0D9;">%</th>
        <th align="right" style="font-size:10px;font-weight:bold;letter-spacing:.5px;text-transform:uppercase;color:#5B6066;padding:8px 10px;border-bottom:1px solid #E1E0D9;">Cur FC</th>
        <th align="left" style="font-size:10px;font-weight:bold;letter-spacing:.5px;text-transform:uppercase;color:#5B6066;padding:8px 10px;border-bottom:1px solid #E1E0D9;border-left:1px solid #E1E0D9;">Reasons</th>
      </tr>
    </thead>
    <tbody>
      __ROWS__
    </tbody>
  </table>

  <div style="margin-top:10px;padding-top:10px;font-size:12.5px;color:#5B6066;">
    <div style="margin-bottom:6px;">__MATERIALITY__</div>
    <div>Draft prepared by AI agent — pending Finance review before use.</div>
  </div>
</div>
"""

ROW_TEMPLATE = """
<tr>
  <td style="padding:12px 10px 12px 0;border-bottom:1px solid #E1E0D9;font-weight:bold;white-space:nowrap;">
    <span style="display:inline-block;width:17px;height:17px;line-height:17px;text-align:center;border-radius:50%;background:#E3ECEB;color:#1B4B4A;font-size:10px;font-weight:bold;margin-right:7px;">{rank}</span>{name}
  </td>
  <td align="right" style="padding:12px 10px;border-bottom:1px solid #E1E0D9;color:#5B6066;white-space:nowrap;">{pre_fc}</td>
  <td align="center" style="padding:12px 10px;border-bottom:1px solid #E1E0D9;white-space:nowrap;">
    <table cellpadding="0" cellspacing="0" style="margin:0 auto;"><tr>
      <td style="width:45px;text-align:right;">{left_bar}</td>
      <td style="width:1px;background:#E1E0D9;font-size:1px;">&nbsp;</td>
      <td style="width:45px;text-align:left;">{right_bar}</td>
    </tr></table>
  </td>
  <td align="right" style="padding:12px 10px;border-bottom:1px solid #E1E0D9;white-space:nowrap;">
    <span style="display:inline-block;font-size:11.5px;font-weight:bold;padding:1px 6px;border-radius:3px;color:{pct_color};background:{pct_bg};">{pct}</span>
  </td>
  <td align="right" style="padding:12px 10px;border-bottom:1px solid #E1E0D9;color:#5B6066;white-space:nowrap;">{cur_fc}</td>
  <td style="padding:12px 10px;border-bottom:1px solid #E1E0D9;border-left:1px solid #E1E0D9;">
    <span style="font-size:12.5px;line-height:1.4;{reason_style}">{text}</span>{review_badge}
  </td>
</tr>
"""

REVIEW_BADGE = (
    '<span style="display:inline-block;font-size:9px;font-weight:bold;'
    'letter-spacing:.4px;text-transform:uppercase;color:#A9790C;'
    'background:#F7F0DE;border:1px solid #A9790C;border-radius:3px;'
    'padding:1px 5px;margin-left:6px;vertical-align:1px;">Needs review</span>'
)

def render_row(obj, max_abs):
    bar_px = round(abs(obj["vs_pre_fc_eur"]) / max_abs * 45) if max_abs else 0
    bar_html = f'<div style="height:10px;background:#A8412F;display:inline-block;width:{bar_px}px;"></div>'
    negative = obj["vs_pre_fc_eur"] < 0

    if obj["answer_clean"]:
        text, reason_style = bold_md_to_html(obj["answer_clean"], color="#1B4B4A"), "color:#5B6066;"
    else:
        text, reason_style = "Pending explanation", "color:#5B6066;font-style:italic;"
    review_badge = REVIEW_BADGE if obj.get("needs_review") else ""

    return ROW_TEMPLATE.format(
        rank=obj["rank"],
        name=obj["name"],
        pre_fc=f"€{obj['pre_fc']:,.0f}",
        cur_fc=f"€{obj['cur_fc']:,.0f}",
        pct=f"{obj['vs_pre_fc_pct']:+.1%}",
        pct_color="#A8412F" if negative else "#2F7A52",
        pct_bg="#F7EBE8" if negative else "#EAF3EC",
        left_bar=bar_html if negative else "",
        right_bar="" if negative else bar_html,
        text=text,
        reason_style=reason_style,
        review_badge=review_badge,
    )

def render_materiality(materiality):
    return (
        f"Materiality: &gt;€{materiality['pnl_eur']:,.0f} or &gt;{materiality['pnl_pct']:.0%} · "
        f"gross margin &gt;€{materiality['gross_margin_eur']:,.0f} · "
        f"expense &gt;€{materiality['expense_eur']:,.0f} · "
        f"EBITA &gt;€{materiality['ebita_eur']:,.0f}"
    )

def render_html(payload, summary_text):
    max_abs = max(abs(o["vs_pre_fc_eur"]) for o in payload["allowed_objects"])
    rows = "".join(render_row(o, max_abs) for o in payload["allowed_objects"])
    return (HTML_TEMPLATE
            .replace("__BU__", payload["business_unit"])
            .replace("__PERIOD_LABEL__", payload["period"])
            .replace("__SUMMARY__", bold_md_to_html(summary_text))
            .replace("__ROWS__", rows)
            .replace("__MATERIALITY__", render_materiality(payload["materiality"])))

def write_summary(payload):
    lines = "\n".join(
        f"- {o['name']}: {o['vs_pre_fc_eur']:+,.0f} ({o['vs_pre_fc_pct']:+.1%}) — "
        f"{o['answer_clean'] or 'no explanation yet'}"
        for o in payload["allowed_objects"]
    )
    response = get_client().chat.completions.create(
        model=require_env("DEEPSEEK_FLAGSHIP_MODEL"),
        messages=[
            {"role": "system", "content": (
                "You are a finance closing assistant. Write a 2-3 sentence "
                "executive summary of this month's P&L variance for "
                "Current Forecast vs Prior FC. Use only the figures and "
                "explanations given. Do not speculate beyond them. Wrap the "
                "2-4 most important phrases (key drivers, biggest movers, "
                "anything still pending) in **markdown bold**."
            )},
            {"role": "user", "content": lines},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()

def draft_commentary(payload_path):
    with open(payload_path, encoding="utf-8") as file:
        payload = json.load(file)
    summary_text = write_summary(payload)
    draft_html = render_html(payload, summary_text)
    return {
        "period": payload["period"],
        "business_unit": payload["business_unit"],
        "all_answered": payload["all_answered"],
        "summary_text": summary_text,
        "draft_html": draft_html,
    }

if __name__ == "__main__":
    for bu in BU_PREFIXES:
        files = sorted(Path("output/payload").glob(f"{bu}_*.json"), reverse=True)
        if not files:
            print(f"{bu}: no payload file found, skipped.")
            continue
        result = draft_commentary(files[0])
        Path("output/draft_commentary").mkdir(parents=True, exist_ok=True)
        out_path = f"output/draft_commentary/{bu}_{result['period']}.json"
        with open(out_path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)
        print(f"Wrote {out_path}")
