"""Prompt, response schema and the templated client notice. Shared by the batch briefs job (src/ai/briefs.py)
and the app (live scenarios), so both use exactly the same wording.

v3 (EVAL_PROTOCOL amendment 2): the LLM writes only the impact summary and key risks; the ETF-issuer notice is a
deterministic template filled from the facts.
"""
import json

PROMPT_VERSION = "v3.1"

INSTRUCTIONS = """You write for the Head of Index Methodology at NextDAQ about ONE proposed NextDAQ-100 rebalance scenario.
Use ONLY the facts in the JSON below. Never invent companies, tickers, numbers, dates, people or documents.
Refer to companies by ticker only. Say a cap is breached only if the facts' breach flag for that cap is true.
If something is an inference rather than a stated fact, say it is likely.
Use neutral language; do not characterise risks beyond the facts.
Return:
- impact_summary: at most 120 words: what changes, the effect on concentration and turnover, the estimated ETF
  trading impact, and the main risk.
- key_risks: up to 3 short phrases.
FACTS (JSON):
"""

RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "scenario_brief",
        "schema": {
            "type": "object",
            "properties": {
                "impact_summary": {"type": "string"},
                "key_risks": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["impact_summary", "key_risks"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}


def response_format_json() -> str:
    return json.dumps(RESPONSE_SCHEMA)


def render_notice(facts: dict) -> str:
    """Deterministic ETF-issuer notice: only facts, plus the one required closing sentence."""
    adds = ", ".join(a["ticker"] for a in facts["additions"]) or "none"
    rems = ", ".join(r["ticker"] for r in facts["removals"]) or "none"
    return (f"{facts['index']} rebalance, effective {facts['effective_date']} (data as of {facts['as_of_date']}).\n"
            f"Additions: {adds}.\nRemovals: {rems}.\n"
            "Full details will follow in the official announcement.")
