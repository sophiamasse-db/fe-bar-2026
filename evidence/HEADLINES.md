# Headline figures (chosen by me, 2026-11-21)

These are the only numbers the README and the deck use. Each states what it is a share of, when it was measured, whether it is measured, simulated or not verified, and where the proof is.

| # | Headline (exact wording) | Share of / basis | Measured on | Status | Evidence |
|---|---|---|---|---|---|
| 1 | A rebalance scenario is recomputed in **under 30 milliseconds** (23-29 ms) for 1,015 securities, against 2-3 analyst-days in today's spreadsheet process | engine time after governed data is loaded; baseline is a discovery assumption | 2026-11-21, app logs | measured (baseline: assumption) | evidence/10_app.md |
| 2 | **54 bad rows quarantined** with a reason out of **1,333,026** landed price rows, and **1 of 77** vendor files flagged as a break (3 rows short) | all landed price rows and manifests | 2026-11-21, final run | measured | evidence/01_pipeline_run.md, evidence/02_data_quality.md |
| 3 | **0 of 1,015** forecast probabilities visible to Client Services; masked by Unity Catalog for both a switched user and a non-admin service principal | all forecast rows | 2026-11-21 | measured | evidence/06_governance.md, evidence/10_app.md |
| 4 | Genie answered **14 of 14** benchmark questions with the same result as the ground-truth SQL | approved benchmark set | 2026-11-21 | measured | evidence/08_genie.md |
| 5 | **~$0.75-1.0M a year** illustrative value (analyst time, fewer corrections, faster custom-index launches) | discovery assumptions in USE_CASE.md section 6 | - | illustrative, not verified | USE_CASE.md |

Stated alongside, never as headlines:
- The add/remove forecast did **not** beat a simple rank rule on the held-out reconstitution (F1 adds 0.40 vs 0.71; removes 0.73 vs 0.86). No accuracy claim; it is a ranked watchlist with reasons. (evidence/05_ai_evaluation.md)
- AI impact summaries: **5 of 8** passed all four judges in the final run (6 of 8 in the previous run), below the 90% bar; every draft goes through human approval. (evidence/05_ai_evaluation.md)
