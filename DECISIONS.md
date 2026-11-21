# DECISIONS

[REWRITE IN YOUR WORDS] — drafted by my AI pair from my choices on 2026-11-21. Each item: what I chose, what I rejected, why.

1. **Ingestion: files in a UC volume read with Auto Loader** over calling APIs from inside the pipeline. Landed files can be replayed, reruns are safe, and I can demo new data arriving.
2. **Realistic market caps: synthetic prices anchored to each company's real SEC public float ÷ shares outstanding**, then a random walk, over purely random prices. Rankings look believable (megacaps on top), which a technical stakeholder would check.
3. **Four sources conformed** (security master, SEC fundamentals, market data, index history with `symbol` vs `ticker`) over one pre-merged file. It costs ~30 min but shows real conforming work.
4. **Data quality: drop-to-quarantine** for null/≤0 prices, negative volume and duplicate ticker-days; **warn** for missing sector (SIC); reconciliation BREAKs are visible but do not fail the update. Failing the whole update on one bad price is too brittle for a daily process.
5. **Four personas from an entitlements table** (methodology analyst, head of methodology, client services, admin) over two personas. Client services must never see unannounced changes or add/remove probabilities: that is the MNPI story.
6. **Non-admin test with a dedicated service principal** over testing only as myself, because my own user can pass while access leaks through a group.
7. **Lakebase: job upsert into `security_watch`** (machine-owned columns refreshed, analyst notes and review status kept) **plus app-owned scenario, approval and audit tables**, over a read-only synced table. Approvals and human notes must survive every refresh.
8. **Intelligence: a trained classifier (MLflow, UC registry) plus `ai_query` summaries**, over a heuristic score alone. The business asked for a forecast of adds/removes; the LLM explains, it does not rank.
9. **AI evaluation with MLflow GenAI judges from a different model family** (GPT judges Claude) over manual spot checks, so the generator does not grade itself.
10. **Evaluation protocol written before results** (EVAL_PROTOCOL.md): rank-band baseline, held-out latest reconstitution, no claim if the model does not beat the baseline.
11. **Streamlit app with the signed-in user's token** over FastAPI + JS: fastest path to live sliders, and Unity Catalog policies apply per user.
12. **File-arrival trigger on the price manifest** over a schedule or manual runs: the cycle starts only when a full day of data has landed.
13. **SEC requests use a generic demo User-Agent**, not a personal email.
14. **Methodology bands: add at rank 90, keep to rank 110** (over 75 / 125). With the wider bands the index barely changed (6 changes in four years) and nothing could be learned or demoed; 90/110 gives ~5-6 changes a year, close to real large-cap indexes. Both are exposed as sliders.
15. **Messy public data handled, not hidden:** 11 SEC filers report public float ~1000x too large (rescaled), 2 dropped as implausible, dual-class filers use weighted-average shares. Recorded as real findings next to the planted ones.
16. **The forecast is a ranked watchlist, not a replacement for the rule.** It did not beat a simple rank rule on the held-out reconstitution (v1 and v2), so no accuracy claim is made; its value is early, explained probabilities for the methodology team.
17. **The ETF-issuer notice is a template; only the impact summary is AI-written.** A client-facing regulated notice should never be free LLM text. Each change to the prompt or judges was a dated amendment written before the rerun; the final version (v3.1) passes 6/8 and every draft goes through human approval.
18. **Claude Sonnet 4.6 generates, GPT-5.5 judges.** Newer Claude endpoints rejected structured output through ai_query; a different model family judges so the generator does not grade itself.
19. **Governed tags used as the workspace defines them** (domain = finance) plus our own key (nextdaq_sensitivity = mnpi), instead of overloading a governed key with values it does not allow.
20. **Job code runs from a Unity Catalog volume**, because serverless reads of bundle workspace files failed intermittently in this workspace; tools/deploy.sh syncs the code after each deploy.
21. **File-arrival trigger kept, demo can run manually.** It did not fire in this workspace during testing; the job is otherwise identical.
