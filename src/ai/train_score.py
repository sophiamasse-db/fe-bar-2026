"""Train, evaluate (per EVAL_PROTOCOL.md section A), register and batch-score the NextDAQ-100 add/remove forecast.

Reads  : gold_universe_monthly, gold_reconstitution_history
Writes : ml_heldout_eval (held-out predictions + baseline), ml_eval_metrics, gold_recon_predictions
Model  : <catalog>.<schema>.recon_classifier (MLflow, Unity Catalog registry)

Protocol recap: snapshot = month-end; label = outcome of the NEXT annual reconstitution (reference = Nov month-end).
Train on snapshots whose next reconstitution is 2022-2024. Held out: the Oct-2025 snapshot -> Dec-2025 outcome.
Baseline: add if non-member ranked <= 100; remove if member ranked > 100. Main measure: F1 per class.
"""
import argparse
import json
from datetime import datetime, timezone

import mlflow
import numpy as np
import pandas as pd
from mlflow.models import infer_signature
from pyspark.sql import SparkSession
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import f1_score, precision_score, recall_score

FEATURES = ["mcap_rank", "ranks_from_cutoff", "log_market_cap", "log_adv", "liquidity_ratio", "return_1m",
            "return_3m", "rank_change_3m", "months_to_reference", "eligible_flag", "inside_add_band", "outside_keep_band"]
PROTOCOL_VERSION = "v2"   # EVAL_PROTOCOL.md amendment 1: band features + CV-chosen threshold
HELD_OUT_YEAR, HELD_OUT_SNAPSHOT_MONTH = 2025, 10
PARAMS = dict(max_iter=200, learning_rate=0.05, max_depth=3, min_samples_leaf=20, l2_regularization=1.0, random_state=7)


class ReconClassifier(mlflow.pyfunc.PythonModel):
    """Two gradient-boosted classifiers behind one model: P(add | non-member), P(remove | member)."""

    def __init__(self, add_model, remove_model):
        self.add_model, self.remove_model = add_model, remove_model

    def predict(self, context, model_input: pd.DataFrame, params=None) -> pd.DataFrame:
        X = model_input[FEATURES].astype(float)
        member = model_input["in_index_flag"].astype(int).values == 1
        p_add = np.where(member, 0.0, self.add_model.predict_proba(X)[:, 1])
        p_remove = np.where(member, self.remove_model.predict_proba(X)[:, 1], 0.0)
        return pd.DataFrame({"p_add": p_add, "p_remove": p_remove})


def features(spark, cat, sch) -> pd.DataFrame:
    u = spark.table(f"{cat}.{sch}.gold_universe_monthly").toPandas()
    u["snapshot_date"] = pd.to_datetime(u["snapshot_date"])
    u = u[u["snapshot_date"] >= "2021-12-31"].copy()
    u["eligible_flag"] = u["eligible"].astype(float)
    u["in_index_flag"] = u["in_index"].astype(int)
    u["mcap_rank"] = u["mcap_rank"].fillna(999)
    u["ranks_from_cutoff"] = u["mcap_rank"] - 100
    u["log_market_cap"] = np.log10(u["market_cap"].clip(lower=1))
    u["log_adv"] = np.log10(u["adv_usd_3m"].clip(lower=1))
    u["liquidity_ratio"] = (u["adv_usd_3m"] / 5e6).clip(upper=100)
    u["rank_change_3m"] = (u["mcap_rank_3m_ago"].fillna(999) - u["mcap_rank"]).clip(-500, 500)
    u[["return_1m", "return_3m"]] = u[["return_1m", "return_3m"]].fillna(0.0)
    u["inside_add_band"] = ((u["in_index_flag"] == 0) & (u["mcap_rank"] <= 90)).astype(float)
    u["outside_keep_band"] = ((u["in_index_flag"] == 1) & (u["mcap_rank"] > 110)).astype(float)
    # next reconstitution: reference date = Nov month-end of the snapshot's year (Dec snapshots roll to next year)
    u["recon_year"] = np.where(u["snapshot_date"].dt.month == 12, u["snapshot_date"].dt.year + 1, u["snapshot_date"].dt.year)
    u["months_to_reference"] = (11 - u["snapshot_date"].dt.month) % 12
    h = spark.table(f"{cat}.{sch}.gold_reconstitution_history").toPandas()
    h = h[h["event_type"] == "ANNUAL_RECONSTITUTION"]
    h["recon_year"] = pd.to_datetime(h["effective_date"]).dt.year
    lab = h.pivot_table(index=["recon_year", "ticker"], columns="action", aggfunc="size", fill_value=0).reset_index()
    u = u.merge(lab, on=["recon_year", "ticker"], how="left")
    for c in ("ADD", "REMOVE"):
        u[c] = u.get(c, 0).fillna(0).astype(int)
    return u


def cv_threshold(frame: pd.DataFrame, label: str) -> tuple[float, dict]:
    """Leave-one-reconstitution-out CV on the training years only: pick the threshold with the best mean F1."""
    grid = np.round(np.arange(0.05, 0.95, 0.05), 2)
    scores = {t: [] for t in grid}
    for yr in sorted(frame["recon_year"].unique()):
        tr, va = frame[frame["recon_year"] != yr], frame[frame["recon_year"] == yr]
        va = va[va["months_to_reference"] == 1]           # same horizon as the held-out test (Oct snapshot)
        if va[label].sum() == 0 or tr[label].sum() == 0:
            continue
        p = HistGradientBoostingClassifier(**PARAMS).fit(tr[FEATURES], tr[label]).predict_proba(va[FEATURES])[:, 1]
        for t in grid:
            scores[t].append(f1_score(va[label], (p >= t).astype(int), zero_division=0))
    mean = {float(t): float(np.mean(v)) for t, v in scores.items() if v}
    best = max(mean, key=lambda t: (round(mean[t], 6), -abs(t - 0.5)))
    return best, mean


def drivers(r) -> str:
    out = [f"rank {int(r.mcap_rank) if r.mcap_rank < 999 else 'n/a'} ({'member' if r.in_index_flag else 'non-member'})"]
    if r.in_index_flag and r.mcap_rank > 110:
        out.append("outside the 110 retention band")
    if not r.in_index_flag and r.mcap_rank <= 90:
        out.append("inside the 90 add band")
    if abs(r.rank_change_3m) >= 10 and r.rank_change_3m < 500:
        out.append(f"{'up' if r.rank_change_3m > 0 else 'down'} {abs(int(r.rank_change_3m))} ranks in 3 months")
    if abs(r.return_3m) >= 0.15:
        out.append(f"3-month return {r.return_3m:+.0%}")
    if r.liquidity_ratio < 1.5:
        out.append("liquidity close to the $5M minimum")
    if not r.eligible_flag:
        out.append("currently ineligible")
    return "; ".join(out)


def metrics(y, yhat, k_scores=None, k=None) -> dict:
    m = {"f1": float(f1_score(y, yhat, zero_division=0)), "precision": float(precision_score(y, yhat, zero_division=0)),
         "recall": float(recall_score(y, yhat, zero_division=0)), "predicted": int(np.sum(yhat)), "actual": int(np.sum(y)),
         "true_positive": int(np.sum((np.asarray(y) == 1) & (np.asarray(yhat) == 1)))}
    if k_scores is not None:
        top = np.argsort(-np.asarray(k_scores))[:k]
        m[f"precision_at_{k}"] = float(np.asarray(y)[top].mean()) if k else 0.0
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--schema", required=True)
    a = ap.parse_args()
    cat, sch = a.catalog, a.schema
    spark = SparkSession.builder.getOrCreate()
    mlflow.set_registry_uri("databricks-uc")
    df = features(spark, cat, sch)

    train = df[df["recon_year"].between(2022, HELD_OUT_YEAR - 1)]
    test = df[(df["recon_year"] == HELD_OUT_YEAR) & (df["snapshot_date"].dt.month == HELD_OUT_SNAPSHOT_MONTH)]
    nm_tr, m_tr = train[train["in_index_flag"] == 0], train[train["in_index_flag"] == 1]
    nm_te, m_te = test[test["in_index_flag"] == 0], test[test["in_index_flag"] == 1]

    exp = f"/Users/{spark.sql('SELECT current_user()').first()[0]}/nextdaq_recon_forecast"
    mlflow.set_experiment(exp)
    with mlflow.start_run(run_name="recon_classifier") as run:
        t_add, cv_add = cv_threshold(nm_tr, "ADD")
        t_rem, cv_rem = cv_threshold(m_tr, "REMOVE")
        add_m = HistGradientBoostingClassifier(**PARAMS).fit(nm_tr[FEATURES], nm_tr["ADD"])
        rem_m = HistGradientBoostingClassifier(**PARAMS).fit(m_tr[FEATURES], m_tr["REMOVE"])
        p_add, p_rem = add_m.predict_proba(nm_te[FEATURES])[:, 1], rem_m.predict_proba(m_te[FEATURES])[:, 1]
        mlflow.log_params({"threshold_add": t_add, "threshold_remove": t_rem, "protocol_version": PROTOCOL_VERSION})
        mlflow.log_dict({"add": cv_add, "remove": cv_rem}, "cv_threshold_f1.json")
        k_add, k_rem = int(nm_te["ADD"].sum()), int(m_te["REMOVE"].sum())
        res = {
            "model_add": metrics(nm_te["ADD"], (p_add >= t_add).astype(int), p_add, k_add),
            "baseline_add": metrics(nm_te["ADD"], (nm_te["mcap_rank"] <= 100).astype(int), -nm_te["mcap_rank"], k_add),
            "model_remove": metrics(m_te["REMOVE"], (p_rem >= t_rem).astype(int), p_rem, k_rem),
            "baseline_remove": metrics(m_te["REMOVE"], (m_te["mcap_rank"] > 100).astype(int), m_te["mcap_rank"], k_rem),
        }
        for name, m in res.items():
            mlflow.log_metrics({f"{name}_{k}": v for k, v in m.items()})
        mlflow.log_params({**PARAMS, "features": ",".join(FEATURES), "train_recon_years": "2022-2024",
                           "held_out": f"{HELD_OUT_YEAR} recon, snapshot month {HELD_OUT_SNAPSHOT_MONTH}",
                           "train_rows_non_members": len(nm_tr), "train_rows_members": len(m_tr),
                           "train_pos_add_rows": int(nm_tr["ADD"].sum()), "train_pos_remove_rows": int(m_tr["REMOVE"].sum())})

        held = pd.concat([
            nm_te.assign(p=p_add, model_pred=(p_add >= t_add).astype(int), baseline_pred=(nm_te["mcap_rank"] <= 100).astype(int),
                         actual=nm_te["ADD"], target="ADD"),
            m_te.assign(p=p_rem, model_pred=(p_rem >= t_rem).astype(int), baseline_pred=(m_te["mcap_rank"] > 100).astype(int),
                        actual=m_te["REMOVE"], target="REMOVE")])
        held = held[(held["actual"] == 1) | (held["model_pred"] == 1) | (held["baseline_pred"] == 1) | (held["p"] >= 0.1)]
        held = held[["snapshot_date", "ticker", "company_name", "target", "mcap_rank", "p", "model_pred", "baseline_pred", "actual"]]
        spark.createDataFrame(held).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{cat}.{sch}.ml_heldout_eval")
        rows = [{"protocol_version": PROTOCOL_VERSION, "metric_set": k, "threshold": t_add if "add" in k and k.startswith("model") else (t_rem if k.startswith("model") else None),
                 **{kk: float(vv) for kk, vv in v.items()}} for k, v in res.items()]
        spark.createDataFrame(pd.DataFrame(rows).fillna(0.0)).write.mode("overwrite").option("overwriteSchema", "true") \
            .saveAsTable(f"{cat}.{sch}.ml_eval_metrics")

        # Production model: refit on every labelled reconstitution (2022-2025) and register in UC
        full = df[df["recon_year"].between(2022, HELD_OUT_YEAR)]
        f_nm, f_m = full[full["in_index_flag"] == 0], full[full["in_index_flag"] == 1]
        model = ReconClassifier(HistGradientBoostingClassifier(**PARAMS).fit(f_nm[FEATURES], f_nm["ADD"]),
                                HistGradientBoostingClassifier(**PARAMS).fit(f_m[FEATURES], f_m["REMOVE"]))
        sample = full[FEATURES + ["in_index_flag"]].head(20)
        info = mlflow.pyfunc.log_model(name="recon_classifier", python_model=model, input_example=sample,
                                       signature=infer_signature(sample, model.predict(None, sample)),
                                       registered_model_name=f"{cat}.{sch}.recon_classifier",
                                       pip_requirements=["scikit-learn", "pandas", "numpy"])
        version = info.registered_model_version

    # Batch score the latest snapshot (the upcoming reconstitution)
    latest = df[df["snapshot_date"] == df["snapshot_date"].max()].copy()
    scored = mlflow.pyfunc.load_model(f"models:/{cat}.{sch}.recon_classifier/{version}").predict(latest[FEATURES + ["in_index_flag"]])
    latest["p_add"], latest["p_remove"] = scored["p_add"].values, scored["p_remove"].values
    latest["predicted_action"] = np.select([latest["p_add"] >= t_add, latest["p_remove"] >= t_rem], ["ADD", "REMOVE"], "HOLD")
    latest["top_drivers"] = latest.apply(drivers, axis=1)
    latest["model_version"] = f"recon_classifier/{version}"
    latest["scored_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = latest[["snapshot_date", "ticker", "company_name", "sector", "in_index", "mcap_rank", "market_cap", "adv_usd_3m",
                  "p_add", "p_remove", "predicted_action", "top_drivers", "model_version", "scored_at"]]
    out = out.rename(columns={"snapshot_date": "as_of_date"})
    spark.createDataFrame(out).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{cat}.{sch}.gold_recon_predictions")
    spark.sql(f"COMMENT ON TABLE {cat}.{sch}.gold_recon_predictions IS 'MNPI: forecast of NextDAQ-100 additions/removals at the "
              f"next reconstitution (model recon_classifier v{version}). Index team only.'")

    summary = {"mlflow_run_id": run.info.run_id, "model": f"{cat}.{sch}.recon_classifier", "version": int(version),
               "as_of": str(latest["snapshot_date"].max().date()), "scored_rows": len(out),
               "predicted_adds": int((out["predicted_action"] == "ADD").sum()),
               "predicted_removes": int((out["predicted_action"] == "REMOVE").sum()),
               "protocol_version": PROTOCOL_VERSION, "threshold_add": t_add, "threshold_remove": t_rem,
               **{f"{k}_f1": round(v["f1"], 3) for k, v in res.items()},
               "heldout_actual_adds": res["model_add"]["actual"], "heldout_actual_removes": res["model_remove"]["actual"]}
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
