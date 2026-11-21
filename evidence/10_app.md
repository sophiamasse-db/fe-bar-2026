# 10 — Databricks App

Generated 2026-11-21 19:03 UTC by tools/generate_evidence.py from the live workspace.

Proves the app is deployed and used end to end: every screen render and action writes a structured line to the app log (no emails or tokens). It shows the persona the platform resolved, how many forecast rows were visible and unmasked, scenario runs, AI drafts, Lakebase submissions/approvals and Genie answers.

App `nextdaq-rebalance-simulator`: compute ACTIVE, active deployment SUCCEEDED, user API scopes sql, dashboards.genie; resources: sql-warehouse, genie-space, llm-endpoint, lakebase.

## Page views by persona (what the platform let each persona see)

| page | persona | forecast rows | unmasked | MNPI cleared | can approve |
|---|---|---|---|---|---|
| Overview | HEAD_OF_METHODOLOGY | 1015 | 1015 | True | True |
| Scenario Lab | HEAD_OF_METHODOLOGY | 1015 | 1015 | True | True |
| Compare & Approve | HEAD_OF_METHODOLOGY | 1015 | 1015 | True | True |
| Ask Genie | HEAD_OF_METHODOLOGY | 1015 | 1015 | True | True |

## Events in the log

| event | count |
|---|---|
| ai_summary | 2 |
| genie_answer | 2 |
| page_view | 37 |
| scenario_decision | 1 |
| scenario_run | 17 |
| scenario_submitted | 1 |

## Workflow actions (every one)

| at | event | persona | detail |
|---|---|---|---|
| 2026-11-21T18:18:01+00:00 | ai_summary | HEAD_OF_METHODOLOGY | {"scenario": "My scenario", "prompt_version": "v3.1", "words": 96} |
| 2026-11-21T18:18:55+00:00 | genie_answer | HEAD_OF_METHODOLOGY | {"question": "Which predicted removals have the highest ETF trading impact?", "rows": 7, "sql_returned": true} |
| 2026-11-21T18:24:56+00:00 | ai_summary | HEAD_OF_METHODOLOGY | {"scenario": "My scenario", "prompt_version": "v3.1", "words": 102} |
| 2026-11-21T18:25:00+00:00 | scenario_submitted | HEAD_OF_METHODOLOGY | {"scenario_id": "SCN-20261121-fc3713"} |
| 2026-11-21T18:25:16+00:00 | scenario_decision | HEAD_OF_METHODOLOGY | {"scenario_id": "SCN-20261121-fc3713", "decision": "APPROVED"} |
| 2026-11-21T18:25:42+00:00 | genie_answer | HEAD_OF_METHODOLOGY | {"question": "How many additions and removals were there in each of the last 3 annual reconstitutions?", "rows": 3, "sql_returned": true} |

## Scenario runs (last 6)

| at | name | shock | additions | removals | turnover % | max weight % | max days to trade |
|---|---|---|---|---|---|---|---|
| 2026-11-21T18:24:04+00:00 | My scenario | TXN 30 | 5 | 5 | 1.53 | 11.37 | 763.32 |
| 2026-11-21T18:24:29+00:00 | My scenario | -  | 5 | 5 | 1.22 | 11.37 | 769.03 |
| 2026-11-21T18:24:33+00:00 | My scenario | -  | 5 | 5 | 9.26 | 7.23 | 858.76 |
| 2026-11-21T18:24:35+00:00 | My scenario | -  | 4 | 4 | 9.15 | 7.23 | 859.81 |
| 2026-11-21T18:24:38+00:00 | My scenario | -  | 3 | 3 | 9.04 | 7.22 | 861.13 |
| 2026-11-21T18:24:40+00:00 | My scenario | -  | 3 | 3 | 9.04 | 7.22 | 861.13 |
