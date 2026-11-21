# 05 — AI evaluation and iteration history

Generated 2026-11-21 17:49 UTC by tools/generate_evidence.py from the live workspace.

Proves the AI was judged against a protocol written before any result (EVAL_PROTOCOL.md, amendments dated and committed before each rerun), with every version's result kept. ML: held-out Dec-2025 reconstitution vs a rank baseline. GenAI: four MLflow Guidelines judges (GPT-5.5) on Claude Sonnet 4.6 output.

## ML forecast: held-out reconstitution (Oct-2025 snapshot -> Dec-2025 outcome)

| version | metric_set | f1 | precision | recall | predicted | actual |
|---|---|---|---|---|---|---|
| v1 | baseline_add | 0.714 | 0.625 | 0.833 | 8 | 6 |
| v1 | baseline_remove | 0.857 | 0.75 | 1.0 | 8 | 6 |
| v1 | model_add | 0.4 | 0.5 | 0.333 | 4 | 6 |
| v1 | model_remove | 0.667 | 1.0 | 0.5 | 3 | 6 |
| v2 | baseline_add | 0.714 | 0.625 | 0.833 | 8 | 6 |
| v2 | baseline_remove | 0.857 | 0.75 | 1.0 | 8 | 6 |
| v2 | model_add | 0.4 | 0.5 | 0.333 | 4 | 6 |
| v2 | model_remove | 0.727 | 0.8 | 0.667 | 5 | 6 |

**Result: the model does not beat the simple rank baseline on F1 in v1 or v2, so no accuracy claim is made.** It is used as a ranked watchlist with probabilities and reasons. Small sample: 6 adds and 6 removes; one name moves F1 a lot.

Held-out names (v2):

| target | ticker | rank_oct | p_model | model_pred | baseline_pred | actual |
|---|---|---|---|---|---|---|
| ADD | CSGP | 63 | 0.894 | 1 | 1 | 1 |
| ADD | PAYX | 75 | 0.888 | 1 | 1 | 1 |
| ADD | GEHC | 96 | 0.416 | 0 | 1 | 1 |
| ADD | COO | 97 | 0.345 | 0 | 1 | 1 |
| ADD | EXPE | 100 | 0.248 | 0 | 1 | 1 |
| ADD | MPWR | 102 | 0.084 | 0 | 0 | 1 |
| ADD | FWONA | 86 | 0.946 | 1 | 1 | 0 |
| ADD | SNDK | 88 | 0.902 | 1 | 1 | 0 |
| ADD | BIIB | 99 | 0.244 | 0 | 1 | 0 |
| REMOVE | SFM | 160 | 0.757 | 1 | 1 | 1 |
| REMOVE | LULU | 119 | 0.755 | 1 | 1 | 1 |
| REMOVE | SMCI | 126 | 0.548 | 1 | 1 | 1 |
| REMOVE | ODFL | 113 | 0.49 | 1 | 1 | 1 |
| REMOVE | FSLR | 120 | 0.086 | 0 | 1 | 1 |
| REMOVE | TSCO | 105 | 0.035 | 0 | 1 | 1 |
| REMOVE | MCHP | 91 | 0.248 | 1 | 0 | 0 |
| REMOVE | CTSH | 108 | 0.023 | 0 | 1 | 0 |
| REMOVE | VRSK | 101 | 0.014 | 0 | 1 | 0 |

## GenAI briefs: pass rate per judge and version

| prompt_version | judge | rows | pass_pct |
|---|---|---|---|
| v1 | actionable_notice | 8 | 100.0 |
| v1 | compliant_tone | 8 | 100.0 |
| v1 | grounded | 8 | 75.0 |
| v1 | no_invention | 8 | 0.0 |
| v2 | actionable_notice | 8 | 100.0 |
| v2 | compliant_tone | 8 | 87.5 |
| v2 | grounded | 8 | 62.5 |
| v2 | no_invention | 8 | 0.0 |
| v3 | actionable_notice | 8 | 100.0 |
| v3 | compliant_tone | 8 | 87.5 |
| v3 | grounded | 8 | 100.0 |
| v3 | no_invention | 8 | 12.5 |
| v3.1 | actionable_notice | 8 | 100.0 |
| v3.1 | compliant_tone | 8 | 87.5 |
| v3.1 | grounded | 8 | 100.0 |
| v3.1 | no_invention | 8 | 87.5 |

Briefs passing every judge:

| prompt_version | briefs | passing_all_judges |
|---|---|---|
| v1 | 8 | 0 |
| v2 | 8 | 0 |
| v3 | 8 | 1 |
| v3.1 | 8 | 6 |

Final version (v3.1) is below the 90% bar set in the protocol; drafts therefore always go through human approval in the app. Remaining failures (judge reasons):

| scenario_id | judge | judge_reason |
|---|---|---|
| S3_STRESS_TOP7_UP_20 | no_invention | The response generally uses the tickers, dates, scenario, index, KPI values, turnover, trading impact, and days-to-trade values that are present in the provided facts, and the sentence “Full details will follow in the official announcement” is explicitly allow |
| S2_STRESS_LARGEST_UP_30 | compliant_tone | The response is generally neutral and does not provide explicit investment advice, a buy/sell recommendation, or a promise about future investment performance. However, the guideline also requires the output to be factual. The statement that “The hardest-to-tr |
