# 01 — Lakeflow pipeline run

Generated 2026-11-21 15:56 UTC by tools/generate_evidence.py from the live workspace.

Proves the serverless Lakeflow Spark Declarative Pipeline `nextdaq_pipeline` (src/pipeline/*.sql) ran to COMPLETED, shows rows per table across bronze/silver/gold, the expectation pass/fail counts read from the pipeline event log, and that a rerun does not duplicate rows.

Pipeline id: `ecd0a7d6-364e-4bf1-98d1-1b2688c1d3a8` (serverless, catalog `fe_bar_2026_kelemen_catalog`, schema `nextdaq_index`).

## Recent updates

| update | state | full refresh | created (UTC) | cause |
|---|---|---|---|---|
| c9a1294b | COMPLETED | False | 2026-11-21 15:55 | API_CALL |
| dcc4a050 | COMPLETED | True | 2026-11-21 15:52 | API_CALL |
| 5bb6b9be | COMPLETED | False | 2026-11-21 15:41 | API_CALL |
| 2a169509 | COMPLETED | False | 2026-11-21 15:40 | RETRY_ON_FAILURE |
| 2a9f34fc | FAILED | False | 2026-11-21 15:38 | API_CALL |

Durations from the event log:

| update_id | started | ended | seconds |
|---|---|---|---|
| c9a1294b-a558-4556-9013-0fbe44934766 | 2026-11-21T15:55:18.843Z | 2026-11-21T15:56:18.072Z | 59.0 |
| dcc4a050-5d12-454f-a2d7-f5bc0e223081 | 2026-11-21T15:52:03.793Z | 2026-11-21T15:53:37.936Z | 94.0 |
| 5bb6b9be-8c6a-4b3d-abbb-da54f20e9c25 | 2026-11-21T15:41:56.230Z | 2026-11-21T15:42:51.625Z | 55.0 |

## Expectations (latest completed update)

| dataset | expectation | passed | failed |
|---|---|---|---|
| recon_market_data | reconciled | 74 | 1 |
| silver_index_events | clean_ticker | 181 | 0 |
| silver_prices | unique_ticker_day | 1330957 | 37 |
| silver_prices | valid_close | 1330982 | 12 |
| silver_prices | valid_volume | 1330989 | 5 |
| silver_securities | has_sector | 1020 | 13 |
| silver_securities | has_ticker | 1033 | 0 |
| silver_shares | positive_shares | 102195 | 984 |

DROP ROW rules: unique_ticker_day, valid_close, valid_volume, has_ticker, positive_shares, clean_ticker. Warn-only: has_sector, reconciled.

## Rows per table

| table_name | row_count |
|---|---|
| silver_securities | 1033 |
| silver_shares | 102195 |
| silver_prices | 1330940 |
| silver_index_events | 181 |
| bronze_security_master | 5608 |
| bronze_sec_companies | 10399 |
| bronze_sec_submissions | 1093 |
| bronze_sec_facts | 210389 |
| bronze_daily_prices | 1330994 |
| bronze_price_manifest | 75 |
| bronze_index_history | 181 |
| bronze_etf_aum | 295 |
| silver_prices_quarantine | 54 |
| silver_etf_aum | 295 |
| recon_market_data | 75 |
| gold_universe_monthly | 63944 |
| gold_index_constituents | 100 |
| gold_reconstitution_history | 181 |
| gold_etf_exposure | 295 |

## Rerun test (idempotency)

The pipeline was run again with no new files. Row counts before and after: IDENTICAL.

| table_name | row_count |
|---|---|
| silver_securities | 1033 |
| silver_shares | 102195 |
| silver_prices | 1330940 |
| silver_index_events | 181 |
| bronze_security_master | 5608 |
| bronze_sec_companies | 10399 |
| bronze_sec_submissions | 1093 |
| bronze_sec_facts | 210389 |
| bronze_daily_prices | 1330994 |
| bronze_price_manifest | 75 |
| bronze_index_history | 181 |
| bronze_etf_aum | 295 |
| silver_prices_quarantine | 54 |
| silver_etf_aum | 295 |
| recon_market_data | 75 |
| gold_universe_monthly | 63944 |
| gold_index_constituents | 100 |
| gold_reconstitution_history | 181 |
| gold_etf_exposure | 295 |

