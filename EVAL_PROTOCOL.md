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

(none yet)
