# 09 — Orchestrated cycle

Generated 2026-11-21 19:02 UTC by tools/generate_evidence.py from the live workspace.

Proves one Lakeflow Job runs the whole journey in order (pipeline, then forecast and briefs, evaluation, governance, Lakebase sync) after new vendor files land, and that a rerun with no new data is safe. Each task's exit summary is its own printed JSON.

Job `nextdaq_rebalance_cycle`: trigger = file arrival on `fe_bar_2026_kelemen_catalog/nextdaq_index/landing/price_manifests/`, max_concurrent_runs = 1, queueing = True.

## Run 462631556123907: final run after the 2 held-back days landed (started manually: the file-arrival trigger is configured but did not fire in this workspace during testing)

trigger = ONE_TIME, result = SUCCESS, started 2026-11-21 18:50 UTC

| task | state | seconds | exit summary |
|---|---|---|---|
| refresh_pipeline | SUCCESS | 103 |  |
| train_and_score | SUCCESS | 70 | {"mlflow_run_id": "51d7c9d2280b4e499ae1a332ff31de1e", "model": "fe_bar_2026_kelemen_catalog.nextdaq_index.recon_classifier", "version": 4, "as_of": "2026-11-20", "scored_rows": 1015, "predicted_adds": 3, "predicted_removes": 5, "protocol_version": "v2", "threshold_add": 0.65, "threshold_remove": 0.1 |
| ai_briefs | SUCCESS | 74 | {"scenarios": 8, "briefs_ok": 8, "errors": 0, "model": "databricks-claude-sonnet-4-6", "prompt_version": "v3.1", "as_of": "2026-11-20", "baseline_adds": 5, "baseline_removes": 5} |
| evaluate_ai | SUCCESS | 54 | {"prompt_version": "v3.1", "rows": 8, "judges": ["grounded", "no_invention", "compliant_tone", "actionable_notice"], "pass_rate_by_judge": {"actionable_notice": 1.0, "compliant_tone": 0.875, "grounded": 1.0, "no_invention": 0.625}, "rows_passing_all_judges": 4, "share_passing_all": 0.5, "mlflow_run_ |
| governance | SUCCESS | 41 |  |
| sync_lakebase | SUCCESS | 26 | {"database": "nextdaq", "schema": "ops", "sync": {"upserted": 150, "created": 1, "model_changes": 4}, "counts": {"HOLD": 142, "ADD": 4, "REMOVE": 5}, "review_status": {"NEW": 150, "CONFIRMED": 1}, "history": {"MODEL_CHANGE": 4, "HUMAN_EDIT": 1, "CREATED": 151}, "scenarios_by_status": {"APPROVED": 1} |

## Run 645495415992934: rerun immediately after, no new data

trigger = ONE_TIME, result = SUCCESS, started 2026-11-21 18:55 UTC

| task | state | seconds | exit summary |
|---|---|---|---|
| refresh_pipeline | SUCCESS | 72 |  |
| train_and_score | SUCCESS | 56 | {"mlflow_run_id": "b21703a5d7704ccdb5d4eec764070ebd", "model": "fe_bar_2026_kelemen_catalog.nextdaq_index.recon_classifier", "version": 5, "as_of": "2026-11-20", "scored_rows": 1015, "predicted_adds": 3, "predicted_removes": 5, "protocol_version": "v2", "threshold_add": 0.65, "threshold_remove": 0.1 |
| ai_briefs | SUCCESS | 57 | {"scenarios": 8, "briefs_ok": 8, "errors": 0, "model": "databricks-claude-sonnet-4-6", "prompt_version": "v3.1", "as_of": "2026-11-20", "baseline_adds": 5, "baseline_removes": 5} |
| evaluate_ai | SUCCESS | 55 | {"prompt_version": "v3.1", "rows": 8, "judges": ["grounded", "no_invention", "compliant_tone", "actionable_notice"], "pass_rate_by_judge": {"actionable_notice": 1.0, "compliant_tone": 1.0, "grounded": 0.875, "no_invention": 0.75}, "rows_passing_all_judges": 5, "share_passing_all": 0.625, "mlflow_run |
| governance | SUCCESS | 24 |  |
| sync_lakebase | SUCCESS | 25 | {"database": "nextdaq", "schema": "ops", "sync": {"upserted": 150, "created": 0, "model_changes": 0}, "counts": {"HOLD": 142, "ADD": 4, "REMOVE": 5}, "review_status": {"NEW": 150, "CONFIRMED": 1}, "history": {"MODEL_CHANGE": 4, "HUMAN_EDIT": 1, "CREATED": 151}, "scenarios_by_status": {"APPROVED": 1} |

## Cross-check after the final run

Gold (SQL):

| latest_price_day | latest_snapshot | forecast_adds_gold | forecast_removes_gold | manifests | reconciled |
|---|---|---|---|---|---|
| 2026-11-20 | 2026-11-20 | 3 | 5 | 77 | 76 |

Lakebase security_watch (sync output): ADD = 4, REMOVE = 5, HOLD = 142.
