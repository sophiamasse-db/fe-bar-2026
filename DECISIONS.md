# DECISIONS

What I chose, what I rejected, and why. Decided step by step during the build (2026-11-21).

## Data and pipeline

1. **Raw files in a Unity Catalog volume, read with Auto Loader** - not API calls from inside the pipeline. Files can be replayed, reruns don't duplicate anything, and I can show new data arriving in the demo.
2. **Synthetic prices anchored to each company's real SEC public float** - not purely random prices. The rankings have to look like the real market, because the first thing a technical stakeholder checks is whether the top of the index makes sense.
3. **Four sources conformed** (security master, SEC fundamentals, market data, and an index history that says `symbol` where market data says `ticker`) - not one pre-merged file. It took longer, but that's what a real index data team deals with.
4. **Bad rows go to quarantine with a reason; missing sector data is a warning; a broken vendor file is a visible break** - not failing the whole update. One bad price shouldn't stop a daily process, but nothing may disappear silently.
5. **Messy public data handled in the open.** 11 SEC filers report public float about 1000x too large (rescaled), 2 were implausible (dropped), and dual-class companies use weighted-average shares. These sit next to the planted findings in the answer key.
6. **Methodology bands of 90 / 110** (add non-members ranked 90 or better, keep members ranked 110 or better) - not 75 / 125. With the wider bands the index barely changed in four years, so there was nothing to learn or to demo. 90 / 110 gives a realistic five or six changes a year, and both are sliders in the app.
7. **A generic demo identity for SEC requests** - not a personal email.

## Governance

8. **Personas are rows in an entitlements table** (methodology analyst, head of methodology, client services, admin) - not hard-coded roles. Access changes all the time: someone joins, changes sector, or gets cleared for pre-announcement data. As rows, each change is one visible, auditable update instead of a code change, and the Unity Catalog policies read the same table, so the app, Genie and SQL all enforce the same rules. Client services must never see unannounced changes or add/remove probabilities; that's the MNPI story.
9. **Access tested as a separate non-admin service principal** - not just as myself. My own account can pass while access leaks through a group membership.
10. **Governed tags used the way the workspace defines them** (domain = finance), plus our own key (nextdaq_sensitivity = mnpi) - not forcing values into a governed key that doesn't allow them.

## Serving, AI and the app

11. **The Lakebase refresh updates only the model's columns; people's review status and notes always survive** - not a read-only synced table. Approvals and analyst notes are the point of an operational store, and every change gets a history row.
12. **A trained add/remove forecast plus AI-written summaries** - not a heuristic score alone. The business asked for a forecast. The AI explains; it never ranks.
13. **The evaluation protocol was written and committed before any result**, with a simple rank-rule baseline, a held-out reconstitution, and a rule that I claim nothing if the model doesn't beat the baseline. Every later change is a dated amendment written before the rerun.
14. **The forecast is a watchlist, not a verdict.** On the reconstitution it had never seen, it didn't beat the simple "rank inside the top 100" rule (v1 and v2), so I don't claim it's more accurate. What it adds is an early, explained list of names drifting toward the cutoff, months before the reference date. The methodology rule still makes the call.
15. **The ETF-issuer notice is a template; only the internal impact summary is AI-written.** The notice goes to clients and moves money, so it has to be exactly right every time. The final AI version passed 5 of 8 briefs (6 of 8 the run before), below my 90% bar, which is why every draft goes through human approval.
16. **A different model family grades the AI** (Claude Sonnet 4.6 writes, GPT-5.5 judges) - not spot checks, so the generator never grades its own work. I used Sonnet 4.6 because the newer Claude endpoints rejected structured output through ai_query.
17. **A Streamlit app that queries with the signed-in user's token** - not FastAPI with a JavaScript front end. It was the fastest way to live sliders, and Unity Catalog policies apply to each person, not to the app.

## Orchestration and operations

18. **One job, started when new vendor files land** - not a fixed schedule. The cycle should start when a complete day of data is in. The trigger didn't fire in this workspace during testing, so the demo can also run the job manually; everything else is the same.
19. **Job code runs from a Unity Catalog volume.** Serverless reads of the bundle's workspace files failed intermittently in this workspace, so tools/deploy.sh syncs the code after each deploy.
