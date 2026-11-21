"""Operational serving in Lakebase (autoscaling Postgres): upsert the forecast watchlist from gold and own the
app's scenario / approval / audit tables.

security_watch: MACHINE-owned columns are refreshed from gold_recon_predictions every cycle;
                HUMAN-owned columns (review_status, analyst_note, owner) are never touched by the refresh.
watch_history : one row per new record, model-driven change or human edit.
scenarios / approvals / audit_log: written by the app (analyst proposes, head of methodology approves).

Auth: short-lived OAuth database credential from the SDK (no static password). Idempotent: rerun = same rows.
Runs as the job owner, who must be MNPI-cleared (it reads unmasked forecasts); access to Lakebase rows is then
enforced by the app.
"""
import argparse
import json

import psycopg
from databricks.sdk import WorkspaceClient
from pyspark.sql import SparkSession

DB, SCHEMA = "nextdaq", "ops"
MACHINE = ["as_of_date", "company_name", "sector", "in_index", "mcap_rank", "market_cap", "p_add", "p_remove",
           "predicted_action", "top_drivers", "model_version"]

DDL = f"""
CREATE SCHEMA IF NOT EXISTS {SCHEMA};
CREATE TABLE IF NOT EXISTS {SCHEMA}.security_watch (
  ticker            TEXT PRIMARY KEY,
  as_of_date        DATE NOT NULL,
  company_name      TEXT,
  sector            TEXT,
  in_index          BOOLEAN NOT NULL,
  mcap_rank         INT,
  market_cap        DOUBLE PRECISION,
  p_add             DOUBLE PRECISION,
  p_remove          DOUBLE PRECISION,
  predicted_action  TEXT CHECK (predicted_action IN ('ADD','REMOVE','HOLD')),
  top_drivers       TEXT,
  model_version     TEXT,
  refreshed_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  review_status     TEXT NOT NULL DEFAULT 'NEW' CHECK (review_status IN ('NEW','REVIEWING','CONFIRMED','DISMISSED')),
  analyst_note      TEXT,
  owner             TEXT,
  human_updated_by  TEXT,
  human_updated_at  TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS {SCHEMA}.watch_history (
  id          BIGSERIAL PRIMARY KEY,
  ticker      TEXT NOT NULL REFERENCES {SCHEMA}.security_watch(ticker),
  change_type TEXT NOT NULL CHECK (change_type IN ('CREATED','MODEL_CHANGE','HUMAN_EDIT')),
  field       TEXT,
  old_value   TEXT,
  new_value   TEXT,
  changed_by  TEXT NOT NULL,
  changed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS {SCHEMA}.scenarios (
  scenario_id   TEXT PRIMARY KEY,
  name          TEXT NOT NULL,
  rules_json    JSONB NOT NULL,
  kpis_json     JSONB NOT NULL,
  impact_summary TEXT,
  client_notice TEXT,
  status        TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','SUBMITTED','APPROVED','REJECTED')),
  created_by    TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  submitted_at  TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS {SCHEMA}.approvals (
  id          BIGSERIAL PRIMARY KEY,
  scenario_id TEXT NOT NULL REFERENCES {SCHEMA}.scenarios(scenario_id),
  decision    TEXT NOT NULL CHECK (decision IN ('APPROVED','REJECTED')),
  decided_by  TEXT NOT NULL,
  comment     TEXT,
  decided_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS {SCHEMA}.audit_log (
  id        BIGSERIAL PRIMARY KEY,
  entity    TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  action    TEXT NOT NULL,
  actor     TEXT NOT NULL,
  detail    JSONB,
  at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def connect(w: WorkspaceClient, endpoint: str, db: str):
    ep = w.postgres.get_endpoint(name=endpoint)
    cred = w.postgres.generate_database_credential(endpoint=endpoint)
    return psycopg.connect(host=ep.status.hosts.host, port=5432, dbname=db, user=w.current_user.me().user_name,
                           password=cred.token, sslmode="require")


def upsert(cur, rows, actor) -> dict:
    cur.execute(f"SELECT ticker, predicted_action FROM {SCHEMA}.security_watch")
    before = dict(cur.fetchall())
    cols = ["ticker"] + MACHINE
    sets = ", ".join(f"{c} = EXCLUDED.{c}" for c in MACHINE) + ", refreshed_at = now()"
    sql = (f"INSERT INTO {SCHEMA}.security_watch ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))}) "
           f"ON CONFLICT (ticker) DO UPDATE SET {sets}")
    cur.executemany(sql, [[r[c] for c in cols] for r in rows])
    new = [r["ticker"] for r in rows if r["ticker"] not in before]
    changed = [(r["ticker"], before[r["ticker"]], r["predicted_action"]) for r in rows
               if r["ticker"] in before and before[r["ticker"]] != r["predicted_action"]]
    cur.executemany(f"INSERT INTO {SCHEMA}.watch_history (ticker, change_type, changed_by) VALUES (%s, 'CREATED', %s)",
                    [(t, actor) for t in new])
    cur.executemany(f"INSERT INTO {SCHEMA}.watch_history (ticker, change_type, field, old_value, new_value, changed_by) "
                    f"VALUES (%s, 'MODEL_CHANGE', 'predicted_action', %s, %s, %s)", [(t, o, n, actor) for t, o, n in changed])
    return {"upserted": len(rows), "created": len(new), "model_changes": len(changed)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--schema", required=True)
    ap.add_argument("--endpoint", required=True, help="projects/<id>/branches/<b>/endpoints/<e>")
    ap.add_argument("--app-sp", default="", help="app service principal application id to grant (optional)")
    ap.add_argument("--edit-test", action="store_true", help="prove human edits survive a refresh")
    a = ap.parse_args()
    w = WorkspaceClient()
    spark = SparkSession.builder.getOrCreate()
    me = w.current_user.me().user_name

    with connect(w, a.endpoint, "databricks_postgres") as c0:
        c0.autocommit = True
        if not c0.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB,)).fetchone():
            c0.execute(f"CREATE DATABASE {DB}")

    pdf = spark.sql(f"""SELECT ticker, CAST(as_of_date AS DATE) AS as_of_date, company_name, sector, in_index,
                               CAST(mcap_rank AS INT) AS mcap_rank, market_cap, p_add, p_remove, predicted_action,
                               top_drivers, model_version
                        FROM {a.catalog}.{a.schema}.gold_recon_predictions
                        WHERE in_index OR mcap_rank <= 150 OR p_add >= 0.05 OR p_remove >= 0.05""").toPandas()
    def py(k, v):
        if v is None or (isinstance(v, float) and v != v):
            return None
        if k == "in_index":
            return bool(v)
        if k == "mcap_rank":
            return int(v)
        return float(v) if k in ("market_cap", "p_add", "p_remove") else v
    rows = [{k: py(k, v) for k, v in r.items()} for r in pdf.astype(object).where(pdf.notna(), None).to_dict("records")]

    out = {"database": DB, "schema": SCHEMA}
    with connect(w, a.endpoint, DB) as conn, conn.cursor() as cur:
        cur.execute(DDL)
        if a.app_sp:
            cur.execute(f"""DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{a.app_sp}') THEN
                  EXECUTE 'GRANT USAGE ON SCHEMA {SCHEMA} TO "{a.app_sp}"';
                  EXECUTE 'GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA {SCHEMA} TO "{a.app_sp}"';
                  EXECUTE 'GRANT USAGE ON ALL SEQUENCES IN SCHEMA {SCHEMA} TO "{a.app_sp}"';
                END IF; END $$;""")
        out["sync"] = upsert(cur, rows, f"pipeline:{me}")
        conn.commit()

        if a.edit_test:
            t = cur.execute(f"SELECT ticker FROM {SCHEMA}.security_watch WHERE predicted_action <> 'HOLD' ORDER BY ticker LIMIT 1").fetchone()[0]
            note = "Edit-survives-refresh test: analyst confirmed after reviewing liquidity"
            cur.execute(f"UPDATE {SCHEMA}.security_watch SET review_status = 'CONFIRMED', analyst_note = %s, owner = %s, "
                        f"human_updated_by = %s, human_updated_at = now() WHERE ticker = %s", (note, me, me, t))
            cur.execute(f"INSERT INTO {SCHEMA}.watch_history (ticker, change_type, field, old_value, new_value, changed_by) "
                        f"VALUES (%s, 'HUMAN_EDIT', 'review_status', 'NEW', 'CONFIRMED', %s)", (t, me))
            conn.commit()
            before = cur.execute(f"SELECT refreshed_at FROM {SCHEMA}.security_watch WHERE ticker = %s", (t,)).fetchone()[0]
            out["refresh_after_edit"] = upsert(cur, rows, f"pipeline:{me}")
            conn.commit()
            r = cur.execute(f"SELECT review_status, analyst_note = %s, refreshed_at > %s FROM {SCHEMA}.security_watch "
                            f"WHERE ticker = %s", (note, before, t)).fetchone()
            out["edit_test"] = {"ticker": t, "review_status_after_refresh": r[0], "note_kept": r[1], "machine_columns_refreshed": r[2]}

        out["counts"] = dict(cur.execute(f"SELECT predicted_action, count(*) FROM {SCHEMA}.security_watch GROUP BY 1").fetchall())
        out["review_status"] = dict(cur.execute(f"SELECT review_status, count(*) FROM {SCHEMA}.security_watch GROUP BY 1").fetchall())
        out["history"] = dict(cur.execute(f"SELECT change_type, count(*) FROM {SCHEMA}.watch_history GROUP BY 1").fetchall())
        out["scenarios_by_status"] = dict(cur.execute(f"SELECT status, count(*) FROM {SCHEMA}.scenarios GROUP BY 1").fetchall())
        out["approvals"] = dict(cur.execute(f"SELECT decision, count(*) FROM {SCHEMA}.approvals GROUP BY 1").fetchall())
        out["audit_actions"] = dict(cur.execute(f"SELECT action, count(*) FROM {SCHEMA}.audit_log GROUP BY 1").fetchall())
        out["audit_sample"] = [dict(zip(("at", "entity", "entity_id", "action"), r)) for r in cur.execute(
            f"SELECT at, entity, entity_id, action FROM {SCHEMA}.audit_log ORDER BY at DESC LIMIT 6").fetchall()]
        out["history_sample"] = [dict(zip(("ticker", "change_type", "field", "old", "new", "at"), r)) for r in cur.execute(
            f"SELECT ticker, change_type, field, old_value, new_value, changed_at FROM {SCHEMA}.watch_history "
            f"WHERE change_type <> 'CREATED' ORDER BY changed_at DESC LIMIT 5").fetchall()]
    print(json.dumps(out, default=str))


if __name__ == "__main__":
    main()
