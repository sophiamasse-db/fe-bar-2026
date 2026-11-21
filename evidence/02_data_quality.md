# 02 — Data quality and completeness

Generated 2026-11-21 19:01 UTC by tools/generate_evidence.py from the live workspace.

Proves bad rows are quarantined with a reason (nothing disappears silently), every vendor file is reconciled against its control totals, and conforming rules work. Compare with the planted counts in 00_answer_key.md.

## Quarantine (silver_prices_quarantine)

| reject_reason | rows | files |
|---|---|---|
| DUPLICATE_TICKER_DAY | 37 | 1 |
| MISSING_CLOSE | 6 | 5 |
| NON_POSITIVE_CLOSE | 6 | 6 |
| NEGATIVE_VOLUME | 5 | 5 |

Sample rows per reason:

| reject_reason | ticker | trade_date | close | volume | _file_name |
|---|---|---|---|---|---|
| DUPLICATE_TICKER_DAY | AGYS | 2025-03-18 | 138.3977 | 70093 | mkt_prices_202503.csv |
| DUPLICATE_TICKER_DAY | ALKS | 2025-03-28 | 33.4287 | 1410283 | mkt_prices_202503.csv |
| MISSING_CLOSE | AMAL | 2023-04-11 |  | 748917 | mkt_prices_202304.csv |
| MISSING_CLOSE | DNLI | 2024-04-18 |  | 2378188 | mkt_prices_202404.csv |
| NEGATIVE_VOLUME | AHCO | 2024-12-17 | 9.3441 | -438211 | mkt_prices_202412.csv |
| NEGATIVE_VOLUME | HBNC | 2025-09-30 | 12.4204 | -560067 | mkt_prices_202509.csv |
| NON_POSITIVE_CLOSE | HROW | 2021-10-05 | 0.0 | 813023 | mkt_prices_202110.csv |
| NON_POSITIVE_CLOSE | LAUR | 2026-05-21 | 0.0 | 364427 | mkt_prices_202605.csv |

## Reconciliation (recon_market_data)

| status | files | control_rows | landed_rows | loaded_rows | quarantined_rows |
|---|---|---|---|---|---|
| RECONCILED | 76 | 1332013 | 1332013 | 1331959 | 54 |
| BREAK | 1 | 1016 | 1013 | 1013 | 0 |

Files with a break or quarantined rows:

| file_name | control_count | landed_rows | loaded_rows | quarantined_rows | control_volume | landed_volume | status |
|---|---|---|---|---|---|---|---|
| mkt_prices_202110.csv | 21336 | 21336 | 21335 | 1 | 54480180234 | 54480180234 | RECONCILED |
| mkt_prices_202208.csv | 23368 | 23368 | 23367 | 1 | 138421610604 | 138421610604 | RECONCILED |
| mkt_prices_202209.csv | 21336 | 21336 | 21335 | 1 | 126710311772 | 126710311772 | RECONCILED |
| mkt_prices_202304.csv | 19304 | 19304 | 19303 | 1 | 106924205322 | 106924205322 | RECONCILED |
| mkt_prices_202310.csv | 22352 | 22352 | 22351 | 1 | 130162070034 | 130162070034 | RECONCILED |
| mkt_prices_202311.csv | 21336 | 21336 | 21335 | 1 | 124227518030 | 124227518030 | RECONCILED |
| mkt_prices_202404.csv | 22352 | 22352 | 22351 | 1 | 114949836584 | 114949836584 | RECONCILED |
| mkt_prices_202406.csv | 19304 | 19304 | 19303 | 1 | 114176641861 | 114176641861 | RECONCILED |
| mkt_prices_202410.csv | 23368 | 23368 | 23366 | 2 | 119555346827 | 119555346827 | RECONCILED |
| mkt_prices_202412.csv | 21336 | 21336 | 21335 | 1 | 97120326680 | 97120326680 | RECONCILED |
| mkt_prices_202503.csv | 21373 | 21373 | 21336 | 37 | 88820413299 | 88820413299 | RECONCILED |
| mkt_prices_202505.csv | 21336 | 21336 | 21335 | 1 | 84295152454 | 84295152454 | RECONCILED |
| mkt_prices_202508.csv | 21336 | 21336 | 21335 | 1 | 89366192215 | 89366192215 | RECONCILED |
| mkt_prices_202509.csv | 21336 | 21336 | 21335 | 1 | 104153296258 | 104153296258 | RECONCILED |
| mkt_prices_202511.csv | 19304 | 19304 | 19303 | 1 | 93666352952 | 93666352952 | RECONCILED |
| mkt_prices_202605.csv | 20320 | 20320 | 20319 | 1 | 107164717326 | 107164717326 | RECONCILED |
| mkt_prices_202607.csv | 22352 | 22352 | 22351 | 1 | 143872310939 | 143872310939 | RECONCILED |
| mkt_prices_20261113.csv | 1016 | 1013 | 1013 | 0 | 8730217557 | 8730007718 | BREAK |

## Conforming index history (`symbol` -> `ticker`)

| symbol_as_received | ticker | event_type | action | effective_date |
|---|---|---|---|---|
| cvlt | CVLT | ANNUAL_RECONSTITUTION | REMOVE | 2022-12-19 |
| WWD   | WWD | ANNUAL_RECONSTITUTION | REMOVE | 2022-12-19 |
| ALNY   | ALNY | ANNUAL_RECONSTITUTION | ADD | 2024-12-23 |

## Sector from SEC SIC (silver_securities)

| sector | issuers |
|---|---|
| Health Care | 225 |
| Financials | 223 |
| Technology | 219 |
| Industrials | 186 |
| Consumer | 110 |
| Communication Services | 22 |
| Utilities | 18 |
| Unclassified | 13 |
| Materials | 9 |
| Energy | 8 |

## Share-count source (point in time, known 14 days after period end)

| shares_source | filers | rows |
|---|---|---|
| COVER_PAGE | 8395 | 95361 |
| WEIGHTED_AVERAGE_FALLBACK | 758 | 6834 |
