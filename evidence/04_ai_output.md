# 04 — AI output: add/remove forecast and scenario briefs

Generated 2026-11-21 17:50 UTC by tools/generate_evidence.py from the live workspace.

Proves the intelligent step ran inside the flow: the MLflow model registered in Unity Catalog scored the latest snapshot (forecast with reasons), and ai_query drafted impact summaries from the facts of preset scenarios built by the same rebalance engine the app uses.

## Forecast for the next reconstitution (gold_recon_predictions)

| model_version | as_of_date | scored_rows | predicted_adds | predicted_removes |
|---|---|---|---|---|
| recon_classifier/3 | 2026-11-18T00:00:00.000Z | 1015 | 4 | 7 |

Highest-probability names:

| ticker | sector | rank | in_index | p_add | p_remove | predicted_action | top_drivers |
|---|---|---|---|---|---|---|---|
| GEHC | Health Care | 124 | true | 0.0 | 0.977 | REMOVE | rank 124 (member); outside the 110 retention band; up 16 ranks in 3 months; 3-month return +17% |
| TSCO | Consumer | 84 | false | 0.844 | 0.0 | ADD | rank 84 (non-member); inside the 90 add band; up 15 ranks in 3 months; 3-month return +43% |
| IDXX | Health Care | 115 | true | 0.0 | 0.806 | REMOVE | rank 115 (member); outside the 110 retention band; down 14 ranks in 3 months; 3-month return -21% |
| FWONA | Communication Services | 51 | false | 0.784 | 0.0 | ADD | rank 51 (non-member); inside the 90 add band |
| NXTT | Technology | 69 | false | 0.664 | 0.0 | ADD | rank 69 (non-member); inside the 90 add band; up 403 ranks in 3 months; 3-month return +4307%; liquidity close to the $5M minimum |
| INSM | Health Care | 87 | false | 0.664 | 0.0 | ADD | rank 87 (non-member); inside the 90 add band |
| SNDK | Technology | 60 | false | 0.649 | 0.0 | HOLD | rank 60 (non-member); inside the 90 add band; 3-month return +16% |
| ZS | Technology | 99 | false | 0.505 | 0.0 | HOLD | rank 99 (non-member) |
| MDB | Technology | 92 | false | 0.48 | 0.0 | HOLD | rank 92 (non-member) |
| FANG | Energy | 93 | false | 0.453 | 0.0 | HOLD | rank 93 (non-member) |
| EXC | Utilities | 102 | true | 0.0 | 0.431 | REMOVE | rank 102 (member) |
| MCHP | Technology | 106 | true | 0.0 | 0.411 | REMOVE | rank 106 (member) |

## Scenario KPIs (rebalance engine)

| scenario_id | additions | removals | turnover_pct | top10_pct | max_weight_pct | hhi | trading_impact_usd_bn | max_days_to_trade |
|---|---|---|---|---|---|---|---|---|
| S0_BASELINE | 5 | 5 | 1.22 | 58.5 | 11.37 | 450.9 | 4.88 | 769.0 |
| S1_TIGHTER_CAPS | 5 | 5 | 5.46 | 54.07 | 8.83 | 374.0 | 21.86 | 851.2 |
| S2_STRESS_LARGEST_UP_30 | 5 | 5 | 2.77 | 58.5 | 12.92 | 465.7 | 11.07 | 769.0 |
| S3_STRESS_TOP7_UP_20 | 5 | 5 | 1.22 | 58.5 | 11.37 | 450.9 | 4.88 | 769.0 |
| S4_LIQUIDITY_25M | 4 | 4 | 0.97 | 58.52 | 11.37 | 451.1 | 3.89 | 31.1 |
| S5_EXCLUDE_UTILITIES | 7 | 7 | 1.55 | 58.59 | 11.37 | 451.9 | 6.2 | 781.6 |
| S6_WIDER_BUFFER | 3 | 3 | 0.88 | 58.52 | 11.37 | 451.1 | 3.51 | 771.4 |
| S7_STRESS_TOP7_DOWN_25 | 5 | 5 | 1.22 | 58.5 | 11.37 | 450.9 | 4.88 | 769.0 |

## Verbatim AI output

### S0_BASELINE (prompt v3.1, model databricks-claude-sonnet-4-6)

Facts given (abridged):
```json
{"scenario": "S0_BASELINE", "description": "Baseline: current NextDAQ-100 methodology applied to the latest data", "as_of_date": "2026-11-18", "effective_date": "2026-12-21", "uncapped_concentration": {"max_single_weight_pct": 17.23, "single_cap_limit_pct": 24.0, "single_cap_breached": false, "aggregate_large_weight_pct": 60.61, "aggregate_cap_limit_pct": 48.0, "aggregate_cap_breached": true, "note": "before capping; capping is applied in kpis_after"}, "additions": ["FWONA", "SNDK", "NXTT", "TSCO", "INSM"], "removals": ["CHTR", "VRSK", "IDXX", "KDP", "GEHC"], "kpis_after": {"turnover_pct": 1.22, "top10_weight_pct": 58.5, "max_weight_pct": 11.37, "trading_impact_usd": 4875650918.8, "max_days_to_trade": 769.03}}
```
AI impact summary (verbatim):
> For the NextDAQ-100 rebalance effective 2026-12-21, five constituents (CHTR, VRSK, IDXX, KDP, GEHC) are removed and five (FWONA, SNDK, NXTT, TSCO, INSM) are added. The aggregate-weight cap is breached before capping is applied; the single-weight cap is not breached. Post-rebalance, concentration is marginally lower (HHI 452.17 → 450.9; top-10 weight 58.59% → 58.50%). One-way turnover is 1.22%. Estimated ETF trading impact is approximately $4.9 billion. The main risk is NXTT's liquidity profile, which likely requires an estimated 769 days to trade its full position.

Key risks (verbatim): ["NXTT liquidity: estimated 769 trading days to execute the full position","Aggregate weight cap breached on a pre-capping basis, requiring redistribution","Large absolute trading volumes across all five additions (~$4.9B total ETF impact)"]

Templated ETF-issuer notice:
```
NextDAQ-100 rebalance, effective 2026-12-21 (data as of 2026-11-18).
Additions: FWONA, SNDK, NXTT, TSCO, INSM.
Removals: CHTR, VRSK, IDXX, KDP, GEHC.
Full details will follow in the official announcement.
```

### S4_LIQUIDITY_25M (prompt v3.1, model databricks-claude-sonnet-4-6)

Facts given (abridged):
```json
{"scenario": "S4_LIQUIDITY_25M", "description": "Higher liquidity floor: 3-month average daily value traded of at least $25M", "as_of_date": "2026-11-18", "effective_date": "2026-12-21", "uncapped_concentration": {"max_single_weight_pct": 17.24, "single_cap_limit_pct": 24.0, "single_cap_breached": false, "aggregate_large_weight_pct": 60.66, "aggregate_cap_limit_pct": 48.0, "aggregate_cap_breached": true, "note": "before capping; capping is applied in kpis_after"}, "additions": ["FWONA", "SNDK", "TSCO", "INSM"], "removals": ["VRSK", "IDXX", "KDP", "GEHC"], "kpis_after": {"turnover_pct": 0.97, "top10_weight_pct": 58.52, "max_weight_pct": 11.37, "trading_impact_usd": 3894682425.31, "max_days_to_trade": 31.12}}
```
AI impact summary (verbatim):
> Scenario S4_LIQUIDITY_25M raises the NextDAQ-100 liquidity floor to $25M 3-month average daily value traded, effective 2026-12-21. Four constituents (VRSK, IDXX, KDP, GEHC) are removed and four (FWONA, SNDK, TSCO, INSM) are added, keeping index size at 100. One-way turnover is 0.97%. Concentration is largely unchanged: top-10 weight moves from 58.59% to 58.52% and HHI from 452.17 to 451.14; the aggregate large-weight cap breach (60.66% vs. 48.0% limit) persists before capping and is resolved by capping rules. Estimated ETF trading impact is ~$3.9B. The largest execution challenge is likely TSCO at an estimated 31.1 days to trade.

Key risks (verbatim): ["TSCO addition requires an estimated 31.1 days to trade, the longest of any constituent change","Aggregate large-weight cap is breached before capping rules are applied, requiring capping adjustments","FWONA addition drives the single largest gross trade at ~$1.4B, with an estimated 19.7 days to execute"]

Templated ETF-issuer notice:
```
NextDAQ-100 rebalance, effective 2026-12-21 (data as of 2026-11-18).
Additions: FWONA, SNDK, TSCO, INSM.
Removals: VRSK, IDXX, KDP, GEHC.
Full details will follow in the official announcement.
```

