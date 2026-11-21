"""Generate SYNTHETIC market data and index history for the NextDAQ-100, seeded from the public files
landed by land_public.py, and write them to the UC landing volume as the source systems would export them.

Writes (under --root):
  prices/<yyyy-mm>/mkt_prices_<period>.csv      market data vendor: monthly files, then daily in Nov 2026
  price_manifests/mkt_prices_<period>.json      control totals, written AFTER each data file
  holdback/...                                  last 2 trading days, kept back to land live in the demo
  index_history/nextdaq100_changes.csv          index administrator's change log (uses `symbol`)
  etf_aum/etf_aum_<yyyy-mm>.json                assets of products tracking the index, monthly
  answer_key.json                               planted findings and their counts

Deterministic (SEED) and idempotent: if answer_key.json exists, nothing is rewritten unless --overwrite.
Prices are synthetic: a factor random walk anchored so each company's market cap at its latest SEC
public-float date equals public float / FLOAT_SHARE (an assumption, not real market data).
"""
import argparse
import glob
import hashlib
import json
import os
import shutil
import sys

import numpy as np
import pandas as pd
from pandas.tseries.holiday import (AbstractHolidayCalendar, GoodFriday, Holiday, USLaborDay,
                                    USMartinLutherKingJr, USMemorialDay, USPresidentsDay, USThanksgivingDay,
                                    nearest_workday)
from pandas.tseries.offsets import CustomBusinessDay



def _load_engine():
    """Import the shared engine (src/app/engine.py) from --code-root (jobs run a /tmp copy of this file,
    so the path cannot be derived from the script location)."""
    import types
    root = sys.argv[sys.argv.index("--code-root") + 1] if "--code-root" in sys.argv else \
        os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "..")
    path = os.path.join(root.replace("dbfs:", ""), "app", "engine.py")
    with open(path) as f:
        src = f.read()
    mod = types.ModuleType("engine")
    mod.__file__ = path
    sys.modules["engine"] = mod
    exec(compile(src, path, "exec"), mod.__dict__)
    return mod


_engine = _load_engine()
Rules, cap_weights, is_financial = _engine.Rules, _engine.cap_weights, _engine.is_financial
needs_capping, rank_universe, select_members = _engine.needs_capping, _engine.rank_universe, _engine.select_members

SEED = 2026
START, END = "2021-09-01", "2026-11-20"
HOLDBACK_DAYS = 2
DAILY_FROM = "2026-11-01"
FLOAT_SHARE = 0.85            # assumption: public float is ~85% of market cap
RECON_YEARS = [2021, 2022, 2023, 2024, 2025]   # 2021 = initial composition; 2025 = held out for ML eval
DISCRETION_YEARS = {2024: 2, 2025: 2}           # planted: rule says add, committee defers
RALLY = ("2025-05-01", 42, 0.011, 60, -0.003)    # planted megacap rally -> special rebalance
RALLY_TOP_N = 7
N_DUP, N_BAD_PRICE, N_NEG_VOL, MANIFEST_SHORT = 37, 12, 5, 3
DUP_PERIOD, SHORT_PERIOD = "2025-03", "20261113"
TOTAL_AUM_LATEST = 400e9
SEC_FIXES: dict = {}
DIAG: dict = {}


class MarketCalendar(AbstractHolidayCalendar):
    rules = [Holiday("NewYearsDay", month=1, day=1, observance=nearest_workday), USMartinLutherKingJr,
             USPresidentsDay, GoodFriday, USMemorialDay,
             Holiday("Juneteenth", month=6, day=19, start_date="2022-01-01", observance=nearest_workday),
             Holiday("July4th", month=7, day=4, observance=nearest_workday), USLaborDay, USThanksgivingDay,
             Holiday("Christmas", month=12, day=25, observance=nearest_workday)]


def h(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


def monday_after_third_friday(year: int, month: int) -> pd.Timestamp:
    fridays = pd.date_range(f"{year}-{month:02d}-01", periods=31, freq="D")
    fridays = fridays[(fridays.month == month) & (fridays.weekday == 4)]
    return fridays[2] + pd.Timedelta(days=3)


# ----------------------------------------------------------------------------- public inputs
def load_universe(root: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    pub = os.path.join(root, "public")
    sm = pd.read_csv(os.path.join(pub, "security_master", "exchange_listed.txt"), sep="|", dtype=str)
    sm = sm[~sm["Symbol"].fillna("").str.startswith("File Creation")]
    sm = sm[(sm["Test Issue"] == "N") & (sm["ETF"] == "N")]
    nm = sm["Security Name"].fillna("")
    good = nm.str.contains("Common Stock|Ordinary Share|American Depositary Shares|Class A|Class B|Class C")
    bad = nm.str.contains("Warrant|Right|Unit|Preferred|Notes|Debenture")
    sm = sm[good & ~bad]

    t = json.load(open(os.path.join(pub, "sec_companies", "company_tickers_exchange.json")))
    sec = pd.DataFrame(t["data"], columns=t["fields"])
    sec = sec[(sec["exchange"] == "Nasdaq") & sec["ticker"].isin(sm["Symbol"].str.strip())]
    sec = sec.drop_duplicates("cik", keep="first")          # one line per issuer (primary share class)
    sic = pd.read_json(os.path.join(pub, "sec_sic", "sec_submissions_extract.jsonl"), lines=True, dtype={"sic": str})
    u = sec.merge(sic[["cik", "sic"]], on="cik", how="inner")

    def frames(concept):
        rows = []
        for p in sorted(glob.glob(os.path.join(pub, "sec_facts", concept, "*.json"))):
            rows += [(r["cik"], r["end"], float(r["val"])) for r in json.load(open(p))["data"]]
        f = pd.DataFrame(rows, columns=["cik", "end", "val"])
        f["end"] = pd.to_datetime(f["end"])
        return f.sort_values(["cik", "end"]).drop_duplicates(["cik", "end"], keep="last")

    shares, flt = frames("EntityCommonStockSharesOutstanding"), frames("EntityPublicFloat")
    wavg = frames("WeightedAverageNumberOfSharesOutstandingBasic")
    shares = pd.concat([shares, wavg[~wavg["cik"].isin(shares["cik"])]])   # fallback for dual-class filers
    SEC_FIXES["shares_from_weighted_average_fallback"] = int(wavg.loc[~wavg["cik"].isin(frames("EntityCommonStockSharesOutstanding")["cik"]), "cik"].nunique())
    anchor = flt[flt["val"] > 0].groupby("cik").tail(1).rename(columns={"end": "anchor_date", "val": "public_float"})
    u = u.merge(anchor, on="cik").copy()
    u = u[u["cik"].isin(shares.loc[shares["val"] > 0, "cik"])]
    # REAL public-data issue (not planted): some filers tag public float ~1000x too large (XBRL scale error).
    # Check implied float per share; rescale when /1000 is plausible, drop when still implausible.
    med_sh = shares[shares["val"] > 0].groupby("cik")["val"].median()
    px = u["public_float"] / u["cik"].map(med_sh)
    fix = (px > 10000) & ((px / 1000).between(0.5, 10000))
    u.loc[fix, "public_float"] = u.loc[fix, "public_float"] / 1000
    px = u["public_float"] / u["cik"].map(med_sh)
    bad = ~px.between(0.5, 10000)
    SEC_FIXES.update({"float_rescaled_div1000": sorted(u.loc[fix, "ticker"]), "dropped_implausible_float": sorted(u.loc[bad, "ticker"])})
    u = u[~bad].copy()
    u["market_cap_anchor"] = u["public_float"] / FLOAT_SHARE
    u["is_financial"] = u["sic"].map(is_financial)
    u = u.sort_values("market_cap_anchor", ascending=False).reset_index(drop=True)
    return u, shares[shares["cik"].isin(u["cik"]) & (shares["val"] > 0)]


# ----------------------------------------------------------------------------- synthetic market
def simulate(u: pd.DataFrame, shares: pd.DataFrame, days: pd.DatetimeIndex, rng) -> dict:
    D, N = len(days), len(u)
    shares_m = np.empty((D, N))
    for j, cik in enumerate(u["cik"]):
        s = shares[shares["cik"] == cik].set_index("end")["val"]
        shares_m[:, j] = s.reindex(s.index.union(days)).sort_index().ffill().bfill().reindex(days).values

    size = np.log10(u["market_cap_anchor"].values)
    idio = np.clip(0.024 - 0.004 * (size - 9), 0.009, 0.026)      # ~14%/yr megacaps .. ~40%/yr small caps
    beta = rng.uniform(0.8, 1.3, N)
    sector = (pd.to_numeric(u["sic"], errors="coerce").fillna(0) // 1000).astype(int).values
    sec_f = rng.normal(0, 0.004, (D, 10))
    mkt = rng.normal(0.00035, 0.010, D)
    eps = rng.standard_t(5, (D, N)) * idio / np.sqrt(5 / 3)
    # company-specific moves mean-revert (half-life ~1.4 years) so ranks stay plausible over five years
    phi = 1 - 1 / 500
    x = np.zeros((D, N))
    for t in range(1, D):
        x[t] = phi * x[t - 1] + eps[t]
    trend = rng.normal(0, 0.12, N) / 252                             # persistent growth / decline per company
    logp = np.cumsum(mkt[:, None] * beta + sec_f[:, sector] + trend[None, :], axis=0) + x
    R = np.vstack([np.zeros((1, N)), np.diff(logp, axis=0)])
    ai = np.clip(days.searchsorted(u["anchor_date"].values), 0, D - 1)
    p_anchor = u["market_cap_anchor"].values / shares_m[ai, np.arange(N)]
    logp += (np.log(p_anchor) - logp[ai, np.arange(N)])[None, :]

    turnover = np.exp(rng.normal(np.log(0.006), 0.6, N))
    dvol = u["market_cap_anchor"].values * turnover * np.exp(rng.normal(0, 0.4, (D, N))) * (1 + 15 * np.abs(R))
    return {"logp": logp, "R": R, "idio": idio, "shares": shares_m, "dvol": dvol}


def apply_rally(sim: dict, days: pd.DatetimeIndex, cols: list) -> None:
    start, up_n, up, down_n, down = RALLY
    i0 = days.searchsorted(pd.Timestamp(start))
    ramp = np.zeros(len(days))
    ramp[i0:i0 + up_n] = up
    ramp[i0 + up_n:i0 + up_n + down_n] = down
    sim["logp"][:, cols] += np.cumsum(ramp)[:, None]


def month_end_snapshots(u, sim, days) -> dict:
    close = np.exp(sim["logp"])
    me = pd.Series(days).groupby([days.year, days.month]).max().values
    adv = pd.DataFrame(sim["dvol"]).rolling(63, min_periods=20).mean().values
    snaps = {}
    for d in pd.DatetimeIndex(me):
        i = days.get_loc(d)
        snaps[d] = pd.DataFrame({"ticker": u["ticker"].values, "market_cap": close[i] * sim["shares"][i],
                                 "adv_usd": adv[i], "is_financial": u["is_financial"].values,
                                 "sector": "", "close": close[i]})
    return snaps


# ----------------------------------------------------------------------------- index history
def run_history(snaps: dict, rules: Rules) -> tuple[list, dict]:
    events, info = [], {"discretion": {}, "special_rebalances": []}
    members, units = set(), None
    for d, s in sorted(snaps.items()):
        if d.month == 11 and d.year in RECON_YEARS:
            ranked = rank_universe(s, rules)
            eff = monday_after_third_friday(d.year, 12)
            ann = eff - pd.Timedelta(days=10)
            skip = set()
            if members and d.year in DISCRETION_YEARS:
                rule_adds = sorted(select_members(ranked, members, rules) - members, key=lambda t: h(f"{d.year}{t}"))
                skip = set(rule_adds[: DISCRETION_YEARS[d.year]])
                info["discretion"][str(d.year)] = sorted(skip)
            new = select_members(ranked, members, rules, skip_adds=skip)
            c = s[s["ticker"].isin(new)].set_index("ticker")
            w = cap_weights(c["market_cap"], rules)
            etype = "INITIAL_COMPOSITION" if not members else "ANNUAL_RECONSTITUTION"
            acts = [(t, "ADD") for t in sorted(new - members)] + [(t, "REMOVE") for t in sorted(members - new)]
            for t, act in acts:
                events.append({"effective_date": eff.date(), "announcement_date": ann.date(), "symbol": t,
                               "event_type": etype, "action": act,
                               "weight_after": round(float(w.get(t, 0.0)), 6), "reference_date": d.date()})
            members, units = new, (w / c["close"])
        elif members:
            c = s[s["ticker"].isin(members)].set_index("ticker")
            wt = units * c["close"]
            wt = wt / wt.sum()
            chk = needs_capping(wt, rules)
            DIAG.setdefault("aggregate_weight_by_month", {})[str(d.date())] = round(chk["aggregate_weight"], 4)
            if chk["single_breach"] or chk["aggregate_breach"]:
                nm = d.month % 12 + 1
                eff = monday_after_third_friday(d.year + (d.month == 12), nm)
                w = cap_weights(c["market_cap"], rules)
                info["special_rebalances"].append({"reference_date": str(d.date()), "effective_date": str(eff.date()),
                                                   **{k: round(v, 4) if isinstance(v, float) else v for k, v in chk.items()}})
                for t in w.index:
                    if abs(w[t] - wt[t]) > 0.001:
                        events.append({"effective_date": eff.date(), "announcement_date": (eff - pd.Timedelta(days=10)).date(),
                                       "symbol": t, "event_type": "SPECIAL_REBALANCE", "action": "REWEIGHT",
                                       "weight_after": round(float(w[t]), 6), "reference_date": d.date()})
                units = w / c["close"]
    return events, info


# ----------------------------------------------------------------------------- writers
def write_prices(root, u, sim, days, rng, key):
    close = np.exp(sim["logp"])
    idio = sim["idio"]
    prev = np.vstack([close[:1], close[:-1]])
    opn = prev * np.exp(rng.normal(0, 1, close.shape) * idio / 3)
    hi = np.maximum(opn, close) * (1 + np.abs(rng.normal(0, 1, close.shape)) * idio / 2)
    lo = np.minimum(opn, close) * (1 - np.abs(rng.normal(0, 1, close.shape)) * idio / 2)
    vol = (sim["dvol"] / close).astype(np.int64)
    D, N = close.shape
    df = pd.DataFrame({"TradeDate": np.repeat(days.strftime("%Y-%m-%d"), N), "Ticker": np.tile(u["ticker"].values, D),
                       "Open": opn.ravel().round(4), "High": hi.ravel().round(4), "Low": lo.ravel().round(4),
                       "Close": close.ravel().round(4), "Volume": vol.ravel(), "Currency": "USD"})
    df["Close"] = df["Close"].astype(object)
    df["period"] = np.where(df["TradeDate"] >= DAILY_FROM, df["TradeDate"].str.replace("-", ""), df["TradeDate"].str[:7])

    # planted bad rows (disjoint, hash-selected so they are stable)
    idx = sorted(df.index[df["TradeDate"] < DAILY_FROM], key=lambda i: h(f"bad{i}"))
    bad_price, neg_vol = idx[:N_BAD_PRICE], idx[N_BAD_PRICE:N_BAD_PRICE + N_NEG_VOL]
    df.loc[bad_price[: N_BAD_PRICE // 2], "Close"] = ""
    df.loc[bad_price[N_BAD_PRICE // 2:], "Close"] = [0.0, -1.0, 0.0, -0.01, 0.0, -5.0][: N_BAD_PRICE - N_BAD_PRICE // 2]
    df.loc[neg_vol, "Volume"] = -df.loc[neg_vol, "Volume"]
    key["bad_price_rows"] = {"count": len(bad_price), "null_close": N_BAD_PRICE // 2, "zero_or_negative_close": N_BAD_PRICE - N_BAD_PRICE // 2}
    key["negative_volume_rows"] = {"count": len(neg_vol)}

    holdback = sorted(df.loc[df["TradeDate"] >= DAILY_FROM, "period"].unique())[-HOLDBACK_DAYS:]
    files = 0
    for period, g in df.groupby("period", sort=True):
        g = g.drop(columns="period")
        sent = len(g)
        if period == DUP_PERIOD:
            dups = g.loc[sorted(set(g.index) - set(bad_price) - set(neg_vol), key=lambda i: h(f"dup{i}"))[:N_DUP]]
            g = pd.concat([g, dups])
            sent = len(g)
        if period == SHORT_PERIOD:
            g = g.iloc[:-MANIFEST_SHORT]           # file truncated in transit; manifest still says `sent`
        base = os.path.join(root, "holdback") if period in holdback else root
        month = period[:7] if "-" in period else f"{period[:4]}-{period[4:6]}"
        fname = f"mkt_prices_{period.replace('-', '')}.csv"
        fpath = os.path.join(base, "prices", month, fname)
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        g.to_csv(fpath, index=False)
        vol_total = int(pd.to_numeric(g["Volume"]).sum()) if period != SHORT_PERIOD else None
        man = {"file_name": fname, "period": period, "record_count": sent,
               "volume_total": vol_total if vol_total is not None else int(pd.to_numeric(df.loc[df["period"] == period, "Volume"]).sum()),
               "source_system": "MKTDATA_VENDOR"}
        mpath = os.path.join(base, "price_manifests", fname.replace(".csv", ".json"))
        os.makedirs(os.path.dirname(mpath), exist_ok=True)
        with open(mpath, "w") as f:
            json.dump(man, f)
        files += 1
    key["duplicate_rows"] = {"count": N_DUP, "file": f"mkt_prices_{DUP_PERIOD.replace('-', '')}.csv"}
    key["manifest_break"] = {"file": f"mkt_prices_{SHORT_PERIOD}.csv", "rows_missing": MANIFEST_SHORT}
    key["holdback_periods"] = holdback
    return files, len(df)


def write_index_history(root, events, key):
    ev = pd.DataFrame(events).sort_values(["effective_date", "event_type", "action", "symbol"]).reset_index(drop=True)
    messy = sorted(ev.index[ev["event_type"] == "ANNUAL_RECONSTITUTION"], key=lambda i: h(f"sym{i}"))[:3]
    ev.loc[messy[0], "symbol"] = ev.loc[messy[0], "symbol"].lower()
    ev.loc[messy[1:], "symbol"] = ev.loc[messy[1:], "symbol"] + "  "
    p = os.path.join(root, "index_history", "nextdaq100_changes.csv")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    ev.to_csv(p, index=False)
    key["messy_index_symbols"] = {"count": 3, "lowercase": 1, "trailing_spaces": 2}
    key["index_events"] = ev.groupby(["event_type", "action"]).size().rename("n").reset_index().to_dict("records")
    return len(ev)


def write_etf_aum(root, snaps, events):
    ev = pd.DataFrame(events)
    months = sorted(d for d in snaps if d >= pd.Timestamp("2021-12-31"))
    members, level, lv = set(), 1.0, []
    prev_close = None
    for d in months:
        s = snaps[d].set_index("ticker")
        chg = ev[(pd.to_datetime(ev["effective_date"]) <= d) & ev["action"].isin(["ADD", "REMOVE"])]
        members = set(chg.groupby("symbol")["action"].last().loc[lambda x: x == "ADD"].index)
        if prev_close is not None:
            m = sorted(members & set(prev_close.index))
            wts = s.loc[m, "market_cap"] / s.loc[m, "market_cap"].sum()
            level *= float((wts * s.loc[m, "close"] / prev_close.loc[m]).sum())
        prev_close = s["close"]
        lv.append((d, level))
    flows = np.cumprod(np.full(len(lv), 1.006))
    raw = np.array([l for _, l in lv]) * flows
    aum = raw / raw[-1] * TOTAL_AUM_LATEST
    products = [("NXQ", "NextDAQ-100 Tracker Trust", 0.62), ("NXQM", "NextDAQ-100 Core ETF", 0.18),
                ("NXQL", "NextDAQ-100 2x Leveraged ETF", 0.08), ("NXQC", "NextDAQ-100 Covered Call ETF", 0.07),
                ("NXQE", "NextDAQ-100 ESG Screened ETF", 0.05)]
    for (d, _), a in zip(lv, aum):
        doc = {"as_of_date": str(d.date()), "products": [{"product_code": c, "product_name": n, "aum_usd": round(a * sh, 2)}
                                                         for c, n, sh in products]}
        p = os.path.join(root, "etf_aum", f"etf_aum_{d.strftime('%Y-%m')}.json")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            json.dump(doc, f)
    return len(lv)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--code-root", default=None)
    a = ap.parse_args()
    kpath = os.path.join(a.root, "answer_key.json")
    if os.path.exists(kpath) and not a.overwrite:
        print(json.dumps({"status": "SKIPPED_EXISTS", **json.load(open(kpath))}))
        return
    for sub in ("prices", "price_manifests", "holdback", "index_history", "etf_aum"):
        shutil.rmtree(os.path.join(a.root, sub), ignore_errors=True)

    rng = np.random.default_rng(SEED)
    rules = Rules()
    u, shares = load_universe(a.root)
    days = pd.bdate_range(START, END, freq=CustomBusinessDay(calendar=MarketCalendar()))
    sim = simulate(u, shares, days, rng)

    # pass 1: find the capped "big" group after the Dec 2024 reconstitution, then plant the rally on it
    snaps = month_end_snapshots(u, sim, days)
    ev1, _ = run_history({d: s for d, s in snaps.items() if d <= pd.Timestamp("2024-12-31")}, rules)
    m24 = pd.DataFrame(ev1).groupby("symbol")["action"].last().loc[lambda x: x == "ADD"].index
    s24 = snaps[max(d for d in snaps if d.year == 2024 and d.month == 11)].set_index("ticker").loc[list(m24)]
    w24 = cap_weights(s24["market_cap"], rules)
    big = list(w24.sort_values(ascending=False).head(RALLY_TOP_N).index)   # the seven largest names rally together
    DIAG["dec2024_top10_capped_weights"] = {t: round(float(v), 4) for t, v in w24.sort_values(ascending=False).head(10).items()}
    DIAG["dec2024_top10_uncapped_weights"] = {t: round(float(v), 4) for t, v in
                                             (s24["market_cap"] / s24["market_cap"].sum()).sort_values(ascending=False).head(10).items()}
    apply_rally(sim, days, [int(np.where(u["ticker"].values == t)[0][0]) for t in big])

    # pass 2: final history
    snaps = month_end_snapshots(u, sim, days)
    events, info = run_history(snaps, rules)

    key = {"seed": SEED, "universe_size": len(u), "trading_days": len(days),
           "first_date": str(days[0].date()), "last_date": str(days[-1].date()),
           "missing_sic_total": int((u["sic"].fillna("") == "").sum()),
           "real_sec_float_issues": SEC_FIXES,
           "rally_names": big, "diagnostics": DIAG, "special_rebalances": info["special_rebalances"],
           "committee_discretion_skipped_adds": info["discretion"],
           "reconstitutions": [str(monday_after_third_friday(y, 12).date()) for y in RECON_YEARS],
           "held_out_reconstitution": str(monday_after_third_friday(RECON_YEARS[-1], 12).date())}
    n_files, n_rows = write_prices(a.root, u, sim, days, rng, key)
    key["price_files"], key["price_rows_generated"] = n_files, n_rows
    key["index_history_rows"] = write_index_history(a.root, events, key)
    key["etf_aum_months"] = write_etf_aum(a.root, snaps, events)
    with open(kpath, "w") as f:
        json.dump(key, f, indent=1, default=str)
    print(json.dumps({"status": "GENERATED", **key}, default=str))


if __name__ == "__main__":
    main()
