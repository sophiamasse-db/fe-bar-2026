"""NextDAQ-100 rebalance engine: one implementation of the methodology, shared by the
synthetic-history generator (src/data/generate.py), the ML labels and the app's Scenario Lab.

Simplified NextDAQ-100 methodology (fictional, modelled on public large-cap index rules):
  * Eligible: exchange-listed common stock / ordinary shares / ADS, not a financial (SIC 6000-6799),
    3-month average daily dollar volume >= liquidity minimum, sector not excluded.
  * Ranked by market cap. Non-members ranked in the top 75% of the index size are added; members ranked
    within the buffer stay; the index is then trimmed or filled to its size by rank.
  * Weights: market-cap weights, then two-stage capping:
      stage 1 - no single weight above the single-stock target;
      stage 2 - if names above the aggregate threshold together exceed the aggregate cap, they are scaled
                to the aggregate target and every other name is capped just below the threshold.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

import numpy as np
import pandas as pd


@dataclass
class Rules:
    index_size: int = 100
    buffer_rank: int = 125
    liquidity_min_usd: float = 5_000_000.0
    single_cap: float = 0.24          # breach trigger for one name
    single_target: float = 0.20       # weight a breaching name is cut to
    agg_threshold: float = 0.045      # names above this weight count toward the aggregate
    agg_cap: float = 0.48             # breach trigger for the aggregate
    agg_target: float = 0.40          # aggregate weight after stage 2
    exclude_sectors: tuple = field(default_factory=tuple)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["exclude_sectors"] = list(self.exclude_sectors)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Rules":
        d = dict(d)
        d["exclude_sectors"] = tuple(d.get("exclude_sectors") or ())
        return cls(**d)


def is_financial(sic) -> bool:
    try:
        s = int(sic)
    except (TypeError, ValueError):
        return False
    return 6000 <= s <= 6799


def eligible_mask(u: pd.DataFrame, rules: Rules) -> pd.Series:
    """u needs columns: market_cap, adv_usd, is_financial, sector."""
    m = (u["market_cap"] > 0) & (~u["is_financial"].astype(bool)) & (u["adv_usd"] >= rules.liquidity_min_usd)
    if rules.exclude_sectors:
        m &= ~u["sector"].isin(rules.exclude_sectors)
    return m


def rank_universe(u: pd.DataFrame, rules: Rules) -> pd.DataFrame:
    """Return u with `eligible` and `rank` (1 = largest eligible market cap; NaN if ineligible)."""
    out = u.copy()
    out["eligible"] = eligible_mask(out, rules)
    out["rank"] = np.nan
    el = out[out["eligible"]].sort_values(["market_cap", "ticker"], ascending=[False, True])
    out.loc[el.index, "rank"] = np.arange(1, len(el) + 1)
    return out


def select_members(u: pd.DataFrame, current: set, rules: Rules, skip_adds: set = frozenset()) -> set:
    """Apply the reconstitution rule. u must be ranked (rank_universe). Returns the new member set."""
    r = u.dropna(subset=["rank"]).set_index("ticker")["rank"].sort_values()
    must_add_cut = int(round(0.75 * rules.index_size))
    keep = {t for t in current if t in r.index and r[t] <= rules.buffer_rank}
    adds = {t for t, k in r.items() if t not in current and k <= must_add_cut and t not in skip_adds}
    chosen = keep | adds
    if len(chosen) > rules.index_size:   # trim lowest-ranked kept members first
        chosen = set(sorted(chosen, key=lambda t: r[t])[: rules.index_size])
    for t in r.index:                    # fill by rank
        if len(chosen) >= rules.index_size:
            break
        if t not in chosen and t not in skip_adds:
            chosen.add(t)
    return chosen


def _cap_iter(w: pd.Series, cap: float, mask: pd.Series | None = None, iters: int = 50) -> pd.Series:
    """Cap weights in `mask` (default all) at `cap`, redistributing excess pro rata to uncapped names."""
    w = w.copy()
    mask = pd.Series(True, index=w.index) if mask is None else mask
    for _ in range(iters):
        over = mask & (w > cap + 1e-12)
        if not over.any():
            break
        excess = (w[over] - cap).sum()
        w[over] = cap
        free = mask & ~over & (w < cap)
        if not free.any():
            break
        w[free] += excess * w[free] / w[free].sum()
    return w


def needs_capping(w: pd.Series, rules: Rules) -> dict:
    agg = w[w > rules.agg_threshold].sum()
    return {"single_breach": bool(w.max() > rules.single_cap), "aggregate_breach": bool(agg > rules.agg_cap),
            "max_weight": float(w.max()), "aggregate_weight": float(agg)}


def cap_weights(market_cap: pd.Series, rules: Rules) -> pd.Series:
    """Market-cap weights with the two-stage cap. Index = ticker."""
    w = market_cap / market_cap.sum()
    w = _cap_iter(w, rules.single_target)                       # stage 1
    big = w > rules.agg_threshold
    if w[big].sum() > rules.agg_cap:                            # stage 2
        wb = w[big] * rules.agg_target / w[big].sum()
        ws = w[~big] * (1 - rules.agg_target) / w[~big].sum()
        ws = _cap_iter(ws, rules.agg_threshold - 0.001)
        w = pd.concat([wb, ws])
    return (w / w.sum()).reindex(market_cap.index)


def build_index(u: pd.DataFrame, current: set, rules: Rules) -> tuple[pd.DataFrame, set]:
    """Rank, select and weight. Returns (constituents df [ticker, weight, market_cap, rank], members)."""
    ranked = rank_universe(u, rules)
    members = select_members(ranked, current, rules)
    c = ranked[ranked["ticker"].isin(members)].set_index("ticker")
    c["weight"] = cap_weights(c["market_cap"], rules)
    return c.reset_index().sort_values("weight", ascending=False), members


def scenario_kpis(before: pd.DataFrame, after: pd.DataFrame, adv_usd: pd.Series, aum_usd: float,
                  participation: float = 0.20) -> tuple[dict, pd.DataFrame]:
    """Compare two constituent frames (ticker, weight). Returns (kpis, per-name trades)."""
    wb = before.set_index("ticker")["weight"]
    wa = after.set_index("ticker")["weight"]
    allt = wb.index.union(wa.index)
    wb, wa = wb.reindex(allt, fill_value=0.0), wa.reindex(allt, fill_value=0.0)
    dw = wa - wb
    trades = pd.DataFrame({"weight_before": wb, "weight_after": wa, "weight_change": dw})
    trades["trade_usd"] = dw * aum_usd
    adv = adv_usd.reindex(allt).fillna(0)
    trades["days_to_trade"] = np.where(adv > 0, trades["trade_usd"].abs() / (adv * participation), np.nan)
    trades["action"] = np.select([(wb == 0) & (wa > 0), (wb > 0) & (wa == 0)], ["ADD", "REMOVE"], "REWEIGHT")
    top10 = wa.sort_values(ascending=False).head(10).sum()
    k = {
        "constituents": int((wa > 0).sum()),
        "additions": int((trades["action"] == "ADD").sum()),
        "removals": int((trades["action"] == "REMOVE").sum()),
        "turnover_pct": float(0.5 * dw.abs().sum() * 100),
        "top10_weight_pct": float(top10 * 100),
        "max_weight_pct": float(wa.max() * 100),
        "hhi": float((wa ** 2).sum() * 10_000),
        "trading_impact_usd": float(trades["trade_usd"].abs().sum() / 2),
        "max_days_to_trade": float(np.nanmax(trades["days_to_trade"])) if len(trades) else 0.0,
    }
    trades = trades.reset_index(names="ticker").sort_values("trade_usd", key=abs, ascending=False)
    return k, trades
