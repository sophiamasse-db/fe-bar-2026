"""Build preset rebalance scenarios for the upcoming reconstitution with the shared engine, then draft an impact
summary + ETF-issuer notice for each with ai_query (structured output). The LLM explains; it never ranks.

Reads  : gold_universe_monthly (latest snapshot), gold_index_constituents, gold_etf_exposure
Writes : scenario_presets (facts per scenario), gold_scenario_briefs (MNPI: draft text per scenario)
"""
import argparse
import json
import os
import sys
import types

import pandas as pd
from pyspark.sql import SparkSession

EFFECTIVE_DATE = "2026-12-21"   # Monday after the third Friday of December 2026


def load(code_root: str, rel: str, name: str):
    path = os.path.join(code_root.replace("dbfs:", ""), rel)
    mod = types.ModuleType(name)
    mod.__file__ = path
    sys.modules[name] = mod
    exec(compile(open(path).read(), path, "exec"), mod.__dict__)
    return mod


def scenarios(engine):
    R = engine.Rules
    return [
        ("S0_BASELINE", "Baseline: current NextDAQ-100 methodology applied to the latest data", R(), {}),
        ("S1_TIGHTER_CAPS", "Tighter concentration caps: aggregate cap 45% -> target 35%, single-name target 15%",
         R(agg_cap=0.45, agg_target=0.35, single_target=0.15), {}),
        ("S2_STRESS_LARGEST_UP_30", "Stress test: the largest company rises 30% before the reference date", R(), {"shock_top1": 1.30}),
        ("S3_STRESS_TOP7_UP_20", "Stress test: the seven largest companies rise 20% before the reference date", R(), {"shock_top7": 1.20}),
        ("S4_LIQUIDITY_25M", "Higher liquidity floor: 3-month average daily value traded of at least $25M",
         R(liquidity_min_usd=25e6), {}),
        ("S5_EXCLUDE_UTILITIES", "Sector exclusion: utilities are not eligible", R(exclude_sectors=("Utilities",)), {}),
        ("S6_WIDER_BUFFER", "Wider buffer: add at rank 75, keep members ranked up to 125", R(add_rank=75, buffer_rank=125), {}),
        ("S7_STRESS_TOP7_DOWN_25", "Stress test: the seven largest companies fall 25% before the reference date", R(), {"shock_top7": 0.75}),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--schema", required=True)
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--code-root", required=True)
    a = ap.parse_args()
    cat, sch = a.catalog, a.schema
    engine = load(a.code_root, "app/engine.py", "engine")
    prompts = load(a.code_root, "app/prompts.py", "prompts")
    spark = SparkSession.builder.getOrCreate()

    u = spark.sql(f"""SELECT ticker, company_name, sector, is_financial, market_cap, adv_usd_3m AS adv_usd, in_index, snapshot_date
                      FROM {cat}.{sch}.gold_universe_monthly
                      WHERE snapshot_date = (SELECT max(snapshot_date) FROM {cat}.{sch}.gold_universe_monthly)""").toPandas()
    current = spark.table(f"{cat}.{sch}.gold_index_constituents").select("ticker", "weight").toPandas()
    aum = float(spark.sql(f"SELECT max_by(total_aum_usd, as_of_date) FROM {cat}.{sch}.gold_etf_exposure").first()[0])
    as_of = str(u["snapshot_date"].max())
    names = u.set_index("ticker")["company_name"]
    members = set(u.loc[u["in_index"], "ticker"])

    rows = []
    for sid, desc, rules, shock in scenarios(engine):
        x = u.copy()
        top = x.sort_values("market_cap", ascending=False)["ticker"]
        if "shock_top1" in shock:
            x.loc[x["ticker"] == top.iloc[0], "market_cap"] *= shock["shock_top1"]
        if "shock_top7" in shock:
            x.loc[x["ticker"].isin(top.iloc[:7]), "market_cap"] *= shock["shock_top7"]
        prop, _ = engine.build_index(x, members, rules)
        k, trades = engine.scenario_kpis(current, prop[["ticker", "weight"]], x.set_index("ticker")["adv_usd"], aum)
        k0, _ = engine.scenario_kpis(current, current, x.set_index("ticker")["adv_usd"], aum)
        cap_check = engine.needs_capping(prop.set_index("ticker")["market_cap"] / prop["market_cap"].sum(), rules)
        rk = prop.set_index("ticker")["rank"]
        adds = trades[trades["action"] == "ADD"].sort_values("weight_after", ascending=False)
        rems = trades[trades["action"] == "REMOVE"]
        facts = {
            "scenario": sid, "event": "proposed NextDAQ-100 rebalance", "description": desc, "as_of_date": as_of,
            "effective_date": EFFECTIVE_DATE, "index": "NextDAQ-100", "aum_tracking_index_usd": round(aum),
            "aum_note": "assets of ETFs and other products tracking the index; trading_impact_usd = assets x weight change",
            "rules": rules.to_dict(),
            "uncapped_concentration": {"max_single_weight_pct": round(cap_check["max_weight"] * 100, 2),
                                       "single_cap_limit_pct": round(rules.single_cap * 100, 2),
                                       "single_cap_breached": cap_check["single_breach"],
                                       "aggregate_large_weight_pct": round(cap_check["aggregate_weight"] * 100, 2),
                                       "aggregate_cap_limit_pct": round(rules.agg_cap * 100, 2),
                                       "aggregate_cap_breached": cap_check["aggregate_breach"],
                                       "note": "before capping; capping is applied in kpis_after"},
            "additions": [{"ticker": t, "company": names.get(t), "rank": int(rk.get(t, 0)), "weight_after_pct": round(w * 100, 2)}
                          for t, w in zip(adds["ticker"], adds["weight_after"])],
            "removals": [{"ticker": t, "company": names.get(t)} for t in rems["ticker"]],
            "kpis_today": {k_: round(v, 2) for k_, v in k0.items() if k_ in ("top10_weight_pct", "max_weight_pct", "hhi")},
            "kpis_after": {k_: round(v, 2) for k_, v in k.items()},
            "largest_trades": [{"ticker": r.ticker, "trade_usd": round(r.trade_usd), "days_to_trade": None if pd.isna(r.days_to_trade) else round(float(r.days_to_trade), 2)}
                               for r in trades.head(5).itertuples()],
        }
        rows.append({"scenario_id": sid, "description": desc, "rules_json": json.dumps(rules.to_dict()),
                     "facts_json": json.dumps(facts), "client_notice": prompts.render_notice(facts), "additions": len(facts["additions"]), "removals": len(facts["removals"]),
                     "turnover_pct": k["turnover_pct"], "top10_weight_pct": k["top10_weight_pct"],
                     "max_weight_pct": k["max_weight_pct"], "hhi": k["hhi"], "trading_impact_usd": k["trading_impact_usd"],
                     "max_days_to_trade": k["max_days_to_trade"], "as_of_date": as_of})
    spark.createDataFrame(pd.DataFrame(rows)).write.mode("overwrite").option("overwriteSchema", "true") \
        .saveAsTable(f"{cat}.{sch}.scenario_presets")

    rf = prompts.response_format_json().replace("'", "\\'")
    instr = prompts.INSTRUCTIONS.replace("'", "\\'")
    spark.sql(f"""
CREATE OR REPLACE TABLE {cat}.{sch}.gold_scenario_briefs
COMMENT 'MNPI: per preset scenario, an AI-drafted impact summary + key risks (ai_query, structured output) and a templated ETF-issuer notice. Drafts, reviewed by a person before use.'
AS WITH r AS (
  SELECT *, ai_query('{a.endpoint}', concat('{instr}', facts_json),
                     responseFormat => '{rf}', modelParameters => named_struct('temperature', 0.0), failOnError => false) AS resp
  FROM {cat}.{sch}.scenario_presets
)
SELECT scenario_id, description, as_of_date, facts_json, additions, removals, turnover_pct, top10_weight_pct, max_weight_pct,
  hhi, trading_impact_usd, max_days_to_trade,
  named_struct('impact_summary', from_json(resp.result, 'impact_summary STRING, key_risks ARRAY<STRING>').impact_summary,
               'client_notice', CASE WHEN resp.result IS NOT NULL THEN client_notice END,
               'key_risks', from_json(resp.result, 'impact_summary STRING, key_risks ARRAY<STRING>').key_risks) AS brief,
  resp.errorMessage AS error_message, '{a.endpoint}' AS model_name, '{prompts.PROMPT_VERSION}' AS prompt_version,
  current_timestamp() AS generated_at
FROM r""")
    s = spark.sql(f"SELECT count(*) n, count_if(brief.impact_summary IS NOT NULL) ok, count_if(error_message IS NOT NULL) errors "
                  f"FROM {cat}.{sch}.gold_scenario_briefs").first()
    print(json.dumps({"scenarios": len(rows), "briefs_ok": s["ok"], "errors": s["errors"], "model": a.endpoint,
                      "prompt_version": prompts.PROMPT_VERSION, "as_of": as_of,
                      "baseline_adds": rows[0]["additions"], "baseline_removes": rows[0]["removals"]}))


if __name__ == "__main__":
    main()
