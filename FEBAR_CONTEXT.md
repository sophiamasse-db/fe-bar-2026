# FEBAR_CONTEXT.md — rules for every session on this repo

Read this file before every task and follow it.

## 1. Purpose

I am building my own FE Bar submission: a working prototype that solves **slow, spreadsheet-based, poorly audited index rebalance and reconstitution scenario analysis** for an **index provider (NextDAQ, publisher of the fictional NextDAQ-100)** in **Capital Markets / Financial Services**.

- **Executive sponsor:** Head of the Index Business (owns licensing revenue and client trust in the index brand).
- **Domain owner:** Head of Index Methodology & Operations (owns rebalance calculations, rule changes and announcements).
- **Buyer KPIs:** time to run one rebalance scenario (days → minutes); scenarios evaluated per cycle; proposal-to-approval time; rebalance calculation errors and restatements; index quality per scenario (turnover %, top-10 weight, max single weight, HHI, adds/removes, days to trade vs ADV, estimated ETF trading impact = AUM × Δweight); time to launch a custom index; add/remove prediction precision and recall.

## 2. Non-negotiable FE Bar rules

- One connected journey starting from RAW synthetic or public data: Lakeflow ingest → Unity Catalog governance → Lakebase operational serving → ML or GenAI → Genie agent → Databricks App. Each stage consumes the output of the previous one. No disconnected demos.
- The evaluator reads TEXT only. Every stage needs committed text evidence that it ran (notebook outputs, run logs, query results, model output). Screenshots and recordings do not count. Source code alone fails the Build domain.
- Evaluator limits: **at most 30 files, 9,000 characters per file, 90,000 characters total.** Keep evidence files short and put the most important files first; split or trim anything longer than 9,000 characters.
- The GitHub repo must be readable by the evaluator (it is public).
- Synthetic or public data only. Never real customer data, customer names, people's names, internal system names or logos in code, data, docs, commit messages or the deck. The company and index are the fictional **NextDAQ** / **NextDAQ-100**. Public sources (the exchange symbol directory, SEC EDGAR company facts) may be named as data sources.
- This is my own work. Never use or imitate Solution Builder output and never copy another person's build.
- A business deck (PDF, .txt or .md) and an AI role-play are also required; we prepare those at the end.

## 3. How you work with me

- Work in small, verifiable steps. After each step: what you changed, how you verified it, what is next.
- STOP AND ASK before any decision about: the use case and story, personas, architecture and trade-offs, which data issues to plant, quality rules, access rules, AI approach, numbers in the value case, slide content and the narrative. Give two or three options with pros and cons and a recommendation; I decide.
- Keep BUILD_LOG.md: date, what you tried, what failed, what you changed and why.
- Record every decision I make in DECISIONS.md (decision, options considered, why). I will rewrite it in my own words.
- Mark every narrative, opinion and decision section you draft (README, DECISIONS.md, deck notes) with [YOUR WORDS] so I rewrite it myself.
- Never print, log or commit tokens, passwords or connection strings. Never guess a Databricks CLI profile; use the one below.
- Commits are authored by me, under my own git identity.

## 4. Engineering conventions

- Workspace: `https://fevm-fe-bar-2026-kelemen.cloud.databricks.com` — CLI profile **`fe-bar-2026`**. Use `--profile fe-bar-2026` (or `-p fe-bar-2026`) on every CLI command.
- Everything lives in Unity Catalog under **`fe_bar_2026_kelemen_catalog.nextdaq_index`**. Raw files go in the UC volume `fe_bar_2026_kelemen_catalog.nextdaq_index.landing`.
- Deploy everything with a Declarative Automation Bundle: `databricks.yml` with variables (catalog, schema, warehouse_id, model endpoints) and one target; `resources/*.yml` for pipelines, jobs and apps. Commands: `databricks bundle validate`, `databricks bundle deploy`, `databricks bundle run <resource>`.
- Prefer serverless compute: serverless Lakeflow pipelines, serverless jobs, the serverless SQL warehouse.
- Pipelines in SQL (Lakeflow Spark Declarative Pipelines) unless Python is clearly better.
- Reruns must be safe (idempotent): no duplicate rows when a step runs twice.
- Every notebook task ends with `dbutils.notebook.exit(json.dumps(summary))`, a short JSON of what it did (rows, IDs, pass counts). Python file tasks print the same summary. The evidence step reads these back.
- If Databricks agent skills are installed, load the matching skill before each product (pipelines, Unity Catalog, Lakebase, apps, Genie, MLflow, jobs, bundles) and follow it.

## 5. Repository layout

README.md, FEBAR_CONTEXT.md, USE_CASE.md, BUILD_PLAN.md, EVAL_PROTOCOL.md, DECISIONS.md, BUILD_LOG.md, databricks.yml, resources/, src/data/, src/pipeline/, src/governance/, src/ai/, src/serve/, src/genie/, src/app/, tools/, evidence/, deck/. `.gitignore` covers .databricks/, .env, *.pem, local notes and any credentials.

## 6. Definition of done for every task

Code committed, deployed, run successfully in the workspace, verified with a query or API call whose output is shown to me, and a line added to BUILD_LOG.md.
