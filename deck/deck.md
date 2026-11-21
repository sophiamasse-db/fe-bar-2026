# NextDAQ-100 Rebalance Simulator - business deck

Google Slides: https://docs.google.com/presentation/d/1vVHQvhakpZE94rTSKyphTQd5FXsDzOe3BAKDFVts0bA/edit (PDF in this folder). Built on the 2025 Databricks corporate template. Numbers match evidence/HEADLINES.md.

## Slide 1: Test every rebalance rule change in minutes, before you announce it

NextDAQ-100 Rebalance Simulator  
For the Head of the Index Business and the Head of Index Methodology

NextDAQ · November 2026

**Speaker notes:** Open with the outcome. Today every rule change or rebalance is tested in spreadsheets over days, while billions of dollars of ETF trading depend on getting it right. In the next 20 minutes I'll show how the methodology team can test a change in minutes, keep pre-announcement data locked down, and record every decision. Ask: what would you most like to see covered today? Pause and adapt.

## Slide 2: Every rebalance moves billions, yet runs on spreadsheets

2-3 analyst-days to rebuild one scenario  
Only 3-4 options reach the index committee  
Late surprises cost trust with ETF issuers

No record of who changed which rule, or why  
Approvals live in minutes and email  
Errors lead to corrections and restatements

Pre-announcement changes sit in shared files  
Anyone with the file sees the decision  
Regulators expect controlled access

Days per scenario

No audit trail

MNPI at risk

Why now: more special rebalances, faster competitors, tougher benchmark oversight

**Speaker notes:** Recap what we heard in discovery. Each December reconstitution and every cap breach is rebuilt in spreadsheets, two to three analyst-days per scenario, so only a handful of options reach the committee. There is no audit trail, and pre-announcement numbers sit in files. Why now: a few megacaps now drive so much of the index that special rebalances are more frequent, competitors launch custom indexes in weeks, and benchmark regulation expects a documented process. Question to the room: which of these hurts most today?

## Slide 3: What you're about to see: three stops, three KPIs

Change caps, liquidity floor and bands; stress-test a megacap  
KPI: time per scenario, days to minutes  
KPI: scenarios per cycle, 3-4 to 20+

Scenario A vs B, AI impact summary, templated client notice  
Submit and approve, recorded in Lakebase  
KPI: proposal-to-approval time

Plain-English questions on the same governed data  
"Which removals have the highest ETF trading impact?"  
KPI: analyst productivity, no SQL

1 · Scenario Lab

2 · Compare & Approve

3 · Ask Genie

Watch for: KPIs moving live, the AI draft, what a non-cleared user can't see

**Speaker notes:** TELL before the demo. Stop 1: change the rules and watch who joins or leaves; the liquidity floor removes a name that would take about 769 days to trade. Stop 2: compare two scenarios, get the AI summary and a templated client notice, then submit and approve. Stop 3: ask Genie in plain English. Watch the KPIs move, and remember that a user who isn't cleared for MNPI sees the forecast masked by the platform. Then switch to the app.

## Slide 4: ~$0.75-1.0M a year, on a platform you can trust

Analyst time: ~$190-240k (4 analysts x 30% of time; scenario work cut ~80%)  
Fewer corrections: ~$250-500k (from 2 to 1 or fewer a year, ~$250k each)  
Faster custom indexes: ~$300k pulled forward (3 launches a year, 2 months sooner)

Scenario recomputed in under 30 ms across 1,015 securities  
54 bad rows quarantined and 1 broken vendor file caught, out of 1.33M rows  
0 of 1,015 forecast probabilities visible to non-cleared users  
Every scenario, approval and change recorded; AI drafts reviewed by a person

The value (illustrative)

Why you can trust it (measured)

Value is illustrative (discovery assumptions); trust points are measured

**Speaker notes:** TELL after the demo: land what it means for each leader. For the Head of Methodology: scenarios in minutes, more options per cycle, approvals with an audit trail. For the Head of the Index Business: fewer surprises for ETF issuers and faster custom index launches. Every value number shows its assumption, and I'm happy to replace them with your figures. Be honest about limits: the forecast is a watchlist, not a verdict, and every AI draft is reviewed by a person.

## Slide 5: Next step: run the December reconstitution through it

Weeks 1-2: connect your security master, market data and index history; set entitlements  
Weeks 3-4: run the reconstitution scenarios in parallel with today's process  
Weeks 5-6: approvals live; compare results and timings with the spreadsheets  
Success: a scenario in under 5 minutes end to end · 20+ scenarios per cycle · zero MNPI exposure · Head of Methodology sign-off  
We need: data access, two methodology analysts, an executive sponsor. Decision by 5 December.

A 6-week pilot that shadows the 21 December 2026 reconstitution

**Speaker notes:** Close with a direct ask. Recap value per persona in one line each. Propose the bounded pilot that shadows the December reconstitution, with four measurable success criteria. Ask for a decision by 5 December so the pilot can run alongside the reconstitution. If the session ends early: headline result, value, the pilot, the ask.
