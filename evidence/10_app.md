# 10 — Databricks App

Generated 2026-11-21 19:23 UTC by tools/generate_evidence.py from the live workspace.

Proves the app is deployed and used end to end: every screen render and action writes a structured line to the app log (no emails or tokens). It shows the persona the platform resolved, how many forecast rows were visible and unmasked, scenario runs, AI drafts, Lakebase submissions/approvals and Genie answers.

App `nextdaq-rebalance-simulator`: compute ACTIVE, active deployment SUCCEEDED, user API scopes sql, dashboards.genie; resources: sql-warehouse, genie-space, llm-endpoint, lakebase.

## Page views by persona (what the platform let each persona see)

| page | persona | forecast rows | unmasked | MNPI cleared | can approve |
|---|---|---|---|---|---|
| Overview | HEAD_OF_METHODOLOGY | 1015 | 1015 | True | True |
| Scenario Lab | HEAD_OF_METHODOLOGY | 1015 | 1015 | True | True |
| Compare & Approve | HEAD_OF_METHODOLOGY | 1015 | 1015 | True | True |
| Ask Genie | HEAD_OF_METHODOLOGY | 1015 | 1015 | True | True |
| Scenario Lab | CLIENT_SERVICES | 1015 | 0 | False | False |
| Ask Genie | CLIENT_SERVICES | 1015 | 0 | False | False |

## Events in the log

| event | count |
|---|---|
| ai_summary | 2 |
| genie_answer | 3 |
| page_view | 45 |
| scenario_decision | 1 |
| scenario_run | 21 |
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
| 2026-11-21T19:21:01+00:00 | genie_answer | CLIENT_SERVICES | {"question": "Which names does the forecast predict will be added or removed at the next reconstitution?", "rows": 1, "sql_returned": true} |

## Scenario compute time

4 timed scenario runs over 1015 securities: min 23 ms, max 29 ms (engine only, after the governed data is loaded).

## Scenario runs (last 6)

| at | persona | shock | additions | removals | turnover % | max weight % | max days to trade | compute ms |
|---|---|---|---|---|---|---|---|---|
| 2026-11-21T18:24:38+00:00 | HEAD_OF_METHODOLOGY | -  | 3 | 3 | 9.04 | 7.22 | 861.13 | - |
| 2026-11-21T18:24:40+00:00 | HEAD_OF_METHODOLOGY | -  | 3 | 3 | 9.04 | 7.22 | 861.13 | - |
| 2026-11-21T19:20:11+00:00 | CLIENT_SERVICES | -  | 5 | 5 | 1.12 | 11.43 | 30.88 | 26 |
| 2026-11-21T19:20:15+00:00 | CLIENT_SERVICES | -  | 5 | 5 | 8.85 | 9.14 | 36.41 | 23 |
| 2026-11-21T19:20:19+00:00 | CLIENT_SERVICES | -  | 5 | 5 | 15.88 | 5.78 | 41.41 | 29 |
| 2026-11-21T19:20:21+00:00 | CLIENT_SERVICES | -  | 5 | 5 | 8.85 | 9.14 | 36.41 | 25 |
