# 01 — Lakeflow pipeline run

Generated 2026-11-21 19:01 UTC by tools/generate_evidence.py from the live workspace.

Proves the serverless Lakeflow Spark Declarative Pipeline `nextdaq_pipeline` (src/pipeline/*.sql) ran to COMPLETED, shows rows per table across bronze/silver/gold, the expectation pass/fail counts read from the pipeline event log, and that a rerun does not duplicate rows.

Pipeline id: `ecd0a7d6-364e-4bf1-98d1-1b2688c1d3a8` (serverless, catalog `fe_bar_2026_kelemen_catalog`, schema `nextdaq_index`).

## Recent updates

| update | state | full refresh | created (UTC) | cause |
|---|---|---|---|---|
| 583e2ac3 | COMPLETED | False | 2026-11-21 18:55 | JOB_TASK |
| 0da7ddba | COMPLETED | False | 2026-11-21 18:50 | JOB_TASK |
| 1982a923 | COMPLETED | False | 2026-11-21 17:30 | JOB_TASK |
| 394d4868 | COMPLETED | False | 2026-11-21 16:18 | JOB_TASK |
| edc17c16 | COMPLETED | False | 2026-11-21 16:00 | JOB_TASK |

Durations from the event log:

| update_id | started | ended | seconds |
|---|---|---|---|
| 583e2ac3-e69a-429f-85aa-773f24ae3616 | 2026-11-21T18:55:50.465Z | 2026-11-21T18:56:49.005Z | 59.0 |
| 0da7ddba-101d-4401-9fa2-82fd3426cad6 | 2026-11-21T18:50:31.882Z | 2026-11-21T18:52:03.915Z | 92.0 |
| 1982a923-b632-4c37-8e9e-56ae130ecdef | 2026-11-21T17:30:11.493Z | 2026-11-21T17:31:09.530Z | 58.0 |

## Expectations (latest completed update)

| dataset | expectation | passed | failed |
|---|---|---|---|
| recon_market_data | reconciled | 76 | 1 |
| silver_index_events | clean_ticker | 181 | 0 |
| silver_prices | unique_ticker_day | 1332989 | 37 |
| silver_prices | valid_close | 1333014 | 12 |
| silver_prices | valid_volume | 1333021 | 5 |
| silver_securities | has_sector | 1020 | 13 |
| silver_securities | has_ticker | 1033 | 0 |
| silver_shares | positive_shares | 102195 | 984 |

DROP ROW rules: unique_ticker_day, valid_close, valid_volume, has_ticker, positive_shares, clean_ticker. Warn-only: has_sector, reconciled.

## Rows per table

| table_name | row_count |
|---|---|
| silver_securities | 1033 |
| silver_shares | 102195 |
| silver_prices | 1332972 |
| silver_index_events | 181 |
| bronze_security_master | 5608 |
| bronze_sec_companies | 10399 |
| bronze_sec_submissions | 1093 |
| bronze_sec_facts | 210389 |
| bronze_daily_prices | 1333026 |
| bronze_price_manifest | 77 |
| bronze_index_history | 181 |
| bronze_etf_aum | 295 |
| silver_prices_quarantine | 54 |
| silver_etf_aum | 295 |
| recon_market_data | 77 |
| gold_universe_monthly | 63944 |
| gold_index_constituents | 100 |
| gold_reconstitution_history | 181 |
| gold_etf_exposure | 295 |

