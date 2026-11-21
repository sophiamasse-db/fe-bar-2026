# NextDAQ-100 Rebalance Simulator

**NextDAQ's methodology team will use this app to cut the time to run one rebalance scenario from days to minutes, evaluate more scenarios per rebalance cycle, shorten the time from methodology proposal to approval, and reduce errors and restatements in rebalance calculations.**

## Who it is for

This app is for the methodology team. Each December, the NextDAQ-100 is reconstituted, and quarterly or special rebalances happen when concentration caps are breached. Every rule change or rebalance moves billions of dollars in trading, so methodology teams need to understand the impact before announcing it.

NextDAQ and the NextDAQ-100 are fictional. All data is **public** (exchange symbol directory, SEC EDGAR) or **synthetic** (prices, index history, ETF assets). No customer data.

## The problem and why now

Today's pain points: scenario analysis runs in spreadsheets, takes days to iterate on, lacks a robust audit trail, and puts sensitive pre-announcement data at risk.

**Why now:** concentration is the big one. A handful of megacaps now carry so much of the index that cap breaches and special rebalances are happening more often, and each one is a client-trust moment with ETF issuers. At the same time, competitors are launching custom and thematic indexes in weeks, and regulators expect benchmark administrators to show a controlled, documented methodology process. Spreadsheets can't keep up with any of those three.

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

One connected flow: raw files -> Lakeflow -> Unity Catalog -> ML + GenAI -> Lakebase -> Genie -> app.

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

The full list, with the alternatives I rejected, is in [DECISIONS.md](DECISIONS.md). The ones that matter most:

1. **The ETF-issuer notice is a template.** It goes to clients and moves money, so it has to be exactly right every time. It's built straight from the scenario facts; the AI only writes the internal impact summary, which a person reviews before anything is decided.
2. **The forecast is a watchlist, not a verdict.** On a reconstitution it had never seen, it didn't beat a simple "rank inside the top 100" rule, so I don't claim it's more accurate. What it adds is an early, explained list of names drifting toward the cutoff. The methodology rule still makes the call.
3. **Entitlements live in a table.** Access changes all the time; as rows, each change is one visible, auditable update instead of a code change. Unity Catalog policies read that table, so the app, Genie and SQL enforce the same rules.
4. **Bad data is quarantined, not fatal.** Rows that fail a check go to a quarantine table with a reason, and a broken vendor file shows up as a reconciliation break. One bad price shouldn't stop a daily process, but nothing disappears silently.
5. **Raw files land in a volume; Auto Loader reads them,** so loads replay safely.
6. **Synthetic prices are anchored to real SEC public float.** Rankings look like the real market, which a technical stakeholder will check. Real SEC data was messy too (11 filers report float ~1000x too large); fixed openly.
7. **Lakebase never overwrites what people own.** The refresh updates the model's columns; review status and analyst notes always survive, and every change is in the history.
8. **A different model family grades the AI.** Claude writes the summaries and GPT judges them, against a protocol I committed before seeing any result.
9. **I tested access as a separate, non-admin identity,** not just as myself, because my own account can pass while access leaks through a group.
10. **Methodology bands of 90 / 110.** With wider bands the index barely changed in four years; 90 / 110 gives a realistic five or six changes a year, and both are sliders in the app.

## How AI was used

I built this with Claude Code as a pair engineer, step by step through the FE Bar prompt pack. Claude drafted the code, SQL and documents; I made the calls at every stop: the use case and personas, the architecture, which data issues to plant, the quality rules, who can see what, the AI approach, and which numbers to stand behind.

What kept it honest:
- **One rulebook for every session** ([FEBAR_CONTEXT.md](FEBAR_CONTEXT.md)) and a running [BUILD_LOG.md](BUILD_LOG.md) of what failed and what we changed.
- **The evaluation protocol was committed before any result.** Every change to it is a dated amendment written before the rerun, and every version's result is kept.
- **Evidence is generated from the live workspace by scripts,** never typed by hand.
- **Realism checks before trusting output.** That caught mid-caps ranked as megacaps (bad SEC float data), a reverse split inflating a company's size, a capping edge case, and an app cache that could have shown data loaded under someone's old access.

**One iteration story.** The first AI summaries passed 0 of 8 judge checks. The judges' reasons showed two causes: one judge contradicted my own prompt, and the model added documents that weren't in the facts. I didn't loosen the judges. I made the client notice a template and gave the model the context it was missing. That took it from 0/8 to 1/8 to 6/8, and 5/8 in the final run. That's still below my 90% bar, which is exactly why every draft goes through human approval.

## Repository and how to run it

```
./tools/deploy.sh                                             # bundle deploy + sync job code to the UC volume
databricks bundle run nextdaq_setup_data -p fe-bar-2026       # land public data, generate synthetic data
databricks bundle run nextdaq_rebalance_cycle -p fe-bar-2026  # pipeline -> AI -> governance -> Lakebase
python3 tools/genie.py; ./tools/access_test.sh                # Genie space + benchmarks; non-admin access test
databricks bundle run nextdaq_app -p fe-bar-2026              # start the app
python3 tools/generate_evidence.py                            # regenerate evidence/ from the live workspace
```

Planning: [USE_CASE.md](USE_CASE.md), [BUILD_PLAN.md](BUILD_PLAN.md).
