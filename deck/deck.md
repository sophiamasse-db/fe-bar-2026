# NextDAQ-100 Rebalance Simulator - executive deck

Google Slides: https://docs.google.com/presentation/d/1vVHQvhakpZE94rTSKyphTQd5FXsDzOe3BAKDFVts0bA/edit (PDF in this folder). NextDAQ branding on the 2025 Databricks template; built by tools/build_deck.py. Numbers match evidence/HEADLINES.md.

## Slide 1: For the Head of the Index Business and the Head of Index Methodology

- Test every rebalance rule change in minutes, before you announce it
- NextDAQ-100 Rebalance Simulator
- November 2026  ·  Powered by Databricks

**Speaker notes:** Open with the outcome. Every rule change or rebalance moves billions of dollars of ETF trading, and today it's tested in spreadsheets over days. In the next 20 minutes I'll show how your methodology team can test a change in minutes, keep pre-announcement data locked down, and record every decision. Ask: what would make this most useful for each of you? Pause and adapt.

## Slide 2: Every rebalance moves billions, yet it runs on spreadsheets

- What it costs the methodology team today
- 2-3 days
- to rebuild one scenario
- So only 3-4 options ever reach the index committee
- No record
- of who changed which rule, or why
- Approvals live in email and committee minutes
- At risk
- pre-announcement changes in shared files
- Anyone with the file sees the decision early
- Why now
- More special rebalances as a few megacaps carry more of the index
- Competitors launch custom indexes in weeks
- Regulators expect a documented, controlled methodology

**Speaker notes:** Recap discovery. Two to three analyst-days per scenario, so only three or four options reach the committee; no record of who changed what; pre-announcement changes in shared files. Why now: a few megacaps carry more of the index, so special rebalances are more frequent; competitors launch custom indexes in weeks; regulators expect a documented process. Ask: which of these costs you the most today?

## Slide 3: What you're about to see: three stops, three KPIs

- Watch the KPIs move live, and what a non-cleared user can't see
- 1
- Scenario Lab
- Change the rules and stress-test a megacap
- KPI  Days to minutes per scenario
- 2
- Compare & Approve
- AI impact summary, client notice, approval on record
- KPI  Faster proposal-to-approval
- 3
- Ask Genie
- Plain-English answers on the same governed data
- KPI  Analysts self-serve, no SQL

**Speaker notes:** TELL before the demo. Stop 1: change the rules; the liquidity floor removes a name that would take about 769 days to trade. Stop 2: compare two scenarios, get the AI summary and a templated client notice, then submit and approve. Stop 3: ask Genie in plain English. Watch the KPIs move, and note that a user who isn't cleared for MNPI sees the forecast masked by the platform. Then switch to the app.

## Slide 4: About $0.75-1.0M a year in value, on a platform you can trust

- Value is illustrative, from your discovery numbers; trust points were measured
- $0.75-1.0M
- per year, illustrative
- Analyst time
- 4 analysts x 30% of time; work cut ~80%
- $190-240k
- Fewer corrections
- From 2 to 1 or fewer a year, ~$250k each
- $250-500k
- Faster custom indexes
- 3 launches a year, 2 months sooner
- ~$300k
- Measured in the build
- < 30 ms
- to recompute a scenario across 1,015 securities
- 54 of 1.33M
- bad rows stopped before they reach weights
- 0 of 1,015
- forecast values visible to non-cleared users
- 14 of 14
- Genie answers matched the ground truth

**Speaker notes:** TELL after the demo. For the Head of Methodology: scenarios in minutes, more options per cycle, approvals with an audit trail. For the Head of the Index Business: fewer surprises for ETF issuers and faster custom index launches. The value uses your discovery numbers; I'd rather use yours. Everything on the right was measured in the build. Be honest about limits: the forecast is a watchlist, not a verdict, and a person reviews every AI draft.

## Slide 5: Next step: run the December reconstitution through it

- A 6-week pilot that shadows the 21 December 2026 reconstitution, with no risk to today's process
- Weeks 1-2   Connect
- Your security master, market data and index history; set access
- Weeks 3-4   Shadow
- Run the December scenarios in parallel with today's spreadsheets
- Weeks 5-6   Decide
- Approvals live; compare results and timings
- Success criteria
- ✓  A scenario end to end in under 5 minutes
- ✓  20+ scenarios per rebalance cycle
- ✓  Zero MNPI exposure
- ✓  Sign-off by the Head of Methodology
- The ask:  a decision by 5 December, two methodology analysts and an executive sponsor

**Speaker notes:** Close with the ask. Recap value per persona in one line each. The pilot shadows the December reconstitution, so there's no risk to today's process. Four measurable success criteria. Ask for a decision by 5 December. If time runs short: headline result, value, the pilot, the ask.
