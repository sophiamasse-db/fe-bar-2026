# Roleplay run-sheet — NextDAQ-100 Rebalance Simulator (20-25 min)

Two personas in the room: the **business stakeholder** (Head of the Index Business: revenue, client trust, cost, risk, time to value) and the **technical stakeholder** (architect / data lead: architecture, data quality, security, integration). Read this aloud once and change anything you wouldn't say. Numbers match evidence/HEADLINES.md.

## Timing (present ~15 min, leave ~8 for questions, close before 23 min)

| Min | Slide / stop | What happens |
|---|---|---|
| 0-2 | Slide 1 | Opening, agree the agenda, ask what they want covered |
| 2-4 | Slide 2 | The problem, in their words; why now |
| 4-5 | Slide 3 | TELL: three stops, what to watch for |
| 5-13 | Demo | SHOW: Scenario Lab → Compare & Approve → Ask Genie (+ persona view) |
| 13-15 | Slide 4 | TELL: what it means for each leader; value and trust |
| 15-23 | Questions | Answer bank below; switch altitude per persona |
| 23-25 | Slide 5 | Close and the ask (start the close by minute 23 at the latest) |

## Opening (slide 1)

"Thanks for the time. When we spoke, you told us that every December reconstitution, and every cap breach, means rebuilding the index in spreadsheets: two to three analyst-days per scenario, only a few options reach the committee, there's no clear record of who changed what, and pre-announcement numbers sit in files. The goal today is to show you how your methodology team can test a rule change in minutes, keep that data locked down, and record every decision. I'll take about fifteen minutes including a live demo, then I want most of the time for your questions. **Before I start: what would make this useful for each of you?**" → **PAUSE. Adapt to the answer.**

## Slide 2 — the problem (2 min)

Say: "Every rule change or rebalance moves billions of dollars of ETF trading, so you need to understand the impact before you announce it. Today it takes days per scenario, there's no audit trail, and the most sensitive information in the business, pre-announcement changes, sits in shared files. And it's getting harder: a handful of megacaps now drive so much of the index that special rebalances are more frequent, competitors launch custom indexes in weeks, and regulators expect a documented process."
Ask: "Which of these three costs you the most today?"
Bridge: "Let me show you what that looks like instead."

## Slide 3 — TELL before the demo (1 min)

"Three stops. First, the Scenario Lab: we'll change the rules and stress-test a megacap — watch the KPIs move. Second, Compare and Approve: two scenarios side by side, an AI draft of the impact, and the approval recorded. Third, Genie, so analysts can ask in plain English. Watch for what a user who isn't cleared for MNPI can't see."

## Demo — SHOW (8 min)

Pre-set: app open on Overview, signed in as Head of Methodology, scenarios A/B not yet kept.

1. **Overview (1 min).** TELL: "This is the methodology team's front door." Point at the journey strip (1.33M raw price rows, 54 quarantined, files reconciled) and the watch list. TELL after: "Before anyone changes a rule, they know the inputs are clean and complete."
2. **Scenario Lab (3 min).**
   - Defaults → **Keep as scenario A**. Point at: 5 additions, 5 removals, NXTT with **~769 days to trade** and the amber liquidity warning.
   - Liquidity minimum **25** → rename "Liquidity floor $25M" → **Keep as scenario B**. NXTT drops out. Point at "computed in ~25 ms".
   - Optional: stress test NVDA +30% → concentration KPIs move.
   - TELL after: "That's a scenario in milliseconds instead of days, so the team can look at 20 options instead of 3 or 4. *(time per scenario, scenarios per cycle)*"
3. **Compare & Approve (3 min).** Pick B → **Generate AI summary** → point at the templated notice ("not AI-written, because it goes to clients") → **Submit** → **Approve** with a comment → audit log shows SUBMITTED and APPROVED.
   - TELL after: "Proposal to approval in minutes, with a record of who decided what and why. *(proposal-to-approval time, errors and restatements)*"
4. **Ask Genie (1 min).** "Which predicted removals have the highest ETF trading impact?" → show answer, table, SQL.
   - TELL after: "Analysts get answers without writing SQL, on exactly the same governed data."
5. **MNPI moment (optional, 30 s, if recorded):** "Here is the same screen for Client Services: the forecast is masked by the platform, not by the app."

## Slide 4 — TELL after the demo (2 min)

"For you, Head of Methodology: scenarios in minutes, more options per cycle, approvals with an audit trail. For you, Head of the Index Business: fewer surprises for ETF issuers and faster custom index launches. On value: about $0.75 to 1 million a year, and every number shows its assumption — I'd rather replace them with yours. And why you can trust it: bad data is caught before it reaches weights, MNPI is locked down by the platform, and every AI draft is reviewed by a person."

## Close (slide 5, 2 min) — start by minute 23

"To recap: for methodology, days to minutes with a full audit trail; for the business, fewer client surprises and faster launches. I'd propose a six-week pilot that shadows the 21 December reconstitution, with four success criteria: a scenario end to end in under five minutes, twenty-plus scenarios per cycle, zero MNPI exposure, and sign-off by the Head of Methodology. What I need from you is data access, two analysts and a sponsor. **Can we agree a decision by 5 December so the pilot runs alongside the reconstitution?**"

**Short close if time runs out** (the AI starts wrapping up, or minute 22 passes without the ask): "The headline: scenarios in minutes instead of days, with MNPI locked down and every decision recorded. That's worth roughly three-quarters of a million a year on conservative assumptions. The next step is a six-week pilot alongside the December reconstitution. Can we agree to decide by 5 December?"

## Answer bank (answer first, detail second)

| Question | Answer | Enforced by / evidence / limits |
|---|---|---|
| **Success criteria?** | Scenario end to end < 5 min; 20+ scenarios per cycle; zero MNPI exposure; Head of Methodology sign-off on the pilot reconstitution. | evidence/10, 06. Not yet measured on real data. |
| **What does it cost?** | Serverless, pay per use: a full cycle runs in about 5 minutes of serverless compute, Lakebase scales to zero, the warehouse is the starter size. We'd size the pilot together; the value case is in the hundreds of thousands a year. | Exact pricing not computed in the build; offer a sizing. |
| **Results disagree with today's spreadsheet?** | That's the point of the pilot: both run in parallel, the methodology team reviews every difference before the reconstitution, and the Head of Methodology signs off. The engine is one documented file, so differences can be traced to a rule. | Process, app-supported. |
| **Can we trust the AI?** | It doesn't make decisions. The forecast is a watchlist, and I tested it honestly: it didn't beat a simple rank rule on a held-out reconstitution, so I don't claim it does. The summaries are checked by judges from another model family; they passed 5 of 8 in the final run, so a person reviews every draft. The client notice isn't AI at all. | evidence/05. Limit: small sample (6 adds, 6 removes). |
| **Late or corrupted vendor file?** | Every file is reconciled against the vendor's control totals; a short file shows as a break (we caught one, 3 rows missing), and bad rows go to quarantine with a reason. Nothing disappears silently. | Platform (pipeline expectations). evidence/02. |
| **Security / MNPI?** | Unity Catalog enforces it per person: analysts see only their sectors, client services sees the forecast masked. We tested it as a separate non-admin identity too: 0 of 1,015 probabilities visible. | Platform for Delta tables; the app enforces approvals and Lakebase rows. evidence/06. |
| **Integration with our systems?** | Raw files land in a governed volume, so your security master, market data and index history feed in as files or via connectors; the pilot's first two weeks are exactly that. Results can flow back to your calculation engine as tables. | Not built: real feeds, production calc engine. |
| **Operations?** | One job runs the whole cycle in order, queues if triggered twice, and reruns are safe (a rerun changed nothing). It's deployed from one bundle. | evidence/09. The file-arrival trigger didn't fire in this test workspace; the job ran manually. |

## Technical persona: where to go deeper (max 2 min each, then come back up)

- **Pipeline:** Auto Loader bronze → silver with expectations and quarantine → reconciliation → gold; shares are point-in-time (known 14 days after period end), so ranks use only what was known.
- **Governance:** entitlements table → row filter + masks; tested as a service principal; governed tags.
- **Lakebase:** machine-owned vs human-owned columns, the edit-survives-refresh test, history rows.
- **AI evaluation:** protocol committed first, dated amendments, judges from a different model family.
- Return line: "So for the business, that means…"

## Claims likely to be probed

| Claim | Evidence | What it doesn't cover | Say exactly |
|---|---|---|---|
| Days to minutes | 23-29 ms engine time (10_app) | Data load, review time, real data volumes; baseline is from discovery | "The engine recomputes a scenario in milliseconds; end to end we target under five minutes." |
| ~$0.75-1.0M | USE_CASE assumptions | Not measured | "Illustrative, on your discovery numbers; I'd rather use yours." |
| MNPI locked down | 06, 10 | Lakebase rows rely on the app | "The platform masks the forecast; the app controls approvals." |
| AI quality | 05 | Below the 90% bar | "5 of 8 passed every check, so a person reviews every draft." |

## Pre-flight checklist

- [ ] App warmed up (open each page once); signed in as Head of Methodology (sidebar badge)
- [ ] No new data landed since the evidence was generated
- [ ] Scenario names reset; old approvals are fine (they show the audit trail)
- [ ] Genie question pre-asked once so it answers fast
- [ ] Backup: screen recording of the full demo open in another tab
- [ ] Deck open on slide 1; this run-sheet on a second screen

## Demo route and fallback

| Stop | Live or recorded | Fallback |
|---|---|---|
| Overview, Scenario Lab | Live | Recording |
| Compare & Approve | Live | Recording; describe the audit trail from slide 4 |
| Ask Genie | Live (pre-asked) | Show the pre-asked answer |
| Persona view | Recording (needs an entitlement switch) | Describe it; point at slide 4's "0 of 1,015" |
