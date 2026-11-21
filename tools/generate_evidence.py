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


if __name__ == "__main__":
    main()
