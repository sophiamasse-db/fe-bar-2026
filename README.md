# NextDAQ-100 Rebalance Simulator

**[YOUR WORDS] Index methodology teams can test a rebalance rule change in under 30 milliseconds instead of 2-3 analyst-days, with every scenario governed, approved and auditable.**

## Who it is for

[YOUR WORDS] **NextDAQ** (fictional), an index provider in Capital Markets that licenses the NextDAQ-100 to ETF issuers and derivatives markets. Built for the **Head of the Index Business** (licensing revenue, client trust) and the **Head of Index Methodology & Operations** (on-time, error-free rebalances). All data is **public** (exchange symbol directory, SEC EDGAR) or **synthetic** (prices, index history, ETF assets). No customer data.

## The problem and why now

- [YOUR WORDS] Each December reconstitution, and every concentration-cap breach, is rebuilt in spreadsheets: 2-3 analyst-days per scenario, so only 3-4 options reach the committee [ASSUMPTION from discovery].
- There is no record of who changed which rule; pre-announcement numbers (material non-public information) sit in shared files.
- **Why now:** a handful of megacaps now drive index weight, so special rebalances are more frequent; competitors launch custom indexes in weeks; benchmark regulation expects a controlled, documented methodology process.

## What it delivers

| Outcome for NextDAQ | How it shows up | Evidence |
|---|---|---|
| Scenarios in milliseconds, not days | Scenario Lab: sliders for caps, liquidity floor, add/keep bands, sector exclusions, stress test; computed in 23-29 ms | [10_app](evidence/10_app.md) |
| Trusted inputs | 54 bad rows quarantined with a reason out of 1,333,026; 1 of 77 vendor files flagged as a break | [01](evidence/01_pipeline_run.md), [02](evidence/02_data_quality.md) |
| MNPI locked down by the platform | Client Services sees 0 of 1,015 forecast probabilities, as a switched user and as a non-admin service principal | [06](evidence/06_governance.md) |
| Decisions recorded | Analyst submits, head of methodology approves; scenarios, approvals and audit trail in Lakebase | [07](evidence/07_lakebase.md) |
| Answers without SQL | Genie: 14 of 14 benchmark questions match ground truth | [08](evidence/08_genie.md) |
| Early warning, explained | Add/remove watchlist with probabilities and plain-language reasons; AI-drafted impact summary | [04](evidence/04_ai_output.md), [05](evidence/05_ai_evaluation.md) |

## Value

| Value driver | From the data | Illustrative value / year |
|---|---|---|
| Analyst time | scenario compute 23-29 ms (measured) vs 2-3 days [ASSUMPTION] | ~$190-240k (4 analysts x 30% x $200k loaded) |
| Fewer corrections | quarantine + reconciliation catch bad inputs before they reach weights | ~$250-500k (2 -> <=1 corrections x ~$250k) |
| Faster custom indexes | same engine, new rules | ~$300k pulled forward (3 launches x 2 months x $50k) |
| **Total** | | **~$0.75-1.0M, illustrative; not verified** |

What it does **not** claim: the add/remove forecast did not beat a simple rank rule on the held-out reconstitution, and 5 of 8 AI summaries passed all judges in the final run (below the 90% bar). Both are used as decision support with a person in the loop. Headline numbers: [evidence/HEADLINES.md](evidence/HEADLINES.md).

## How it works

Raw files land in a Unity Catalog volume; a Lakeflow pipeline builds bronze, silver (with quarantine and reconciliation) and gold; Unity Catalog governs it; an MLflow model forecasts adds and removes and `ai_query` drafts summaries; a job upserts the watchlist into Lakebase, where the app also keeps scenarios and approvals; Genie answers questions on the same gold tables; the app brings it together, querying as the signed-in user.

| Stage | What it does | Files |
|---|---|---|
| Lakeflow | Auto Loader bronze, typed/deduped silver, expectations + quarantine, reconciliation vs control totals, gold | [src/pipeline/](src/pipeline), [src/data/](src/data) |
| Unity Catalog | Entitlements table, sector row filter, MNPI masks and row gate, governed tags, lineage | [src/governance/](src/governance) |
| ML + GenAI | Gradient-boosted forecast in UC; scenario briefs with ai_query; MLflow judges | [src/ai/](src/ai), [EVAL_PROTOCOL.md](EVAL_PROTOCOL.md) |
| Lakebase | security_watch (machine vs human columns), history, scenarios, approvals, audit_log | [src/serve/](src/serve) |
| Genie | 5 governed gold tables, definitions, benchmarks | [src/genie/](src/genie), [tools/genie.py](tools/genie.py) |
| App | Streamlit with the user's token; shared rebalance engine | [src/app/](src/app) |
| Orchestration | One job: pipeline -> forecast + briefs -> evaluate -> governance -> Lakebase | [resources/job.yml](resources/job.yml) |

## Decisions and trade-offs

[YOUR WORDS] Full list with alternatives: [DECISIONS.md](DECISIONS.md).

1. Files in a UC volume with Auto Loader over API calls in the pipeline, so loads replay safely.
2. Synthetic prices anchored to real SEC public float over random prices, so rankings are believable.
3. Bad rows dropped to quarantine with a reason over failing the update; breaks are visible, not fatal.
4. Entitlements as data (a table) over hard-coded users, so access changes are row changes.
5. A dedicated non-admin service principal for the access test over testing only as myself.
6. Lakebase upsert that never touches human-owned columns over a read-only synced table.
7. A trained forecast plus AI summaries over a heuristic score; the AI explains, it never ranks.
8. The client notice is a template; only the internal summary is AI-written.
9. A different model family judges the generator; every protocol change dated before the rerun.
10. Methodology bands 90/110 over 75/125, so the index changes at a realistic rate.

## How AI was used

[YOUR WORDS] I built this with Claude Code as a pair engineer, following the FE Bar prompt pack: it drafted code and documents; I made every decision at each stop (use case, architecture, quality rules, personas, AI approach, headlines). Practices that kept it honest:
- A context file every session follows ([FEBAR_CONTEXT.md](FEBAR_CONTEXT.md)); a build log of what failed and what changed ([BUILD_LOG.md](BUILD_LOG.md)).
- An evaluation protocol committed before any result, with dated amendments and every version's result kept.
- Evidence generated from the live workspace by scripts, never typed by hand.
- **One iteration story:** v1 AI briefs passed 0 of 8 judge checks. The judges showed two causes: a judge that contradicted the prompt, and the model adding documents that were not in the facts. Instead of loosening judges, I made the client notice a template and added the missing context to the facts: 0/8 -> 1/8 -> 6/8 and 5/8 in the final run.
- Realism checks caught real bugs: mid-caps ranked as megacaps (SEC public float tagged ~1000x too large for 11 filers), a reverse split inflating market cap, and a capping edge case.

## Repository and how to run it

```
databricks auth login --host <workspace> --profile fe-bar-2026
./tools/deploy.sh                                   # bundle deploy + sync job code to the UC volume
databricks bundle run nextdaq_setup_data -p fe-bar-2026      # land public data, generate synthetic data
databricks bundle run nextdaq_rebalance_cycle -p fe-bar-2026 # pipeline -> AI -> governance -> Lakebase
python3 tools/genie.py                              # create/update the Genie space and run benchmarks
databricks bundle run nextdaq_app -p fe-bar-2026    # start the app
./tools/access_test.sh                              # non-admin access test (grant, run as SP, revoke)
python3 tools/generate_evidence.py && python3 tools/evidence_00_answer_key.py
./tools/land_holdback.sh                            # demo: land the held-back trading days
```

Layout: `src/` (data, pipeline, governance, ai, serve, genie, app), `resources/` (bundle), `tools/`, `evidence/`, `deck/`. Planning: [USE_CASE.md](USE_CASE.md), [BUILD_PLAN.md](BUILD_PLAN.md).
