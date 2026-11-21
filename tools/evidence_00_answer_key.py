"""Write evidence/00_answer_key.md from the live workspace: the generator's answer key (landing/answer_key.json)
plus planted counts recomputed independently from the landed files with SQL, and a file inventory.
Runs locally with only the Databricks CLI (tools/sql.sh). Usage: python3 tools/evidence_00_answer_key.py"""
import datetime as dt
import json
import os
import subprocess
import tempfile

PROFILE = os.environ.get("DATABRICKS_PROFILE", "fe-bar-2026")
L = "/Volumes/fe_bar_2026_kelemen_catalog/nextdaq_index/landing"
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def sql(q):
    return subprocess.run([os.path.join(ROOT, "tools", "sql.sh"), q], capture_output=True, text=True, check=True).stdout


def cli(*args):
    return subprocess.run(["databricks", *args, "-p", PROFILE], capture_output=True, text=True, check=True).stdout


def main():
    with tempfile.TemporaryDirectory() as t:
        cli("fs", "cp", f"dbfs:{L}/answer_key.json", f"{t}/k.json", "--overwrite")
        k = json.load(open(f"{t}/k.json"))
        cli("fs", "cp", f"dbfs:{L}/prices/2026-11/mkt_prices_20261102.csv", f"{t}/p.csv", "--overwrite")
        price_head = "".join(open(f"{t}/p.csv").readlines()[:4])
        cli("fs", "cp", f"dbfs:{L}/price_manifests/mkt_prices_20261102.json", f"{t}/m.json", "--overwrite")
        manifest = open(f"{t}/m.json").read()
        cli("fs", "cp", f"dbfs:{L}/index_history/nextdaq100_changes.csv", f"{t}/i.csv", "--overwrite")
        idx_lines = open(f"{t}/i.csv").readlines()
        idx_head = idx_lines[0] + "".join(l for l in idx_lines if "SPECIAL" in l)[:400]

    prices = sql(f"""WITH p AS (SELECT * FROM read_files('{L}/prices/', format=>'csv', header=>true, inferSchema=>false))
SELECT (SELECT count(*) FROM p) AS landed_price_rows,
 (SELECT count(*) - count(DISTINCT TradeDate, Ticker) FROM p) AS duplicate_rows,
 (SELECT count(*) FROM p WHERE Close IS NULL OR trim(Close)='') AS null_close,
 (SELECT count(*) FROM p WHERE CAST(Close AS DOUBLE) <= 0) AS non_positive_close,
 (SELECT count(*) FROM p WHERE CAST(Volume AS BIGINT) < 0) AS negative_volume,
 (SELECT count(DISTINCT Ticker) FROM p) AS tickers, (SELECT min(TradeDate) FROM p) AS first_day,
 (SELECT max(TradeDate) FROM p) AS last_day""")
    manif = sql(f"""WITH m AS (SELECT * FROM read_files('{L}/price_manifests/', format=>'json')),
 f AS (SELECT regexp_extract(_metadata.file_path,'([^/]+)$',1) AS file_name, count(*) AS n
       FROM read_files('{L}/prices/', format=>'csv', header=>true) GROUP BY 1)
SELECT count(*) AS manifests, count_if(m.record_count = f.n) AS counts_match, count_if(m.record_count <> f.n) AS counts_break,
 max(CASE WHEN m.record_count <> f.n THEN m.file_name || ': control ' || m.record_count || ' vs landed ' || f.n END) AS break_detail
FROM m JOIN f USING (file_name)""")
    index = sql(f"""SELECT event_type, action, count(*) AS rows, count_if(symbol <> upper(trim(symbol))) AS messy_symbols,
 min(effective_date) AS first_effective, max(effective_date) AS last_effective
FROM read_files('{L}/index_history/', format=>'csv', header=>true) GROUP BY ALL ORDER BY 1, 2""")
    sic = sql(f"SELECT count(*) AS sec_sic_records, count_if(sic IS NULL OR sic='') AS blank_sic FROM read_files('{L}/public/sec_sic/', format=>'json')")

    inv = []
    for d in ["public/security_master", "public/sec_companies", "public/sec_sic", "public/sec_facts/EntityCommonStockSharesOutstanding",
              "public/sec_facts/EntityPublicFloat", "public/sec_facts/WeightedAverageNumberOfSharesOutstandingBasic",
              "prices", "price_manifests", "index_history", "etf_aum", "holdback/prices/2026-11", "holdback/price_manifests"]:
        n = len([x for x in cli("fs", "ls", f"dbfs:{L}/{d}").splitlines() if x.strip()])
        inv.append(f"| `landing/{d}/` | {n} |")

    sr = k["special_rebalances"]
    planted = [
        ("Duplicate ticker-day rows (re-sent rows in one file)", k["duplicate_rows"]["count"], k["duplicate_rows"]["file"], "silver_prices_quarantine reason DUPLICATE_TICKER_DAY"),
        ("Null close price", k["bad_price_rows"]["null_close"], "spread across monthly files", "reason MISSING_CLOSE"),
        ("Zero or negative close price", k["bad_price_rows"]["zero_or_negative_close"], "spread across monthly files", "reason NON_POSITIVE_CLOSE"),
        ("Negative volume", k["negative_volume_rows"]["count"], "spread across monthly files", "reason NEGATIVE_VOLUME"),
        ("Manifest break: file truncated in transit", k["manifest_break"]["rows_missing"], k["manifest_break"]["file"], "recon_market_data status BREAK"),
        ("Index-history symbols not conformed (lower case / trailing spaces)", k["messy_index_symbols"]["count"], "index_history/nextdaq100_changes.csv", "silver_index_events: upper(trim(symbol))"),
        ("SEC filers with SIC blanked (planted, hash-selected)", 10, "public/sec_sic/", "silver_securities expectation has_sector (warn)"),
        ("Megacap rally -> special rebalance", len(sr), f"reference {sr[0]['reference_date']}, effective {sr[0]['effective_date']}" if sr else "-", "gold_reconstitution_history event_type SPECIAL_REBALANCE"),
        ("Committee discretion: rule says add, not added", sum(len(v) for v in k["committee_discretion_skipped_adds"].values()), json.dumps(k["committee_discretion_skipped_adds"]), "limits any rule-only forecast"),
    ]
    rows = "\n".join(f"| {a} | {b} | {c} | {d} |" for a, b, c, d in planted)
    fx = k["real_sec_float_issues"]
    out = f"""# 00 — Answer key and landed data inventory

Generated {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC by tools/evidence_00_answer_key.py from the live workspace.
This file proves the raw data exists in the UC volume, what was planted in it, and that the planted counts can be recomputed from the files alone (independently of the generator). Seed {k['seed']}; reruns give the same counts.

## Universe and history

- {k['universe_size']} issuers (public symbol directory + SEC filers with public float >= $300M), {k['trading_days']} trading days, {k['first_date']} to {k['last_date']}; last {len(k['holdback_periods'])} days ({', '.join(k['holdback_periods'])}) held back in `landing/holdback/` to land live in the demo.
- Reconstitutions (effective): {', '.join(k['reconstitutions'])}. Held out for ML evaluation: **{k['held_out_reconstitution']}**.
- Planted rally names (seven largest after the 2024 reconstitution): {', '.join(k['rally_names'])}.

## Planted findings

| Finding | Count | Where | How the build catches it |
|---|---|---|---|
{rows}

## Real issues found in the public SEC data (not planted)

- Public float ~1000x too large (XBRL scale error), rescaled /1000: {', '.join(fx['float_rescaled_div1000'])}.
- Still implausible after the check, dropped from the universe: {', '.join(fx['dropped_implausible_float'])}.
- Dual-class filers have no cover-page share count in SEC frames; weighted-average basic shares used instead (silver_shares.shares_source = WEIGHTED_AVERAGE_FALLBACK).

## Recomputed from the landed files (SQL on the volume)

Prices:

{prices}
Manifests vs files:

{manif}
Index history:

{index}
SEC SIC extract (10 planted blanks + filers SEC itself leaves blank):

{sic}
## File inventory

| Folder | Entries |
|---|---|
{chr(10).join(inv)}

## Samples (verbatim)

`prices/2026-11/mkt_prices_20261102.csv` (first rows):
```
{price_head}```
`price_manifests/mkt_prices_20261102.json`:
```
{manifest}
```
`index_history/nextdaq100_changes.csv` (header + special-rebalance rows):
```
{idx_head}
```
"""
    with open(os.path.join(ROOT, "evidence", "00_answer_key.md"), "w") as f:
        f.write(out)
    print(f"wrote evidence/00_answer_key.md ({len(out)} chars)")


if __name__ == "__main__":
    main()
