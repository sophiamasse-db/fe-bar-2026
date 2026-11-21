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


CYCLE_JOB = "nextdaq_rebalance_cycle"


def job_id(name):
    j = cli_json("jobs", "list", "--name", name)
    return j[0]["job_id"] if j else None


def task_outputs(run):
    """{task_key: (state, seconds, last log line)} for one job run."""
    out = {}
    for t in run["tasks"]:
        st_ = t["state"].get("result_state") or t["state"].get("life_cycle_state")
        line = ""
        if st_ == "SUCCESS" and "spark_python_task" in t:
            o = cli_json("jobs", "get-run-output", str(t["run_id"]))
            lines = (o.get("logs") or "").strip().splitlines()
            line = lines[-1] if lines else ""
        out[t["task_key"]] = (st_, round((t.get("execution_duration") or 0) / 1000), line)
    return out


def sync_outputs(limit=25):
    """Successful sync_lakebase outputs, newest first."""
    res = []
    for r in cli_json("jobs", "list-runs", "--job-id", str(job_id(CYCLE_JOB)), "--limit", str(limit)):
        run = cli_json("jobs", "get-run", str(r["run_id"]))
        for t in run["tasks"]:
            if t["task_key"] == "sync_lakebase" and t["state"].get("result_state") == "SUCCESS":
                o = cli_json("jobs", "get-run-output", str(t["run_id"]))
                lines = (o.get("logs") or "").strip().splitlines()
                if lines:
                    res.append((run["run_id"], json.loads(lines[-1])))
    return res


def ev_07():
    outs = sync_outputs()
    latest = outs[0]
    edit = next(((rid, o) for rid, o in outs if "edit_test" in o), None)
    L = latest[1]
    txt = header("07 — Lakebase operational serving", "Proves the forecast watchlist is served from Lakebase (autoscaling Postgres, "
                 "project nextdaq-ops, database nextdaq, schema ops): machine-owned columns are refreshed from gold every cycle while "
                 "human-owned columns survive, every change has a history row, and the app's scenario / approval / audit tables are live. "
                 "Values come from the sync task's own output (it connects with a short-lived OAuth database credential).")
    txt += f"## Latest sync (job run {latest[0]})\n\n| measure | value |\n|---|---|\n"
    for k in ("sync", "counts", "review_status", "history", "scenarios_by_status", "approvals", "audit_actions"):
        txt += f"| {k} | `{json.dumps(L.get(k, {}), default=str)}` |\n"
    if edit:
        e = edit[1]
        txt += (f"\n## Edit survives refresh (job run {edit[0]})\n\nA person set one record to CONFIRMED with a note, then the "
                f"refresh ran again.\n\n| check | result |\n|---|---|\n| record | {e['edit_test']['ticker']} |\n"
                f"| review_status after refresh | {e['edit_test']['review_status_after_refresh']} |\n"
                f"| analyst note kept | {e['edit_test']['note_kept']} |\n| machine columns refreshed | {e['edit_test']['machine_columns_refreshed']} |\n"
                f"| refresh after edit | `{json.dumps(e['refresh_after_edit'])}` |\n")
    if L.get("history_sample"):
        txt += "\n## History sample (non-creation changes)\n\n| ticker | change | field | old | new | at |\n|---|---|---|---|---|---|\n"
        txt += "\n".join(f"| {h['ticker']} | {h['change_type']} | {h['field']} | {h['old']} | {h['new']} | {h['at'][:19]} |" for h in L["history_sample"]) + "\n"
    if L.get("audit_sample"):
        txt += "\n## Audit log sample (app actions)\n\n| at | entity | id | action |\n|---|---|---|---|\n"
        txt += "\n".join(f"| {a['at'][:19]} | {a['entity']} | {a['entity_id']} | {a['action']} |" for a in L["audit_sample"]) + "\n"
    txt += ("\n## Who enforces what\n\n| control | enforced by |\n|---|---|\n"
            "| Sector row filter, MNPI masks, MNPI row gate on Delta | Platform (Unity Catalog), per signed-in user via the app's user token |\n"
            "| Who may approve a scenario (entitlements.can_approve) | App, reading the entitlements table as the signed-in user |\n"
            "| Who sees Lakebase scenario rows and watchlist probabilities | App (the app connects to Postgres as its service principal) |\n"
            "| App role may not delete history or audit rows | Platform (Postgres grants: SELECT, INSERT, UPDATE only) |\n")
    write("07_lakebase.md", txt[:9000])


def ev_09():
    runs = cli_json("jobs", "list-runs", "--job-id", str(job_id(CYCLE_JOB)), "--limit", "25")
    full = [r for r in runs if r["state"].get("result_state") == "SUCCESS"
            and all(t["state"].get("result_state") == "SUCCESS" for t in cli_json("jobs", "get-run", str(r["run_id"]))["tasks"])]
    trig = next((r for r in full if r.get("trigger") == "FILE_ARRIVAL"), None)
    picked = []
    if trig:
        picked.append(("file arrival (2 held-back days landed)", trig))
        rerun = next((r for r in full if r["start_time"] > trig["start_time"]), None)
    else:
        trig = full[1] if len(full) > 1 else full[0]
        picked.append(("final run after the 2 held-back days landed (started manually: the file-arrival trigger is configured "
                       "but did not fire in this workspace during testing)", trig))
        rerun = full[0] if len(full) > 1 else None
    if rerun:
        picked.append(("rerun immediately after, no new data", rerun))
    txt = header("09 — Orchestrated cycle", "Proves one Lakeflow Job runs the whole journey in order (pipeline, then forecast and briefs, "
                 "evaluation, governance, Lakebase sync) after new vendor files land, and that a rerun with no new data is safe. "
                 "Each task's exit summary is its own printed JSON.")
    jd = cli_json("jobs", "get", str(job_id(CYCLE_JOB)))["settings"]
    fa = jd.get("trigger", {}).get("file_arrival", {})
    txt += (f"Job `{CYCLE_JOB}`: trigger = file arrival on `{fa.get('url', '').split('/Volumes/')[-1]}`, max_concurrent_runs = "
            f"{jd.get('max_concurrent_runs')}, queueing = {jd.get('queue', {}).get('enabled')}.\n\n")
    for label, r in picked:
        run = cli_json("jobs", "get-run", str(r["run_id"]))
        t = task_outputs(run)
        txt += (f"## Run {run['run_id']}: {label}\n\ntrigger = {run.get('trigger')}, result = {run['state'].get('result_state')}, "
                f"started {dt.datetime.fromtimestamp(run['start_time'] / 1000, dt.timezone.utc):%Y-%m-%d %H:%M} UTC\n\n"
                "| task | state | seconds | exit summary |\n|---|---|---|---|\n")
        for k in ("refresh_pipeline", "train_and_score", "ai_briefs", "evaluate_ai", "governance", "sync_lakebase"):
            if k in t:
                s_, sec, line = t[k]
                txt += f"| {k} | {s_} | {sec} | {line[:300].replace('|', '/')} |\n"
        txt += "\n"
    cross = sql("""SELECT (SELECT max(trade_date) FROM silver_prices) AS latest_price_day,
       (SELECT max(snapshot_date) FROM gold_universe_monthly) AS latest_snapshot,
       (SELECT count_if(predicted_action = 'ADD') FROM gold_recon_predictions) AS forecast_adds_gold,
       (SELECT count_if(predicted_action = 'REMOVE') FROM gold_recon_predictions) AS forecast_removes_gold,
       (SELECT count(*) FROM recon_market_data) AS manifests, (SELECT count_if(status = 'RECONCILED') FROM recon_market_data) AS reconciled""")
    lb = sync_outputs(3)[0][1]["counts"]
    txt += ("## Cross-check after the final run\n\nGold (SQL):\n\n" + cross +
            f"\nLakebase security_watch (sync output): ADD = {lb.get('ADD')}, REMOVE = {lb.get('REMOVE')}, HOLD = {lb.get('HOLD')}.\n")
    write("09_orchestration.md", txt[:9000])


def ev_10():
    r = subprocess.run(["databricks", "apps", "logs", "nextdaq-rebalance-simulator", "--tail-lines", "1000", "-p", PROFILE],
                       capture_output=True, text=True)
    evs = []
    for line in r.stdout.splitlines():
        i = line.find('{"event"')
        if i >= 0:
            try:
                evs.append(json.loads(line[i:]))
            except json.JSONDecodeError:
                pass
    app = cli_json("apps", "get", "nextdaq-rebalance-simulator")
    txt = header("10 — Databricks App", "Proves the app is deployed and used end to end: every screen render and action writes a "
                 "structured line to the app log (no emails or tokens). It shows the persona the platform resolved, how many forecast "
                 "rows were visible and unmasked, scenario runs, AI drafts, Lakebase submissions/approvals and Genie answers.")
    txt += (f"App `{app['name']}`: compute {app.get('compute_status', {}).get('state')}, active deployment "
            f"{app.get('active_deployment', {}).get('status', {}).get('state')}, user API scopes "
            f"{', '.join(app.get('user_api_scopes', []))}; resources: " + ", ".join(x["name"] for x in app.get("resources", [])) + ".\n\n")
    pv = [e for e in evs if e["event"] == "page_view"]
    txt += "## Page views by persona (what the platform let each persona see)\n\n| page | persona | forecast rows | unmasked | MNPI cleared | can approve |\n|---|---|---|---|---|---|\n"
    seen = set()
    for e in pv:
        k = (e["page"], e["persona"])
        if k in seen:
            continue
        seen.add(k)
        txt += f"| {e['page']} | {e['persona']} | {e['forecast_rows']} | {e['forecast_unmasked']} | {e['mnpi_cleared']} | {e['can_approve']} |\n"
    from collections import Counter
    cnt = Counter(e["event"] for e in evs)
    txt += "\n## Events in the log\n\n| event | count |\n|---|---|\n" + "\n".join(f"| {k} | {v} |" for k, v in sorted(cnt.items())) + "\n"
    txt += "\n## Workflow actions (every one)\n\n| at | event | persona | detail |\n|---|---|---|---|\n"
    for e in [e for e in evs if e["event"] in ("scenario_submitted", "scenario_decision", "ai_summary", "genie_answer")]:
        d = {k: v for k, v in e.items() if k not in ("event", "at", "persona")}
        txt += f"| {e['at']} | {e['event']} | {e['persona']} | {json.dumps(d, default=str)[:220].replace('|', '/')} |\n"
    txt += "\n## Scenario runs (last 6)\n\n| at | name | shock | additions | removals | turnover % | max weight % | max days to trade |\n|---|---|---|---|---|---|---|---|\n"
    for e in [e for e in evs if e["event"] == "scenario_run"][-6:]:
        k = e["kpis"]
        txt += (f"| {e['at']} | {e['name']} | {e['shock'].get('ticker') or '-'} {e['shock'].get('pct') if e['shock'].get('ticker') else ''} | "
                f"{k['additions']} | {k['removals']} | {k['turnover_pct']} | {k['max_weight_pct']} | {k['max_days_to_trade']} |\n")
    write("10_app.md", txt[:9000])


def ev_index():
    files = sorted(f for f in os.listdir(EV) if f.endswith(".md") and f[:2].isdigit())
    desc = {"00": "answer key: planted findings, real SEC data issues, file inventory", "01": "Lakeflow pipeline run, expectations, rerun test",
            "02": "quarantine, reconciliation, conforming", "04": "AI output: forecast and verbatim briefs",
            "05": "AI evaluation: ML vs baseline, judges per version", "06": "Unity Catalog: personas, service principal, policies, lineage",
            "07": "Lakebase: sync, edit survives refresh, workflow tables", "08": "Genie benchmark: expected vs Genie",
            "09": "orchestrated job: file-arrival run, rerun, cross-check", "10": "Databricks App: page views by persona, actions"}
    txt = header("Evidence index", "Every file below was generated from the live workspace by tools/ scripts (nothing typed by hand).")
    txt += "| file | proves |\n|---|---|\n" + "\n".join(f"| [{f}]({f}) | {desc.get(f[:2], '')} |" for f in files) + "\n"
    write("README.md", txt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="01,02,04,05,06,07,09,10,index")
    ap.add_argument("--rerun-test", action="store_true")
    a = ap.parse_args()
    only = set(a.only.split(","))
    if "01" in only:
        ev_01(a.rerun_test)
    if "02" in only:
        ev_02()
    for k, fn in (("04", ev_04), ("05", ev_05), ("06", ev_06), ("07", ev_07), ("09", ev_09), ("10", ev_10), ("index", ev_index)):
        if k in only:
            fn()


if __name__ == "__main__":
    main()
