"""Access test run AS the non-admin service principal `nextdaq-access-tester` (Client Services persona: public data
yes, MNPI no). Logs only status, row counts and error classes - never table contents.

Expected: public gold readable; forecast rows visible but MNPI columns masked; briefs return zero rows; a join on a
masked column finds nothing; an ungranted table is denied the same way as an ungranted harmless probe table.
"""
import argparse
import json

from pyspark.sql import SparkSession


def run(spark, label, sql):
    try:
        rows = [r.asDict() for r in spark.sql(sql).collect()]
        return {"check": label, "status": "OK", "result": rows[0] if len(rows) == 1 else {"rows": len(rows)}}
    except Exception as e:  # record the error class and size only
        msg = str(e)
        cls = msg.split("]")[0].lstrip("[") if msg.startswith("[") else type(e).__name__
        return {"check": label, "status": "ERROR", "error_class": cls, "message_chars": len(msg)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--schema", required=True)
    a = ap.parse_args()
    s = f"{a.catalog}.{a.schema}"
    spark = SparkSession.builder.getOrCreate()
    checks = [
        ("identity", "SELECT current_user() IS NOT NULL AS has_identity, current_user() LIKE '%@%' AS is_human_user"),
        ("public_gold_read", f"SELECT count(*) AS rows FROM {s}.gold_universe_monthly"),
        ("forecast_rows_and_masks", f"""SELECT count(*) AS rows_visible, count(p_add) AS p_add_not_null,
               count_if(predicted_action = 'RESTRICTED') AS action_restricted, count_if(top_drivers = 'RESTRICTED') AS drivers_restricted
               FROM {s}.gold_recon_predictions"""),
        ("join_on_masked_column", f"""SELECT count(*) AS likely_adds_found FROM {s}.gold_recon_predictions p
               JOIN {s}.gold_universe_monthly u ON u.ticker = p.ticker AND u.snapshot_date = p.as_of_date WHERE p.p_add >= 0.5"""),
        ("mnpi_briefs_rows", f"SELECT count(*) AS rows_visible FROM {s}.gold_scenario_briefs"),
        ("protected_table_read", f"SELECT count(*) AS rows FROM {s}.entitlements"),
        ("probe_table_read_same_permissions", f"SELECT count(*) AS rows FROM {s}.zz_access_probe"),
    ]
    out = [run(spark, l, q) for l, q in checks]
    print(json.dumps({"persona": "CLIENT_SERVICES (service principal)", "checks": out}, default=str))


if __name__ == "__main__":
    main()
