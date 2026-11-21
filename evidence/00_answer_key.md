# 00 — Answer key and landed data inventory

Generated 2026-11-21 15:37 UTC by tools/evidence_00_answer_key.py from the live workspace.
This file proves the raw data exists in the UC volume, what was planted in it, and that the planted counts can be recomputed from the files alone (independently of the generator). Seed 2026; reruns give the same counts.

## Universe and history

- 1016 issuers (public symbol directory + SEC filers with public float >= $300M), 1312 trading days, 2021-09-01 to 2026-11-20; last 2 days (20261119, 20261120) held back in `landing/holdback/` to land live in the demo.
- Reconstitutions (effective): 2021-12-20, 2022-12-19, 2023-12-18, 2024-12-23, 2025-12-22. Held out for ML evaluation: **2025-12-22**.
- Planted rally names (seven largest after the 2024 reconstitution): MSFT, NVDA, AAPL, AMZN, AVGO, META, GOOGL.

## Planted findings

| Finding | Count | Where | How the build catches it |
|---|---|---|---|
| Duplicate ticker-day rows (re-sent rows in one file) | 37 | mkt_prices_202503.csv | silver_prices_quarantine reason DUPLICATE_TICKER_DAY |
| Null close price | 6 | spread across monthly files | reason MISSING_CLOSE |
| Zero or negative close price | 6 | spread across monthly files | reason NON_POSITIVE_CLOSE |
| Negative volume | 5 | spread across monthly files | reason NEGATIVE_VOLUME |
| Manifest break: file truncated in transit | 3 | mkt_prices_20261113.csv | recon_market_data status BREAK |
| Index-history symbols not conformed (lower case / trailing spaces) | 3 | index_history/nextdaq100_changes.csv | silver_index_events: upper(trim(symbol)) |
| SEC filers with SIC blanked (planted, hash-selected) | 10 | public/sec_sic/ | silver_securities expectation has_sector (warn) |
| Megacap rally -> special rebalance | 1 | reference 2025-05-30, effective 2025-06-23 | gold_reconstitution_history event_type SPECIAL_REBALANCE |
| Committee discretion: rule says add, not added | 4 | {"2024": ["LRCX", "PANW"], "2025": ["CRWV", "PANW"]} | limits any rule-only forecast |

## Real issues found in the public SEC data (not planted)

- Public float ~1000x too large (XBRL scale error), rescaled /1000: CIVB, EVER, HUBG, MCFT, MGRC, OLED, RENX, TEM, THRM, TRMK, TTMI.
- Still implausible after the check, dropped from the universe: MREO, OPEN.
- Dual-class filers have no cover-page share count in SEC frames; weighted-average basic shares used instead (silver_shares.shares_source = WEIGHTED_AVERAGE_FALLBACK).

## Recomputed from the landed files (SQL on the volume)

Prices:

| landed_price_rows | duplicate_rows | null_close | non_positive_close | negative_volume | tickers | first_day | last_day |
|---|---|---|---|---|---|---|---|
| 1330994 | 37 | 6 | 6 | 5 | 1016 | 2021-09-01 | 2026-11-18 |

Manifests vs files:

| manifests | counts_match | counts_break | break_detail |
|---|---|---|---|
| 75 | 74 | 1 | mkt_prices_20261113.csv: control 1016 vs landed 1013 |

Index history:

| event_type | action | rows | messy_symbols | first_effective | last_effective |
|---|---|---|---|---|---|
| ANNUAL_RECONSTITUTION | ADD | 13 | 1 | 2022-12-19 | 2025-12-22 |
| ANNUAL_RECONSTITUTION | REMOVE | 13 | 2 | 2022-12-19 | 2025-12-22 |
| INITIAL_COMPOSITION | ADD | 100 | 0 | 2021-12-20 | 2021-12-20 |
| SPECIAL_REBALANCE | REWEIGHT | 23 | 0 | 2025-06-23 | 2025-06-23 |

SEC SIC extract (10 planted blanks + filers SEC itself leaves blank):

| sec_sic_records | blank_sic |
|---|---|
| 1093 | 24 |

## File inventory

| Folder | Entries |
|---|---|
| `landing/public/security_master/` | 1 |
| `landing/public/sec_companies/` | 1 |
| `landing/public/sec_sic/` | 1 |
| `landing/public/sec_facts/EntityCommonStockSharesOutstanding/` | 22 |
| `landing/public/sec_facts/EntityPublicFloat/` | 22 |
| `landing/public/sec_facts/WeightedAverageNumberOfSharesOutstandingBasic/` | 21 |
| `landing/prices/` | 63 |
| `landing/price_manifests/` | 75 |
| `landing/index_history/` | 1 |
| `landing/etf_aum/` | 59 |
| `landing/holdback/prices/2026-11/` | 2 |
| `landing/holdback/price_manifests/` | 2 |

## Samples (verbatim)

`prices/2026-11/mkt_prices_20261102.csv` (first rows):
```
TradeDate,Ticker,Open,High,Low,Close,Volume,Currency
2026-11-02,NVDA,251.0003,255.7527,249.3448,253.6549,185143297,USD
2026-11-02,AAPL,362.2247,368.0746,359.8559,363.4942,42917084,USD
2026-11-02,MSFT,630.4492,633.3648,622.6994,626.2887,17064193,USD
```
`price_manifests/mkt_prices_20261102.json`:
```
{"file_name": "mkt_prices_20261102.csv", "period": "20261102", "record_count": 1016, "volume_total": 7217278411, "source_system": "MKTDATA_VENDOR"}
```
`index_history/nextdaq100_changes.csv` (header + special-rebalance rows):
```
effective_date,announcement_date,symbol,event_type,action,weight_after,reference_date
2025-06-23,2025-06-13,AAPL,SPECIAL_REBALANCE,REWEIGHT,0.083607,2025-05-30
2025-06-23,2025-06-13,AMD,SPECIAL_REBALANCE,REWEIGHT,0.019583,2025-05-30
2025-06-23,2025-06-13,AMGN,SPECIAL_REBALANCE,REWEIGHT,0.008167,2025-05-30
2025-06-23,2025-06-13,AMZN,SPECIAL_REBALANCE,REWEIGHT,0.052835,2025-05-30
2025-06-23,2025-06-13,AVGO,SPECIAL_REBALANCE,REWEIGHT,0.044,2025-05-30
2025-06-23,2025-06-13,BKNG,SPECIAL
```
