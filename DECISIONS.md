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
