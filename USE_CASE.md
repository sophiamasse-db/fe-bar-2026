# USE_CASE — NextDAQ-100 Rebalance Simulator

> Fictional customer: **NextDAQ**, an index provider that publishes and licenses the **NextDAQ-100**. All data is public (exchange symbol directory, SEC EDGAR company facts) or synthetic. Sections marked [YOUR WORDS] are to be rewritten by me; [ASSUMPTION] marks figures agreed in discovery, not measured; [CHECK] marks facts to verify.

## 1. One-line outcome

[YOUR WORDS] Cut the time to evaluate one rebalance scenario from **2–3 analyst-days to under 5 minutes**, so the methodology team can test **20+ scenarios per cycle instead of 3–4**, with every scenario versioned, approved and auditable.

## 2. The problem in the customer's words

[YOUR WORDS] "Every December, and whenever a megacap pushes us past a concentration cap, we rebuild the index in spreadsheets. One scenario takes two to three days, so we only ever look at three or four options before the committee meets. We can't easily show who changed which rule, and the pre-announcement numbers live in files on a shared drive."

**Quantified pain:** 4 analysts × ~30% of their year on scenario work, ~2 calculation corrections a year, each costing ~$250k in client remediation and reputation [ASSUMPTION].

## 3. Why now

1. **Concentration:** a handful of megacaps now hold over 40% of flagship-index weight, so cap breaches and special rebalances are more frequent and harder to predict [CHECK].
2. **Competition:** rival index providers are launching thematic and custom indexes in weeks; direct indexing is growing. A slow methodology process loses mandates.
3. **Regulation:** benchmark-administrator expectations (IOSCO Principles for Financial Benchmarks, EU Benchmarks Regulation) require a documented, controlled methodology process, and pre-announcement constituent changes are MNPI that must be access-controlled [CHECK].

## 4. Personas

| | Head of the Index Business (executive sponsor) | Head of Index Methodology & Operations (domain owner) |
|---|---|---|
| Tells the board | Licensing revenue, assets tracking the index (~$400B on the flagship) [ASSUMPTION], client retention with ETF issuers | On-time, error-free rebalances; audit findings; methodology changes approved |
| KPI owned | Licensing revenue and AUM on NextDAQ indexes; time to launch a new index | Time per scenario; scenarios per cycle; proposal-to-approval time; errors and restatements |
| Today | Learns of concentration problems late; a surprise special rebalance is a client-trust event | Team of ~4 analysts in Excel; results emailed; approval by committee minutes |

## 5. Today versus tomorrow

| | Today | Tomorrow |
|---|---|---|
| Run a scenario | 2–3 days in Excel, 3 internal feeds copied by hand | Sliders in an app; results in minutes from governed gold tables |
| Compare options | 3–4 scenarios, compared in emailed spreadsheets | 20+ scenarios, side by side on turnover, concentration, liquidity and trading impact |
| Approve and audit | Committee minutes; no record of who changed which rule | Analyst submits, head of methodology approves in-app; every change in a Lakebase audit log |
| Protect MNPI | Pre-announcement files on a shared drive | Unity Catalog restricts scenario and prediction tables to the index team |

## 6. Value hypothesis

| Value driver | Current baseline | Expected change | Assumption | Illustrative value / yr |
|---|---|---|---|---|
| Analyst time | 4 analysts × 30% on scenarios | Scenario effort cut by ~80% | $200k loaded cost per analyst | ~$190–240k |
| Fewer corrections | ~2 per year | Cut to ≤1 | ~$250k cost per correction | ~$250–500k |
| Faster custom-index launches | ~3 months to launch | ~4 weeks | 3 launches/yr × 2 months sooner × $50k/month licensing | ~$300k pulled forward |
| **Total** | | | All [ASSUMPTION] | **~$0.75–1.0M** |

Not counted: AUM retained because ETF issuers see fewer surprises, regulatory findings avoided.

## 7. The data

| Source a customer like this has | Our stand-in | Rows (approx.) | What is messy |
|---|---|---|---|
| Exchange security master | Public exchange symbol directory (pipe-delimited) | ~3,000–5,000 | Test issues, ETFs and non-common shares mixed in; footer row; trailing spaces |
| Company fundamentals | SEC EDGAR company facts (JSON) for the eligible universe | ~400 companies | Multiple filings per period; ticker–CIK gaps; restated share counts |
| Market data feed | Synthetic daily prices and volume, seeded from real tickers | ~400 × 260 days ≈ 100k | Late files, duplicate rows, a few bad prices, missing days |
| Index history | Synthetic past constituent lists and announced changes | ~3 reconstitutions | Different field names from the market data (`symbol` vs `ticker`) |
| ETF exposure | Synthetic AUM of products tracking the index | ~5 products | Monthly, arrives late |

## 8. How the six stages serve the story

- **Lakeflow:** ingests the security master, fundamentals and market data into bronze/silver/gold, with quality rules and a reconciliation, so the domain owner trusts the inputs.
- **Unity Catalog:** locks scenario and prediction tables (MNPI) to the index team, masks pre-announcement fields for others, and shows lineage from source to weights.
- **Lakebase:** stores saved scenarios, rule settings and the analyst-proposes / manager-approves workflow with a full history.
- **ML / GenAI:** a model forecasts which names are likely to be added or removed; an LLM drafts the scenario impact summary and the ETF-issuer notice.
- **Genie:** answers analyst questions in plain English, e.g. "Which tech stocks are within 5 ranks of the cutoff?"
- **App:** rule sliders, live adds/removes with bubble names, stress test, scenario A vs B comparison, AI summary, submit for approval.

## 9. What we will NOT build

- A production index calculation engine (intraday index levels, corporate-action processing, real-time dissemination).
- Real licensed market data or real announced constituent changes.
- Custom/thematic index backtesting (named as the next phase, not demoed).
- Integration with real committee, client-notification or distribution systems.

## Challenge (to resolve before approval)

1. **"It's just a spreadsheet replacement"** → we lead with MNPI control, auditability and trading impact, which spreadsheets cannot give.
2. **The ML label risk:** with synthetic history, the add/remove model only learns rules we planted. Mitigation: label from the published methodology applied to past dates, compare against a simple "rank near cutoff" baseline, and say plainly what it does and does not prove.
3. **Genie could feel bolted on** → tie it to the demo moment: "Which removed names have the highest ETF trading impact?", answered from the same gold tables the app uses.
4. **Lakebase must be essential** → the approval state and audit trail live only in Lakebase; the app's approval queue reads from it.
5. **Real-name risk:** keep the index, company and products fictional; describe past events generically.
