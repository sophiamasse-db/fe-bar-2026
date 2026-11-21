"""Evaluate the AI scenario briefs (EVAL_PROTOCOL.md section B) with MLflow 3 GenAI judges from a different model
family than the generator, and write one row per brief x judge.

Reads  : gold_scenario_briefs
Writes : ai_eval_results (scenario, judge, pass, rationale, prompt_version), MLflow evaluation run
"""
import argparse
import json

import mlflow
import pandas as pd
from mlflow.genai.scorers import Guidelines
from pyspark.sql import SparkSession

JUDGES = {
    "grounded": "Every number, percentage, ticker, company name and date in the outputs appears in, or is directly "
                "computed from, the facts given in the inputs. Rounding is acceptable.",
    "no_invention": "The outputs do not mention any person, company, ticker, price, date, document or event that is "
                    "not present in the facts given in the inputs. The single sentence stating that full details will "
                    "follow in the official announcement is required by the instructions and is allowed; any other "
                    "document, guidance, event or instruction to recipients is not.",
    "compliant_tone": "The outputs are factual and neutral. They give no investment advice, no buy/sell "
                      "recommendation and no promise about future performance.",
    "actionable_notice": "The client_notice states the effective date, lists the additions and removals by ticker (or "
                         "says there are none), and says that full details will follow in the official announcement.",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--schema", required=True)
    ap.add_argument("--judge-endpoint", required=True)
    a = ap.parse_args()
    cat, sch = a.catalog, a.schema
    spark = SparkSession.builder.getOrCreate()
    briefs = spark.sql(f"""SELECT scenario_id, facts_json, brief.impact_summary AS impact_summary, brief.client_notice AS client_notice,
                                  to_json(brief.key_risks) AS key_risks, prompt_version, model_name
                           FROM {cat}.{sch}.gold_scenario_briefs WHERE brief IS NOT NULL""").toPandas()
    if briefs.empty:
        raise SystemExit("No successful briefs in gold_scenario_briefs - check error_message from ai_briefs")
    data = [{"inputs": {"facts": r.facts_json},
             "outputs": {"impact_summary": r.impact_summary, "client_notice": r.client_notice, "key_risks": r.key_risks}}
            for r in briefs.itertuples()]
    model = f"databricks:/{a.judge_endpoint}"
    scorers = [Guidelines(name=n, guidelines=g, model=model) for n, g in JUDGES.items()]

    me = spark.sql("SELECT current_user()").first()[0]
    mlflow.set_experiment(f"/Users/{me}/nextdaq_scenario_briefs_eval")
    pv = briefs["prompt_version"].iloc[0]
    with mlflow.start_run(run_name=f"briefs_eval_{pv}") as run:
        res = mlflow.genai.evaluate(data=data, scorers=scorers)
        mlflow.log_params({"prompt_version": pv, "generator": briefs["model_name"].iloc[0], "judge": a.judge_endpoint})

    # Per-row results come from the same evaluation run (one source of truth; judges are not fully deterministic)
    by_scenario = {json.loads(r.facts_json)["scenario"]: r for r in briefs.itertuples()}
    rows = []
    for tr in mlflow.search_traces(run_id=run.info.run_id, return_type="list"):
        req = tr.data.request
        req = json.loads(req) if isinstance(req, str) else req
        sid = json.loads(req["facts"])["scenario"]
        for asm in tr.info.assessments or []:
            if asm.name not in JUDGES:
                continue
            val = asm.feedback.value if getattr(asm, "feedback", None) is not None else getattr(asm, "value", None)
            rows.append({"scenario_id": sid, "judge": asm.name, "passed": str(val).lower() in ("yes", "true", "pass"),
                         "rationale": (asm.rationale or "")[:600], "prompt_version": pv,
                         "generator": by_scenario[sid].model_name, "judge_model": a.judge_endpoint,
                         "mlflow_run_id": run.info.run_id})
    out = pd.DataFrame(rows)
    out["evaluated_at"] = pd.Timestamp.now(tz="UTC").isoformat()
    tbl = f"{cat}.{sch}.ai_eval_results"
    sdf = spark.createDataFrame(out)
    if spark.catalog.tableExists(tbl):
        spark.sql(f"DELETE FROM {tbl} WHERE prompt_version = '{pv}'")      # rerun of a version replaces it; others stay
        sdf.write.mode("append").option("mergeSchema", "true").saveAsTable(tbl)
    else:
        sdf.write.saveAsTable(tbl)
    by_judge = out.groupby("judge")["passed"].mean().round(3).to_dict()
    all_pass = out.groupby("scenario_id")["passed"].all()
    print(json.dumps({"prompt_version": pv, "rows": len(briefs), "judges": list(JUDGES), "pass_rate_by_judge": by_judge,
                      "rows_passing_all_judges": int(all_pass.sum()), "share_passing_all": round(float(all_pass.mean()), 3),
                      "mlflow_run_id": run.info.run_id, "aggregate_metrics": {k: round(v, 3) for k, v in res.metrics.items()}}))


if __name__ == "__main__":
    main()
