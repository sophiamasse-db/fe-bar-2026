"""Create/patch the NextDAQ Genie space, export it to src/genie/space.json, run the approved benchmarks through the
Genie Conversation API and write evidence/08_genie.md (expected vs Genie, match or mismatch).

Usage: python3 tools/genie.py [--skip-benchmarks]
Needs only the Databricks CLI (profile fe-bar-2026). Runs as the signed-in user, so UC policies apply.
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
import uuid

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "src", "genie"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from benchmarks import QUESTIONS, S  # noqa: E402
from generate_evidence import header, sql_rows, write  # noqa: E402

PROFILE = os.environ.get("DATABRICKS_PROFILE", "fe-bar-2026")
WAREHOUSE = "0b1ef599493d9600"
SPACE_ID = "01f1e5d540d61ef3b6d757b4cb45a66e"   # also the genie_space_id variable in databricks.yml; "" creates a new space
TITLE = "NextDAQ-100 Index Methodology Genie"

INSTRUCTIONS = """You answer questions from the NextDAQ index methodology team and the index business about the NextDAQ-100.
Definitions:
- "Latest snapshot" = the most recent snapshot_date in gold_universe_monthly. Always filter to one snapshot_date unless a trend is asked.
- "The cutoff" = rank 100 (mcap_rank). "Within N places of the cutoff" = mcap_rank between 100-N and 100+N.
- Methodology bands: non-members ranked 90 or better are added; members ranked 110 or better are kept; members ranked worse than 110 are at risk of removal.
- mcap_rank only exists for eligible securities (non-financial, 3-month average daily value traded >= $5M). NULL rank = ineligible.
- Weights are fractions (0-1); show them as percentages with 2 decimals.
- "Current index" = gold_index_constituents (members at the latest snapshot with capped weights).
- "Assets tracking the index" = total_aum_usd in gold_etf_exposure (use the latest as_of_date unless a date is asked).
- "ETF trading impact" of a name = current capped weight x latest total assets tracking the index (USD).
- "Reconstitution" = event_type ANNUAL_RECONSTITUTION; "special rebalance" = event_type SPECIAL_REBALANCE.
- Report annual reconstitutions by year: year(effective_date) AS year.
- "Over the last N months" for snapshots = the latest snapshot plus the N month-end snapshots before it (N+1 rows):
  snapshot_date >= add_months(<latest snapshot_date>, -N).
- Forecast columns (p_add, p_remove, predicted_action) are MNPI; they are masked for users who are not cleared. If they come back NULL or RESTRICTED, say the user is not cleared to see them.
Do not give investment advice. Use tickers in answers, with company names where helpful."""

TABLES = {
    "gold_etf_exposure": {"as_of_date": "Month-end date", "total_aum_usd": "Assets of all products tracking the index (USD)",
                          "product_code": "Product ticker of the ETF or fund", "aum_usd": "Assets of this product (USD)"},
    "gold_index_constituents": {"ticker": "Security ticker", "weight": "Capped index weight (fraction 0-1)",
                                "weight_uncapped": "Market-cap weight before capping (fraction 0-1)",
                                "adv_usd_3m": "3-month average daily value traded (USD)", "sector": "Sector from SEC SIC code"},
    "gold_recon_predictions": {"ticker": "Security ticker", "p_add": "Probability of being added at the next reconstitution",
                               "p_remove": "Probability of being removed at the next reconstitution",
                               "predicted_action": "ADD, REMOVE or HOLD", "top_drivers": "Plain-language reasons for the forecast"},
    "gold_reconstitution_history": {"effective_date": "Date the change took effect", "event_type": "INITIAL_COMPOSITION, ANNUAL_RECONSTITUTION or SPECIAL_REBALANCE",
                                    "action": "ADD, REMOVE or REWEIGHT", "rank_at_reference": "Market-cap rank on the reference date"},
    "gold_universe_monthly": {"snapshot_date": "Month-end snapshot date (latest = current month to date)",
                              "mcap_rank": "Rank by market cap among eligible securities (1 = largest)",
                              "in_index": "Member of the NextDAQ-100 on that date", "eligible": "Meets the eligibility rules",
                              "adv_usd_3m": "3-month average daily value traded (USD)", "sector": "Sector from SEC SIC code"},
}
EXAMPLES = [
    ("Which securities are within 3 places of the cutoff on the latest snapshot?",
     f"SELECT ticker, company_name, mcap_rank, in_index FROM {S}.gold_universe_monthly\nWHERE snapshot_date = (SELECT max(snapshot_date) FROM {S}.gold_universe_monthly)\n  AND mcap_rank BETWEEN 97 AND 103\nORDER BY mcap_rank"),
    ("What is the ETF trading impact of the current top 5 names?",
     f"SELECT c.ticker, round(c.weight * a.total_aum_usd) AS trading_impact_usd\nFROM {S}.gold_index_constituents c\nCROSS JOIN (SELECT max_by(total_aum_usd, as_of_date) AS total_aum_usd FROM {S}.gold_etf_exposure) a\nORDER BY c.weight DESC LIMIT 5"),
]


def api(method, path, body=None):
    args = ["databricks", "api", method, path, "-p", PROFILE]
    if body is not None:
        args += ["--json", json.dumps(body)]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stdout + r.stderr)
    return json.loads(r.stdout or "{}")


def lines(t):
    return t.splitlines(keepends=True) or [t]


def build_space() -> dict:
    tables = []
    for t, cols in sorted(TABLES.items()):
        tables.append({"identifier": f"{S}.{t}", "column_configs": [
            {"column_name": c, "description": [d], "enable_format_assistance": True,
             **({"enable_entity_matching": True} if c in ("ticker", "sector", "event_type", "action", "predicted_action") else {})}
            for c, d in sorted(cols.items())]})
    u, c, h, p, e = (f"{S}.gold_universe_monthly", f"{S}.gold_index_constituents", f"{S}.gold_reconstitution_history",
                     f"{S}.gold_recon_predictions", f"{S}.gold_etf_exposure")
    joins = [
        ({"identifier": c, "alias": "constituents"}, {"identifier": u, "alias": "universe"},
         "`constituents`.`ticker` = `universe`.`ticker` AND `constituents`.`snapshot_date` = `universe`.`snapshot_date`"),
        ({"identifier": h, "alias": "history"}, {"identifier": u, "alias": "universe"},
         "`history`.`ticker` = `universe`.`ticker` AND `history`.`reference_date` = `universe`.`snapshot_date`"),
        ({"identifier": p, "alias": "forecast"}, {"identifier": c, "alias": "constituents"}, "`forecast`.`ticker` = `constituents`.`ticker`"),
    ]
    return {
        "version": 2,
        "config": {"sample_questions": [{"id": uuid.uuid4().hex, "question": [q]} for _, q, _, _ in QUESTIONS[:5] + QUESTIONS[13:]]},
        "data_sources": {"tables": tables},
        "instructions": {
            "text_instructions": [{"id": uuid.uuid4().hex, "content": lines(INSTRUCTIONS)}],
            "example_question_sqls": [{"id": uuid.uuid4().hex, "question": [q], "sql": lines(s)} for q, s in EXAMPLES],
            "join_specs": [{"id": uuid.uuid4().hex, "left": l, "right": r,
                            "sql": [j, "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"]} for l, r, j in joins],
        },
        "benchmarks": {"questions": [{"id": uuid.uuid4().hex, "question": [q], "answer": [{"format": "SQL", "content": lines(s)}]}
                                     for _, q, s, _ in QUESTIONS]},
    }


def sort_ids(space: dict) -> dict:
    """The API requires every id-keyed list to be sorted by id."""
    for path in (("config", "sample_questions"), ("instructions", "text_instructions"),
                 ("instructions", "example_question_sqls"), ("instructions", "join_specs"), ("benchmarks", "questions")):
        node = space
        for k in path[:-1]:
            node = node[k]
        node[path[-1]] = sorted(node[path[-1]], key=lambda x: x["id"])
    return space


def upsert_space() -> str:
    body = {"title": TITLE, "description": "Plain-English questions on NextDAQ-100 rank, membership, history, forecast and ETF exposure. Governed gold tables only.",
            "warehouse_id": WAREHOUSE, "serialized_space": json.dumps(sort_ids(build_space()))}
    if SPACE_ID:
        sid = SPACE_ID
        api("patch", f"/api/2.0/genie/spaces/{sid}", body)
    else:
        me = subprocess.run(["databricks", "current-user", "me", "-p", PROFILE, "-o", "json"], capture_output=True, text=True, check=True)
        body["parent_path"] = f"/Workspace/Users/{json.loads(me.stdout)['userName']}"
        sid = api("post", "/api/2.0/genie/spaces", body)["space_id"]
        print(f"created space {sid}: set SPACE_ID here and genie_space_id in databricks.yml")
    got = api("get", f"/api/2.0/genie/spaces/{sid}?include_serialized_space=true")
    space = json.loads(got["serialized_space"])
    with open(os.path.join(ROOT, "src", "genie", "space.json"), "w") as f:
        json.dump(space, f, indent=1)
    print(f"space {sid}: {len(space['data_sources']['tables'])} tables, {len(space['benchmarks']['questions'])} benchmarks")
    return sid


def ask(sid, q):
    m = api("post", f"/api/2.0/genie/spaces/{sid}/start-conversation", {"content": q})
    cid, mid = m["conversation_id"], m["message_id"]
    for _ in range(90):
        msg = api("get", f"/api/2.0/genie/spaces/{sid}/conversations/{cid}/messages/{mid}")
        if msg.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
            break
        time.sleep(4)
    att = next((a for a in msg.get("attachments", []) if a.get("query")), None)
    text = " ".join(a.get("text", {}).get("content", "") for a in msg.get("attachments", []) if a.get("text"))
    if not att:
        return {"status": msg.get("status"), "sql": None, "rows": [], "text": text}
    res = api("get", f"/api/2.0/genie/spaces/{sid}/conversations/{cid}/messages/{mid}/query-result/{att['attachment_id']}")
    rows = res.get("statement_response", {}).get("result", {}).get("data_array", []) or []
    return {"status": msg.get("status"), "sql": att["query"].get("query"), "rows": rows, "text": text or att["query"].get("description", "")}


def norm(v):
    if v is None:
        return set()
    try:
        x = float(v)
        out = {f"{x:.4g}", f"{x * 100:.4g}", f"{round(x)}"}
        return out
    except ValueError:
        return {str(v).strip().upper()}


def compare(expected, got, key):
    exp_keys = set().union(*[norm(r[key]) for r in expected]) if expected else set()
    got_vals = set().union(*[norm(v) for r in got for v in r]) if got else set()
    keys_ok = all(norm(r[key]) & got_vals for r in expected)
    return keys_ok and len(got) == len(expected), keys_ok, len(expected), len(got)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-benchmarks", action="store_true")
    a = ap.parse_args()
    sid = upsert_space()
    if a.skip_benchmarks:
        return
    rows, summary = [], []
    for i, (qid, q, s, key) in enumerate(QUESTIONS):
        expected = sql_rows(s)
        g = ask(sid, q)
        match, keys_ok, ne, ng = compare(expected, g["rows"], key)
        verdict = "MATCH" if match else ("KEYS MATCH, ROW COUNT DIFFERS" if keys_ok else "MISMATCH")
        summary.append((qid, verdict))
        exp_txt = ", ".join(str(r[key]) for r in expected[:8]) + (" ..." if len(expected) > 8 else "")
        got_txt = "; ".join(", ".join(str(v) for v in r[:3]) for r in g["rows"][:4]) + (" ..." if len(g["rows"]) > 4 else "")
        rows.append(f"| {qid} | {q} | {ne} rows: {exp_txt} | {ng} rows: {got_txt} | **{verdict}** |")
        print(qid, verdict, flush=True)
        time.sleep(13)   # stay under the Genie rate limit (5 questions per minute)
    n = sum(v == "MATCH" for _, v in summary)
    txt = header("08 — Genie agent benchmark", f"Proves the Genie space `{TITLE}` (id {sid}; definition in src/genie/space.json) answers "
                 "the approved business questions correctly over the governed gold tables: each question was asked through the "
                 "Genie Conversation API as the signed-in user and compared with ground-truth SQL from src/genie/benchmarks.py.")
    txt += f"**Result: {n} of {len(QUESTIONS)} exact matches.**\n\n| id | question | expected (key column) | Genie answer (first columns) | verdict |\n|---|---|---|---|---|\n"
    txt += "\n".join(rows) + "\n"
    write("08_genie.md", txt[:9000])


if __name__ == "__main__":
    main()
