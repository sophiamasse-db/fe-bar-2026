# EVAL_PROTOCOL

Written and committed **2026-11-21, before any model or AI output exists.** Later changes are added as dated notes at the bottom; original results stay.

## A. Add/remove forecast (ML)

- **Question:** at a month-end snapshot two months before a December reconstitution (the October snapshot), which securities will be **added** to, or **removed** from, the NextDAQ-100?
- **Labels:** the actual reconstitution outcome in `gold_reconstitution_history`.
- **Timing rule:** features use only data known at the snapshot date (prices, volume, and shares from filings *filed* on or before that date). No feature may use data after the snapshot date.
- **Training data:** month-end snapshots before the held-out reconstitution, each labelled with the outcome of the *next* reconstitution.
- **Held out:** the most recent December reconstitution in the data, never used for training or tuning.
- **Baseline (rule):** predict **add** if a non-member ranks ≤ 100 by market cap; predict **remove** if a member ranks > 100 (no buffer, no liquidity check).
- **Main measure:** F1 for adds and F1 for removes on the held-out reconstitution; also precision and recall at K = number of actual changes.
- **No claim:** if the model's F1 does not beat the baseline's for a class, the README says so for that class and claims nothing more.
- **Edge checks:** report counts with the metric (with few changes per year, one name moves F1 a lot); do not treat the same security's monthly snapshots as independent evidence.

## B. AI impact summary and ETF-issuer notice (GenAI)

- **Inputs:** the facts of a scenario (rules, adds, removes, KPI deltas, trading impact) as structured JSON.
- **Judges** (`mlflow.genai.evaluate`, Guidelines, judge from a different model family than the generator):
  1. *Grounded:* every number and ticker appears in the given facts.
  2. *No invention:* no people, dates, prices or companies that are not in the facts.
  3. *Compliant tone:* factual, no investment advice, no forward-looking promises.
  4. *Actionable notice:* states effective date, changes and where to find details.
- **Pass bar:** ≥ 90% of rows pass every judge; any failure is shown with the judge's reason.
- **Iteration:** at most one prompt revision, before/after recorded in BUILD_LOG.md. Judges are not weakened to raise the pass rate.

## Change log

### 2026-11-21 — amendment 1 (written after v1 results, before any v2 run)

**v1 results stand as the original, official result** (job run 574811579792389; tables `ml_eval_metrics_v1`, `ai_eval_results` where prompt_version = 'v1'):
- ML, held-out Dec-2025 reconstitution from the Oct-2025 snapshot: model F1 adds 0.40 vs baseline 0.71; removes 0.67 vs baseline 0.86. **The v1 model did not beat the baseline.**
- GenAI: 0 of 8 briefs passed all four judges (no_invention 0%, grounded 75%, compliant_tone 100%, actionable_notice 100%).

Changes for v2, decided by me before running them:
1. **ML threshold** is chosen by leave-one-reconstitution-out cross-validation on 2022-2024 only (maximise mean F1 across the three folds), never on the held-out year. v1 used a fixed 0.5.
2. **ML features** add the methodology's own band flags: non-member inside the add band (rank <= 90), member outside the retention band (rank > 110). Everything else (data, held-out year, snapshot, baseline, main measure, no-claim rule) is unchanged.
3. **GenAI judge `no_invention`** was in conflict with the prompt and the `actionable_notice` judge: both require the sentence that full details follow in the official announcement. The judge now allows exactly that one reference and nothing else. No other judge changes.
4. **GenAI prompt v2** requires that exact sentence and forbids mentioning any other document, guidance, event or instruction to recipients.
5. Judge results now come from one source (the per-row assessments of the `mlflow.genai.evaluate` run), because separate judge calls on the same outputs disagreed (judges are not fully deterministic). Pass rates are reported with that caveat.

If v2 still does not beat the baseline, the README says so and the forecast is presented as a ranked watchlist with probabilities and reasons, not as more accurate than the rule.
