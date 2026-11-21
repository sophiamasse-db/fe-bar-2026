# 08 — Genie agent benchmark

Generated 2026-11-21 18:13 UTC by tools/generate_evidence.py from the live workspace.

Proves the Genie space `NextDAQ-100 Index Methodology Genie` (id 01f1e5d540d61ef3b6d757b4cb45a66e; definition in src/genie/space.json) answers the approved business questions correctly over the governed gold tables: each question was asked through the Genie Conversation API as the signed-in user and compared with ground-truth SQL from src/genie/benchmarks.py.

Iteration: run 1 (same day) gave 12/14 exact matches; Q05 was labelled by effective date instead of year and Q08 used 12 instead of 13 month-end snapshots. Two definitions were added to the space instructions (tools/genie.py) and every benchmark was rerun.

**Result: 14 of 14 exact matches.**

| id | question | expected (key column) | Genie answer (first columns) | verdict |
|---|---|---|---|---|
| Q01 | Which securities rank within 5 places of the cutoff (ranks 95 to 105) on the latest snapshot? | 11 rows: ROP, ON, WDAY, MPWR, ZS, CPRT, TEAM, EXC ... | 11 rows: ROP, ROPER TECHNOLOGIES INC, 95; ON, ON SEMICONDUCTOR CORP, 96; WDAY, Workday, Inc., 97; MPWR, MONOLITHIC POWER SYSTEMS, INC., 98 ... | **MATCH** |
| Q02 | Which Technology stocks are within 10 ranks of the cutoff on the latest snapshot? | 9 rows: MDB, ROP, ON, WDAY, MPWR, ZS, TEAM, CTSH ... | 9 rows: MDB, MongoDB, Inc., 92; ROP, ROPER TECHNOLOGIES INC, 95; ON, ON SEMICONDUCTOR CORP, 96; WDAY, Workday, Inc., 97 ... | **MATCH** |
| Q03 | Which current index members rank worse than 110 on the latest snapshot? | 4 rows: VRSK, IDXX, KDP, GEHC | 4 rows: GEHC, GE HealthCare Technologies Inc., 124; KDP, Keurig Dr Pepper Inc., 120; IDXX, IDEXX LABORATORIES INC /DE, 115; VRSK, Verisk Analytics, Inc., 111 | **MATCH** |
| Q04 | Which non-members rank inside the top 90 on the latest snapshot? | 5 rows: FWONA, SNDK, NXTT, TSCO, INSM | 5 rows: FWONA, Liberty Media Corp, 51; SNDK, Sandisk Corp, 60; NXTT, Next Technology Holding Inc., 69; TSCO, TRACTOR SUPPLY CO /DE/, 84 ... | **MATCH** |
| Q05 | How many additions and removals were there in each of the last 3 annual reconstitutions? | 3 rows: 2025, 2024, 2023 | 3 rows: 2025, 2025-12-22, 6; 2024, 2024-12-23, 6; 2023, 2023-12-18, 5 | **MATCH** |
| Q06 | When were the special rebalances and how many names were reweighted in each? | 2 rows: 14, 23 | 2 rows: 2022-10-24, 14; 2025-06-23, 23 | **MATCH** |
| Q07 | Which 10 current index members have the lowest 3-month average daily value traded? | 10 rows: MPWR, TTD, SNPS, XEL, MCHP, IDXX, EBAY, PODD ... | 10 rows: MPWR, MONOLITHIC POWER SYSTEMS, INC., Technology; TTD, Trade Desk, Inc., Technology; SNPS, SYNOPSYS INC, Technology; XEL, XCEL ENERGY INC, Utilities ... | **MATCH** |
| Q08 | How has SMCI's market-cap rank changed over the last 12 months? | 13 rows: 142, 142, 142, 142, 138, 129, 134, 140 ... | 13 rows: 2025-11-28, SMCI, Super Micro Computer, Inc.; 2025-12-31, SMCI, Super Micro Computer, Inc.; 2026-01-30, SMCI, Super Micro Computer, Inc.; 2026-02-27, SMCI, Super Micro Computer, Inc. ... | **MATCH** |
| Q09 | How many securities are eligible for the index on the latest snapshot? | 1 rows: 652 | 1 rows: 652 | **MATCH** |
| Q10 | What are the combined top-10 weight and the largest single weight in the current index? | 1 rows: 58.59 | 1 rows: 58.59, 11.37 | **MATCH** |
| Q11 | What were the total assets tracking the index at each month-end in 2026? | 11 rows: 3.7793399996148E11, 3.4788422224732996E11, 3.6978104893334E11, 3.7507655221487E11, 3.8521777305483E11, 3.9131094395008E11, 4.0173376626755005E11, 3.8430547240734E11 ... | 11 rows: 2026-01-30, 3.7793399996148E11; 2026-02-27, 3.4788422224732996E11; 2026-03-31, 3.6978104893334E11; 2026-04-30, 3.7507655221487E11 ... | **MATCH** |
| Q12 | How many members does each sector have in the current index? | 7 rows: 42, 20, 19, 11, 4, 3, 1 | 7 rows: Technology, 42; Industrials, 20; Consumer, 19; Health Care, 11 ... | **MATCH** |
| Q13 | Which names does the forecast predict will be added or removed at the next reconstitution? | 11 rows: FWONA, INSM, NXTT, TSCO, CHTR, CPRT, EXC, GEHC ... | 11 rows: TSCO, TRACTOR SUPPLY CO /DE/, Consumer; FWONA, Liberty Media Corp, Communication Services; NXTT, Next Technology Holding Inc., Technology; INSM, INSMED Inc, Health Care ... | **MATCH** |
| Q14 | Which predicted removals have the highest ETF trading impact? | 7 rows: CPRT, TEAM, EXC, MCHP, CHTR, IDXX, GEHC | 7 rows: CPRT, COPART INC, REMOVE; TEAM, Atlassian Corp, REMOVE; EXC, EXELON CORP, REMOVE; MCHP, MICROCHIP TECHNOLOGY INC, REMOVE ... | **MATCH** |
