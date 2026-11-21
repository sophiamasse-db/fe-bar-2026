# BUILD_PLAN — NextDAQ-100 Rebalance Simulator

Namespace: `fe_bar_2026_kelemen_catalog.nextdaq_index` (abbreviated `ndx.` below). Raw files: `/Volumes/fe_bar_2026_kelemen_catalog/nextdaq_index/landing/`.

## 1. Data flow

```
PUBLIC                          SYNTHETIC (src/data/generate.py)
symbol directory (txt) ─┐       daily prices + volume (csv/day) + manifest ─┐
SEC tickers + SIC (json)┤       index history (csv, uses `symbol`)         ┤
SEC dei facts (jsonl)  ─┘       ETF AUM (json/month)                       ─┘
          │  src/data/land_public.py + generate.py  → UC volume landing/
          ▼
LAKEFLOW SDP (serverless, SQL)        bronze_* (Auto Loader, + _source_file, _ingested_at)
          ▼                           silver_* (typed, trimmed, deduped, conformed) + silver_prices_quarantine
          ▼                           recon_market_data (manifest vs landed/loaded/quarantined)
          ▼                           gold_universe_monthly, gold_index_constituents,
          ▼                           gold_reconstitution_history, gold_etf_exposure
UNITY CATALOG  entitlements table → row filter / column masks on gold + prediction tables; tags; lineage
          ▼
ML  src/ai/train.py: features from gold_universe_monthly → MLflow → UC model ndx.recon_classifier
          ▼          score → gold_recon_predictions (p_add, p_remove, drivers)
GENAI src/ai/briefs.sql: ai_query on preset scenarios → gold_scenario_briefs; evaluate.py → ai_eval_results
          ▼
LAKEBASE  src/serve/sync_lakebase.py upserts security_watch (machine cols) from gold + predictions;
          app-owned: scenarios, scenario_rules, approvals, audit_log
          ▼
GENIE     space over gold_universe_monthly, gold_index_constituents, gold_reconstitution_history,
          gold_recon_predictions, gold_etf_exposure (governed tables only)
          ▼
APP       Streamlit (user token): Overview · Scenario Lab · Compare & Approve · Ask Genie
```

## 2. Stages

| Stage | Does for the Head of Methodology | Reads → writes | Features | Verified by / evidence |
|---|---|---|---|---|
| Lakeflow | Trusted, reconciled inputs instead of copied spreadsheets | landing/ → bronze → silver → gold | SDP, Auto Loader, expectations, quarantine, MVs | row counts, quarantine, recon status → `01_pipeline_run.md`, `02_data_quality.md` |
| Unity Catalog | MNPI locked to the index team; lineage to weights | gold, predictions | row filters, column masks, tags, comments, grants, lineage | per-persona queries + SP test → `06_governance.md` |
| ML | Early warning of likely adds/removes | gold_universe_monthly → gold_recon_predictions | MLflow 3, UC model registry, batch scoring | held-out metrics vs baseline → `05_ai_evaluation.md` |
| GenAI | Impact summary + ETF-issuer notice in seconds | preset scenarios → gold_scenario_briefs | ai_query, structured output, mlflow.genai.evaluate | verbatim outputs + judge scores → `04_ai_output.md`, `05_ai_evaluation.md` |
| Lakebase | Saved scenarios, approvals, audit trail | gold + predictions → security_watch; app → scenarios/approvals/audit_log | autoscaling Postgres, OAuth DB credentials | edit-survives-refresh, history → `07_lakebase.md` |
| Genie | Plain-English answers without SQL | 5 gold tables | Genie space, instructions, benchmarks | expected vs Genie → `08_genie.md` |
| App | One place to run, compare, approve | SQL warehouse + Lakebase + Genie | Databricks Apps, OBO user token | route checks, persona diff → `10_app.md` |

## 3. Tables (grain)

**Bronze** (raw as landed + `_source_file`, `_ingested_at`): `bronze_security_master` (symbol-directory row), `bronze_sec_companies` (ticker–CIK–SIC row), `bronze_sec_facts` (CIK × fact × period), `bronze_daily_prices` (file row), `bronze_price_manifest` (file), `bronze_index_history` (symbol × event), `bronze_etf_aum` (product × month).

**Silver:** `silver_securities` (one per ticker: type, sector, eligibility inputs), `silver_shares` (CIK × as-of date, point-in-time), `silver_prices` (ticker × trade date, deduped), `silver_prices_quarantine` (rejected row + reason), `silver_index_events` (ticker × reconstitution × add/remove/stay), `silver_etf_aum` (product × month). Plus `recon_market_data` (one per daily file: RECONCILED/BREAK).

**Gold (5):** `gold_universe_monthly` (ticker × month-end: mcap, rank, ADV, sector, eligible, in_index); `gold_index_constituents` (current baseline: ticker, weight, capped weight); `gold_reconstitution_history` (reconstitution × ticker: action, turnover contribution); `gold_etf_exposure` (month: AUM tracking the index); `gold_recon_predictions` (ticker × as-of: p_add, p_remove, top drivers, model version).

## 4. Bundle layout

`databricks.yml` variables: `catalog`, `schema`, `warehouse_id`, `llm_endpoint` (Claude), `judge_endpoint` (GPT), `lakebase_project`. Target `dev` on profile `fe-bar-2026`.
`resources/`: `pipeline.yml` (one SDP), `job.yml` (orchestration), `setup_job.yml` (land + generate data), `app.yml` (Streamlit app + warehouse, Genie, Lakebase resources).

## 5. Orchestration (one Lakeflow Job, `nextdaq_rebalance_cycle`)

`refresh_pipeline` → `train_and_score` + `ai_briefs` → `evaluate_ai` → `governance` (SQL task, re-applies policies to the tables the AI tasks rewrote) → `sync_lakebase`. Trigger: file arrival on `landing/price_manifests/`. `max_concurrent_runs: 1`, queueing on.

## 6. Time plan (~8 h)

| Stage | Time |
|---|---|
| P03 data generator + public landing | 45 min |
| P04 Lakeflow pipeline | 60 min |
| P05 Unity Catalog | 30 min |
| P06 ML + GenAI + evaluation | 75 min |
| P07 Lakebase | 45 min |
| P08 Genie | 45 min |
| P09 App | 90 min |
| P10 orchestration | 30 min |
| P11–P13 evidence, README, scrub | 60 min |
