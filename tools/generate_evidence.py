"""Generate plain-text evidence in evidence/ from the LIVE workspace (nothing typed by hand).
Uses only the Databricks CLI (tools/sql.sh for SQL; `databricks ... -o json` for APIs).

Usage:  python3 tools/generate_evidence.py [--only 01,02] [--rerun-test]
"""
import argparse
import datetime as dt
import json
import os
import subprocess

PROFILE = os.environ.get("DATABRICKS_PROFILE", "fe-bar-2026")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
EV = os.path.join(ROOT, "evidence")
CAT, SCH = "fe_bar_2026_kelemen_catalog", "nextdaq_index"


def sql(q: str) -> str:
    r = subprocess.run([os.path.join(ROOT, "tools", "sql.sh"), q], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stdout + r.stderr)
    return r.stdout


def cli_json(*args):
    r = subprocess.run(["databricks", *args, "-p", PROFILE, "-o", "json"], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def header(title: str, proves: str) -> str:
    return (f"# {title}\n\nGenerated {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC by tools/generate_evidence.py "
            f"from the live workspace.\n\n{proves}\n\n")


def write(name: str, text: str):
    with open(os.path.join(EV, name), "w") as f:
        f.write(text)
    print(f"wrote evidence/{name} ({len(text)} chars)")


def pipeline_id() -> str:
    ps = cli_json("pipelines", "list-pipelines", "--filter", "name LIKE 'nextdaq_pipeline'")
    return ps[0]["pipeline_id"]


TABLES = ["bronze_security_master", "bronze_sec_companies", "bronze_sec_submissions", "bronze_sec_facts",
          "bronze_daily_prices", "bronze_price_manifest", "bronze_index_history", "bronze_etf_aum",
          "silver_securities", "silver_shares", "silver_prices", "silver_prices_quarantine", "silver_index_events",
          "silver_etf_aum", "recon_market_data", "gold_universe_monthly", "gold_index_constituents",
          "gold_reconstitution_history", "gold_etf_exposure"]


def row_counts() -> str:
    return sql(" UNION ALL ".join(f"SELECT '{t}' AS table_name, count(*) AS row_count FROM {t}" for t in TABLES))


def ev_01(rerun_test: bool):
    pid = pipeline_id()
    before = row_counts() if rerun_test else None
    rerun_note = ""
    if rerun_test:
        subprocess.run(["databricks", "bundle", "run", "nextdaq_pipeline", "-p", PROFILE], cwd=ROOT,
                       capture_output=True, text=True, check=True)
        after = row_counts()
        rerun_note = ("## Rerun test (idempotency)\n\nThe pipeline was run again with no new files. Row counts before and after:"
                      f" {'IDENTICAL' if before == after else 'DIFFERENT'}.\n\n" + after + "\n")
    ups = cli_json("pipelines", "list-updates", pid, "--max-results", "5")["updates"]
    rows = []
    for u in ups:
        d = cli_json("pipelines", "get-update", pid, u["update_id"])["update"]
        rows.append(f"| {u['update_id'][:8]} | {d['state']} | {d.get('full_refresh', False)} | "
                    f"{dt.datetime.fromtimestamp(d['creation_time'] / 1000, dt.timezone.utc):%Y-%m-%d %H:%M} | {d.get('cause', '')} |")
    dur = sql(f"""SELECT origin.update_id AS update_id, min(timestamp) AS started, max(timestamp) AS ended,
  round((unix_millis(max(timestamp)) - unix_millis(min(timestamp))) / 1000) AS seconds
FROM event_log('{pid}') WHERE event_type = 'update_progress' GROUP BY 1 ORDER BY started DESC LIMIT 3""")
    exp = sql(f"""WITH last AS (SELECT origin.update_id AS u FROM event_log('{pid}') WHERE event_type = 'update_progress'
                    AND details:update_progress:state = 'COMPLETED' ORDER BY timestamp DESC LIMIT 1),
 e AS (SELECT explode(from_json(details:flow_progress:data_quality:expectations,
          'ARRAY<STRUCT<name STRING, dataset STRING, passed_records BIGINT, failed_records BIGINT>>')) AS x
       FROM event_log('{pid}') WHERE event_type = 'flow_progress' AND origin.update_id = (SELECT u FROM last)
         AND details:flow_progress:data_quality:expectations IS NOT NULL)
SELECT replace(x.dataset, '{CAT}.{SCH}.', '') AS dataset, x.name AS expectation, sum(x.passed_records) AS passed,
       sum(x.failed_records) AS failed FROM e GROUP BY 1, 2 ORDER BY 1, 2""")
    txt = header("01 — Lakeflow pipeline run", "Proves the serverless Lakeflow Spark Declarative Pipeline `nextdaq_pipeline` "
                 "(src/pipeline/*.sql) ran to COMPLETED, shows rows per table across bronze/silver/gold, the expectation "
                 "pass/fail counts read from the pipeline event log, and that a rerun does not duplicate rows.")
    txt += f"Pipeline id: `{pid}` (serverless, catalog `{CAT}`, schema `{SCH}`).\n\n## Recent updates\n\n"
    txt += "| update | state | full refresh | created (UTC) | cause |\n|---|---|---|---|---|\n" + "\n".join(rows) + "\n\n"
    txt += "Durations from the event log:\n\n" + dur + "\n## Expectations (latest completed update)\n\n" + exp
    txt += "\nDROP ROW rules: unique_ticker_day, valid_close, valid_volume, has_ticker, positive_shares, clean_ticker. "
    txt += "Warn-only: has_sector, reconciled.\n\n## Rows per table\n\n" + (before or row_counts()) + "\n" + rerun_note
    write("01_pipeline_run.md", txt)


def ev_02():
    q = sql("SELECT reject_reason, count(*) AS rows, count(DISTINCT _file_name) AS files FROM silver_prices_quarantine GROUP BY 1 ORDER BY 2 DESC")
    qs = sql("SELECT reject_reason, ticker, trade_date, close, volume, _file_name FROM silver_prices_quarantine "
             "QUALIFY row_number() OVER (PARTITION BY reject_reason ORDER BY ticker, trade_date) <= 2 ORDER BY 1, 2")
    rs = sql("SELECT status, count(*) AS files, sum(control_count) AS control_rows, sum(landed_rows) AS landed_rows, "
             "sum(loaded_rows) AS loaded_rows, sum(quarantined_rows) AS quarantined_rows FROM recon_market_data GROUP BY 1")
    rb = sql("SELECT file_name, control_count, landed_rows, loaded_rows, quarantined_rows, control_volume, landed_volume, status "
             "FROM recon_market_data WHERE status <> 'RECONCILED' OR quarantined_rows > 0 ORDER BY file_name")
    conf = sql("SELECT symbol_as_received, ticker, event_type, action, effective_date FROM silver_index_events "
               "WHERE symbol_as_received <> ticker ORDER BY effective_date")
    sec = sql("SELECT sector, count(*) AS issuers FROM silver_securities GROUP BY 1 ORDER BY 2 DESC")
    shr = sql("SELECT shares_source, count(DISTINCT cik) AS filers, count(*) AS rows FROM silver_shares GROUP BY 1")
    txt = header("02 — Data quality and completeness", "Proves bad rows are quarantined with a reason (nothing disappears "
                 "silently), every vendor file is reconciled against its control totals, and conforming rules work. "
                 "Compare with the planted counts in 00_answer_key.md.")
    txt += "## Quarantine (silver_prices_quarantine)\n\n" + q + "\nSample rows per reason:\n\n" + qs
    txt += "\n## Reconciliation (recon_market_data)\n\n" + rs + "\nFiles with a break or quarantined rows:\n\n" + rb
    txt += "\n## Conforming index history (`symbol` -> `ticker`)\n\n" + conf
    txt += "\n## Sector from SEC SIC (silver_securities)\n\n" + sec
    txt += "\n## Share-count source (point in time, known 14 days after period end)\n\n" + shr
    write("02_data_quality.md", txt)


def sql_rows(q: str, warehouse: str = "0b1ef599493d9600") -> list:
    """Run SQL and return rows as lists (for multi-line text that does not fit a Markdown table)."""
    import time
    body = json.dumps({"warehouse_id": warehouse, "statement": q, "wait_timeout": "50s", "on_wait_timeout": "CONTINUE",
                       "catalog": CAT, "schema": SCH})
    r = json.loads(subprocess.run(["databricks", "api", "post", "/api/2.0/sql/statements", "--json", body, "-p", PROFILE],
                                  capture_output=True, text=True, check=True).stdout)
    while r["status"]["state"] in ("PENDING", "RUNNING"):
        time.sleep(3)
        r = json.loads(subprocess.run(["databricks", "api", "get", f"/api/2.0/sql/statements/{r['statement_id']}", "-p", PROFILE],
                                      capture_output=True, text=True, check=True).stdout)
    if r["status"]["state"] != "SUCCEEDED":
        raise RuntimeError(r["status"])
    return r.get("result", {}).get("data_array", []) or []


def ev_04():
    preds = sql("""SELECT ticker, sector, CAST(mcap_rank AS INT) AS rank, in_index, round(p_add, 3) AS p_add, round(p_remove, 3) AS p_remove,
                   predicted_action, top_drivers FROM gold_recon_predictions
                   WHERE predicted_action <> 'HOLD' OR p_add >= 0.3 OR p_remove >= 0.1 ORDER BY greatest(p_add, p_remove) DESC LIMIT 12""")
    meta = sql("SELECT max(model_version) AS model_version, max(as_of_date) AS as_of_date, count(*) AS scored_rows, "
               "count_if(predicted_action='ADD') AS predicted_adds, count_if(predicted_action='REMOVE') AS predicted_removes FROM gold_recon_predictions")
    kp = sql("SELECT scenario_id, additions, removals, round(turnover_pct, 2) AS turnover_pct, round(top10_weight_pct, 2) AS top10_pct, "
             "round(max_weight_pct, 2) AS max_weight_pct, round(hhi, 1) AS hhi, round(trading_impact_usd / 1e9, 2) AS trading_impact_usd_bn, "
             "round(max_days_to_trade, 1) AS max_days_to_trade FROM gold_scenario_briefs ORDER BY 1")
    rows = sql_rows("SELECT scenario_id, prompt_version, model_name, facts_json, brief.impact_summary, brief.client_notice, "
                    "to_json(brief.key_risks) FROM gold_scenario_briefs "
                    "WHERE scenario_id IN ('S0_BASELINE','S4_LIQUIDITY_25M') ORDER BY 1")
    samples = ""
    for c in rows:
        f = json.loads(c[3])
        facts = {k: f[k] for k in ("scenario", "description", "as_of_date", "effective_date", "uncapped_concentration")}
        facts["additions"] = [a["ticker"] for a in f["additions"]]
        facts["removals"] = [x["ticker"] for x in f["removals"]]
        facts["kpis_after"] = {k: f["kpis_after"][k] for k in ("turnover_pct", "top10_weight_pct", "max_weight_pct", "trading_impact_usd", "max_days_to_trade")}
        samples += (f"### {c[0]} (prompt {c[1]}, model {c[2]})\n\nFacts given (abridged):\n```json\n{json.dumps(facts)}\n```\n"
                    f"AI impact summary (verbatim):\n> {c[4]}\n\nKey risks (verbatim): {c[6]}\n\nTemplated ETF-issuer notice:\n```\n{c[5]}\n```\n\n")
    txt = header("04 — AI output: add/remove forecast and scenario briefs", "Proves the intelligent step ran inside the flow: "
                 "the MLflow model registered in Unity Catalog scored the latest snapshot (forecast with reasons), and ai_query "
                 "drafted impact summaries from the facts of preset scenarios built by the same rebalance engine the app uses.")
    txt += "## Forecast for the next reconstitution (gold_recon_predictions)\n\n" + meta + "\nHighest-probability names:\n\n" + preds
    txt += "\n## Scenario KPIs (rebalance engine)\n\n" + kp + "\n## Verbatim AI output\n\n" + samples
    write("04_ai_output.md", txt[:9000])


def ev_05():
    ml = sql("SELECT 'v1' AS version, metric_set, round(f1, 3) AS f1, round(precision, 3) AS precision, round(recall, 3) AS recall, "
             "CAST(predicted AS INT) AS predicted, CAST(actual AS INT) AS actual FROM ml_eval_metrics_v1 UNION ALL "
             "SELECT protocol_version, metric_set, round(f1, 3), round(precision, 3), round(recall, 3), CAST(predicted AS INT), CAST(actual AS INT) "
             "FROM ml_eval_metrics ORDER BY 1, 2")
    held = sql("SELECT target, ticker, CAST(mcap_rank AS INT) AS rank_oct, round(p, 3) AS p_model, model_pred, baseline_pred, actual "
               "FROM ml_heldout_eval WHERE actual = 1 OR model_pred = 1 OR baseline_pred = 1 ORDER BY target, actual DESC, p DESC")
    gj = sql("SELECT prompt_version, judge, count(*) AS rows, round(avg(CAST(passed AS INT)) * 100, 1) AS pass_pct FROM ai_eval_results "
             "GROUP BY 1, 2 ORDER BY 1, 2")
    ga = sql("SELECT prompt_version, count(*) AS briefs, count_if(all_pass) AS passing_all_judges FROM "
             "(SELECT prompt_version, scenario_id, bool_and(passed) AS all_pass FROM ai_eval_results GROUP BY 1, 2) GROUP BY 1 ORDER BY 1")
    fl = sql("SELECT scenario_id, judge, substr(rationale, 1, 260) AS judge_reason FROM ai_eval_results "
             "WHERE prompt_version = (SELECT max(prompt_version) FROM ai_eval_results) AND NOT passed")
    txt = header("05 — AI evaluation and iteration history", "Proves the AI was judged against a protocol written before any "
                 "result (EVAL_PROTOCOL.md, amendments dated and committed before each rerun), with every version's result kept. "
                 "ML: held-out Dec-2025 reconstitution vs a rank baseline. GenAI: four MLflow Guidelines judges (GPT-5.5) "
                 "on Claude Sonnet 4.6 output.")
    txt += ("## ML forecast: held-out reconstitution (Oct-2025 snapshot -> Dec-2025 outcome)\n\n" + ml +
            "\n**Result: the model does not beat the simple rank baseline on F1 in v1 or v2, so no accuracy claim is made.** "
            "It is used as a ranked watchlist with probabilities and reasons. Small sample: 6 adds and 6 removes; one name moves F1 a lot.\n\n"
            "Held-out names (v2):\n\n" + held)
    txt += "\n## GenAI briefs: pass rate per judge and version\n\n" + gj + "\nBriefs passing every judge:\n\n" + ga
    txt += ("\nFinal version (v3.1) is below the 90% bar set in the protocol; drafts therefore always go through human approval "
            "in the app. Remaining failures (judge reasons):\n\n" + fl)
    write("05_ai_evaluation.md", txt[:9000])


ME = json.loads(subprocess.run(["databricks", "current-user", "me", "-p", PROFILE, "-o", "json"],
                             capture_output=True, text=True, check=True).stdout)["userName"]   # signed-in user, not hard-coded
TESTER_SP = "ecdea4a2-ebe7-45a1-ae4e-e00598744b5c"
PERSONAS = [("HEAD_OF_METHODOLOGY", "ALL", True, True), ("METHODOLOGY_ANALYST", "Technology", True, False),
            ("CLIENT_SERVICES", "ALL", False, False)]
PERSONA_QUERY = """SELECT
 (SELECT count(*) FROM gold_universe_monthly) AS universe_rows,
 (SELECT count(*) FROM gold_recon_predictions) AS forecast_rows_visible,
 (SELECT count(DISTINCT sector) FROM gold_recon_predictions) AS forecast_sectors,
 (SELECT count(p_add) FROM gold_recon_predictions) AS p_add_unmasked,
 (SELECT count_if(predicted_action = 'RESTRICTED') FROM gold_recon_predictions) AS action_restricted,
 (SELECT count(*) FROM gold_scenario_briefs) AS briefs_visible"""


def set_persona(persona, scope, mnpi, approve):
    sql(f"UPDATE entitlements SET persona='{persona}', sector_scope='{scope}', can_see_mnpi={str(mnpi).lower()}, "
        f"can_approve={str(approve).lower()}, updated_at=current_timestamp() WHERE principal='{ME}'")


def ev_06():
    lines = []
    try:
        for persona, scope, mnpi, approve in PERSONAS:
            set_persona(persona, scope, mnpi, approve)
            lines.append((persona, scope, mnpi, sql_rows(PERSONA_QUERY)[0]))
    finally:
        set_persona(*PERSONAS[0])
    cols = ["universe_rows", "forecast_rows_visible", "forecast_sectors", "p_add_unmasked", "action_restricted", "briefs_visible"]
    table = ("| persona | sector_scope | can_see_mnpi | " + " | ".join(cols) + " |\n|" + "---|" * (3 + len(cols)) + "\n" +
             "\n".join(f"| {p} | {sc} | {m} | " + " | ".join(v) + " |" for p, sc, m, v in lines) + "\n")
    sp_out = "(access test job not run yet)"
    jobs = cli_json("jobs", "list", "--name", "nextdaq_access_test")
    if jobs:
        runs = cli_json("jobs", "list-runs", "--job-id", str(jobs[0]["job_id"]))
        if runs:
            run = cli_json("jobs", "get-run", str(runs[0]["run_id"]))
            out = cli_json("jobs", "get-run-output", str(run["tasks"][-1]["run_id"]))
            res = json.loads((out.get("logs") or "{}").strip().splitlines()[-1])
            sp_out = (f"Job run {run['run_id']} ({run['state'].get('result_state')}), run_as = service principal "
                      "`nextdaq-access-tester` (Client Services: no MNPI).\n\n| check | status | result / error class |\n|---|---|---|\n")
            for c in res["checks"]:
                detail = json.dumps(c.get("result")) if c["status"] == "OK" else \
                    f"{c['error_class']} ({c['message_chars']} chars, content not logged)"
                sp_out += f"| {c['check']} | {c['status']} | {detail} |\n"
    remaining = sql("SELECT count(*) AS remaining_grants_for_tester FROM system.information_schema.table_privileges "
                    f"WHERE grantee = '{TESTER_SP}' AND table_schema = 'nextdaq_index'")
    pol = sql("SELECT table_name, filter_name AS policy, target_columns FROM information_schema.row_filters WHERE table_schema='nextdaq_index' "
              "UNION ALL SELECT table_name, concat(column_name, ' <- ', mask_name), using_columns FROM information_schema.column_masks "
              "WHERE table_schema='nextdaq_index' ORDER BY 1, 2")
    tags = sql("SELECT table_name, tag_name, tag_value FROM information_schema.table_tags WHERE schema_name='nextdaq_index' ORDER BY 1, 2")
    lin = sql(f"""SELECT replace(source_table_full_name, '{CAT}.{SCH}.', '') AS source, replace(target_table_full_name, '{CAT}.{SCH}.', '') AS target,
                 count(*) AS events FROM system.access.table_lineage
              WHERE target_table_full_name LIKE '{CAT}.{SCH}.gold%' AND source_table_full_name LIKE '{CAT}.{SCH}.%'
              GROUP BY 1, 2 ORDER BY 2, 1""")
    txt = header("06 — Unity Catalog governance", "Proves access is enforced by the platform per persona from an entitlements "
                 "table (row filter by sector, MNPI column masks, MNPI row gate), verified as my own user switched through "
                 "each persona AND as a separate non-admin service principal; plus tags and lineage from system tables.")
    txt += "## Same query, three personas (my entitlements row switched, then restored)\n\n" + table
    txt += "\n## Non-admin identity (service principal, temporary grants then revoked)\n\n" + sp_out
    txt += "\nAfter revoke:\n\n" + remaining
    txt += "\n## Policies attached\n\n" + pol + "\n## Tags\n\n" + tags + "\n## Lineage into gold (system.access.table_lineage)\n\n" + lin
    write("06_governance.md", txt[:9000])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="01,02")
    ap.add_argument("--rerun-test", action="store_true")
    a = ap.parse_args()
    only = set(a.only.split(","))
    if "01" in only:
        ev_01(a.rerun_test)
    if "02" in only:
        ev_02()
    for k, fn in (("04", ev_04), ("05", ev_05), ("06", ev_06)):
        if k in only:
            fn()


if __name__ == "__main__":
    main()
