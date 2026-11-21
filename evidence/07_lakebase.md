# 07 — Lakebase operational serving

Generated 2026-11-21 19:02 UTC by tools/generate_evidence.py from the live workspace.

Proves the forecast watchlist is served from Lakebase (autoscaling Postgres, project nextdaq-ops, database nextdaq, schema ops): machine-owned columns are refreshed from gold every cycle while human-owned columns survive, every change has a history row, and the app's scenario / approval / audit tables are live. Values come from the sync task's own output (it connects with a short-lived OAuth database credential).

## Latest sync (job run 645495415992934)

| measure | value |
|---|---|
| sync | `{"upserted": 150, "created": 0, "model_changes": 0}` |
| counts | `{"HOLD": 142, "ADD": 4, "REMOVE": 5}` |
| review_status | `{"NEW": 150, "CONFIRMED": 1}` |
| history | `{"MODEL_CHANGE": 4, "HUMAN_EDIT": 1, "CREATED": 151}` |
| scenarios_by_status | `{"APPROVED": 1}` |
| approvals | `{"APPROVED": 1}` |
| audit_actions | `{"SUBMITTED": 1, "APPROVED": 1}` |

## Edit survives refresh (job run 948168268290092)

A person set one record to CONFIRMED with a note, then the refresh ran again.

| check | result |
|---|---|
| record | CHTR |
| review_status after refresh | CONFIRMED |
| analyst note kept | True |
| machine columns refreshed | True |
| refresh after edit | `{"upserted": 150, "created": 0, "model_changes": 0}` |

## History sample (non-creation changes)

| ticker | change | field | old | new | at |
|---|---|---|---|---|---|
| MDB | MODEL_CHANGE | predicted_action | HOLD | ADD | 2026-11-21 18:55:32 |
| TEAM | MODEL_CHANGE | predicted_action | REMOVE | HOLD | 2026-11-21 18:55:32 |
| CPRT | MODEL_CHANGE | predicted_action | REMOVE | HOLD | 2026-11-21 18:55:32 |
| INSM | MODEL_CHANGE | predicted_action | ADD | HOLD | 2026-11-21 18:55:32 |
| CHTR | HUMAN_EDIT | review_status | NEW | CONFIRMED | 2026-11-21 17:54:36 |

## Audit log sample (app actions)

| at | entity | id | action |
|---|---|---|---|
| 2026-11-21 18:25:16 | scenario | SCN-20261121-fc3713 | APPROVED |
| 2026-11-21 18:25:00 | scenario | SCN-20261121-fc3713 | SUBMITTED |

## Who enforces what

| control | enforced by |
|---|---|
| Sector row filter, MNPI masks, MNPI row gate on Delta | Platform (Unity Catalog), per signed-in user via the app's user token |
| Who may approve a scenario (entitlements.can_approve) | App, reading the entitlements table as the signed-in user |
| Who sees Lakebase scenario rows and watchlist probabilities | App (the app connects to Postgres as its service principal) |
| App role may not delete history or audit rows | Platform (Postgres grants: SELECT, INSERT, UPDATE only) |
