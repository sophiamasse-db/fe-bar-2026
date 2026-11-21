# 04 — AI output: add/remove forecast and scenario briefs

Generated 2026-11-21 19:01 UTC by tools/generate_evidence.py from the live workspace.

Proves the intelligent step ran inside the flow: the MLflow model registered in Unity Catalog scored the latest snapshot (forecast with reasons), and ai_query drafted impact summaries from the facts of preset scenarios built by the same rebalance engine the app uses.

## Forecast for the next reconstitution (gold_recon_predictions)

| model_version | as_of_date | scored_rows | predicted_adds | predicted_removes |
|---|---|---|---|---|
| recon_classifier/5 | 2026-11-20T00:00:00.000Z | 1015 | 3 | 5 |

Highest-probability names:

| ticker | sector | rank | in_index | p_add | p_remove | predicted_action | top_drivers |
|---|---|---|---|---|---|---|---|
| GEHC | Health Care | 124 | true | 0.0 | 0.982 | REMOVE | rank 124 (member); outside the 110 retention band; up 16 ranks in 3 months; 3-month return +19% |
| IDXX | Health Care | 115 | true | 0.0 | 0.857 | REMOVE | rank 115 (member); outside the 110 retention band; down 14 ranks in 3 months; 3-month return -23% |
| TSCO | Consumer | 85 | false | 0.849 | 0.0 | ADD | rank 85 (non-member); inside the 90 add band; up 14 ranks in 3 months; 3-month return +42% |
| FWONA | Communication Services | 49 | false | 0.776 | 0.0 | ADD | rank 49 (non-member); inside the 90 add band; 3-month return +17% |
| MDB | Technology | 90 | false | 0.653 | 0.0 | ADD | rank 90 (non-member); inside the 90 add band |
| SNDK | Technology | 61 | false | 0.649 | 0.0 | HOLD | rank 61 (non-member); inside the 90 add band; 3-month return +17% |
| INSM | Health Care | 88 | false | 0.645 | 0.0 | HOLD | rank 88 (non-member); inside the 90 add band |
| STLD | Industrials | 101 | false | 0.519 | 0.0 | HOLD | rank 101 (non-member); 3-month return +15% |
| ZS | Technology | 98 | false | 0.505 | 0.0 | HOLD | rank 98 (non-member) |
| FANG | Energy | 92 | false | 0.453 | 0.0 | HOLD | rank 92 (non-member) |
| EXC | Utilities | 102 | true | 0.0 | 0.431 | REMOVE | rank 102 (member) |
| ON | Technology | 94 | false | 0.356 | 0.0 | HOLD | rank 94 (non-member) |

## Scenario KPIs (rebalance engine)

| scenario_id | additions | removals | turnover_pct | top10_pct | max_weight_pct | hhi | trading_impact_usd_bn | max_days_to_trade |
|---|---|---|---|---|---|---|---|---|
| S0_BASELINE | 5 | 5 | 1.12 | 58.52 | 11.43 | 450.9 | 4.5 | 30.9 |
| S1_TIGHTER_CAPS | 5 | 5 | 5.46 | 54.09 | 8.85 | 374.1 | 21.82 | 34.2 |
| S2_STRESS_LARGEST_UP_30 | 5 | 5 | 2.66 | 58.52 | 12.96 | 465.7 | 10.63 | 30.9 |
| S3_STRESS_TOP7_UP_20 | 5 | 5 | 8.86 | 50.53 | 10.67 | 382.5 | 35.42 | 36.8 |
| S4_LIQUIDITY_25M | 5 | 5 | 1.12 | 58.52 | 11.43 | 450.9 | 4.5 | 30.9 |
| S5_EXCLUDE_UTILITIES | 6 | 6 | 1.46 | 58.62 | 11.43 | 452.0 | 5.86 | 31.4 |
| S6_WIDER_BUFFER | 2 | 2 | 0.64 | 58.55 | 11.43 | 451.2 | 2.55 | 19.7 |
| S7_STRESS_TOP7_DOWN_25 | 5 | 5 | 1.12 | 58.52 | 11.43 | 450.9 | 4.5 | 30.9 |

## Verbatim AI output

### S0_BASELINE (prompt v3.1, model databricks-claude-sonnet-4-6)

Facts given (abridged):
```json
{"scenario": "S0_BASELINE", "description": "Baseline: current NextDAQ-100 methodology applied to the latest data", "as_of_date": "2026-11-20", "effective_date": "2026-12-21", "uncapped_concentration": {"max_single_weight_pct": 17.26, "single_cap_limit_pct": 24.0, "single_cap_breached": false, "aggregate_large_weight_pct": 60.43, "aggregate_cap_limit_pct": 48.0, "aggregate_cap_breached": true, "note": "before capping; capping is applied in kpis_after"}, "additions": ["FWONA", "SNDK", "TSCO", "INSM", "MDB"], "removals": ["CHTR", "VRSK", "IDXX", "KDP", "GEHC"], "kpis_after": {"turnover_pct": 1.12, "top10_weight_pct": 58.52, "max_weight_pct": 11.43, "trading_impact_usd": 4499715560.46, "max_days_to_trade": 30.88}}
```
AI impact summary (verbatim):
> Effective 2026-12-21, the NextDAQ-100 adds FWONA, SNDK, TSCO, INSM, and MDB while removing CHTR, VRSK, IDXX, KDP, and GEHC, keeping the index at 100 constituents. One-way turnover is 1.12%. The aggregate large-weight cap (48%) is breached before capping is applied, triggering redistribution; after capping, top-10 weight edges down from 58.60% to 58.52% and HHI from 452.01 to 450.88, indicating minimal concentration change. Estimated ETF trading impact is approximately $4.5 billion. TSCO is likely the most operationally challenging trade at ~30.9 days to liquidate.

Key risks (verbatim): ["Aggregate large-weight cap breached pre-capping, requiring weight redistribution across multiple constituents","TSCO trade estimated at ~30.9 days to execute, indicating potential market-impact risk","Minimal post-rebalance concentration reduction may leave index sensitivity to large-cap names largely unchanged"]

Templated ETF-issuer notice:
```
NextDAQ-100 rebalance, effective 2026-12-21 (data as of 2026-11-20).
Additions: FWONA, SNDK, TSCO, INSM, MDB.
Removals: CHTR, VRSK, IDXX, KDP, GEHC.
Full details will follow in the official announcement.
```

### S4_LIQUIDITY_25M (prompt v3.1, model databricks-claude-sonnet-4-6)

Facts given (abridged):
```json
{"scenario": "S4_LIQUIDITY_25M", "description": "Higher liquidity floor: 3-month average daily value traded of at least $25M", "as_of_date": "2026-11-20", "effective_date": "2026-12-21", "uncapped_concentration": {"max_single_weight_pct": 17.26, "single_cap_limit_pct": 24.0, "single_cap_breached": false, "aggregate_large_weight_pct": 60.43, "aggregate_cap_limit_pct": 48.0, "aggregate_cap_breached": true, "note": "before capping; capping is applied in kpis_after"}, "additions": ["FWONA", "SNDK", "TSCO", "INSM", "MDB"], "removals": ["CHTR", "VRSK", "IDXX", "KDP", "GEHC"], "kpis_after": {"turnover_pct": 1.12, "top10_weight_pct": 58.52, "max_weight_pct": 11.43, "trading_impact_usd": 4499715560.46, "max_days_to_trade": 30.88}}
```
AI impact summary (verbatim):
> Scenario S4_LIQUIDITY_25M proposes a $25M liquidity floor effective 2026-12-21, removing CHTR, VRSK, IDXX, KDP, and GEHC and adding FWONA, SNDK, TSCO, INSM, and MDB. One-way turnover is 1.12%. The aggregate large-weight cap is breached before capping is applied; after capping, the top-10 weight edges down from 58.60% to 58.52% and HHI from 452.01 to 450.88, indicating marginally reduced concentration. Estimated ETF trading impact is approximately $4.5B, with TSCO requiring the most days to trade (30.88 days), likely reflecting tighter liquidity near the new floor.

Key risks (verbatim): ["Aggregate large-weight cap breached pre-capping, requiring capping adjustments","TSCO trade estimated at ~30.9 days to execute, indicating elevated execution risk near the liquidity floor","Low turnover of 1.12% may limit rebalance effectiveness in materially reducing concentration"]

Templated ETF-issuer notice:
```
NextDAQ-100 rebalance, effective 2026-12-21 (data as of 2026-11-20).
Additions: FWONA, SNDK, TSCO, INSM, MDB.
Removals: CHTR, VRSK, IDXX, KDP, GEHC.
Full details will follow in the official announcement.
```

