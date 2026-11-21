"""NextDAQ-100 Rebalance Simulator (Databricks App, Streamlit).

Reads gold tables through the SQL warehouse WITH THE SIGNED-IN USER'S TOKEN (Unity Catalog row filters and MNPI masks
apply per user); asks Genie with the user's token; writes scenarios, approvals and the audit trail to Lakebase as the
app's service principal; drafts AI summaries with the same prompt as the batch job (prompts.py).
"""
import json
import os
import uuid
from datetime import datetime, timezone

import pandas as pd
import psycopg
import requests
import streamlit as st
from databricks import sql as dbsql
from databricks.sdk import WorkspaceClient

import engine
import prompts

CAT, SCH = os.environ.get("CATALOG", "fe_bar_2026_kelemen_catalog"), os.environ.get("SCHEMA", "nextdaq_index")
T = lambda t: f"{CAT}.{SCH}.{t}"  # noqa: E731
WAREHOUSE = os.environ["DATABRICKS_WAREHOUSE_ID"]
GENIE_SPACE = os.environ.get("GENIE_SPACE_ID", "")
LLM = os.environ.get("LLM_ENDPOINT", "databricks-claude-sonnet-4-6")
PG_ENDPOINT = os.environ.get("LAKEBASE_ENDPOINT", "")
EFFECTIVE_DATE = "2026-12-21"

st.set_page_config(page_title="NextDAQ-100 Rebalance Simulator", page_icon="assets/nextdaq_mark.svg", layout="wide")
w = WorkspaceClient()                       # app service principal (Lakebase, LLM)
HOST = w.config.host.rstrip("/")
headers = st.context.headers
USER_TOKEN = headers.get("X-Forwarded-Access-Token")
USER = headers.get("X-Forwarded-Email") or headers.get("X-Forwarded-Preferred-Username") or "unknown"


# --------------------------------------------------------------------------------------------- data access
def q(sql_text: str, params: dict | None = None) -> pd.DataFrame:
    """Query as the signed-in user (one connection per request, parameterised)."""
    with dbsql.connect(server_hostname=HOST.replace("https://", ""), http_path=f"/sql/1.0/warehouses/{WAREHOUSE}",
                       access_token=USER_TOKEN) as c, c.cursor() as cur:
        cur.execute(sql_text, params or {})
        return pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])


@st.cache_data(ttl=600, show_spinner="Loading governed gold tables...")
def load(user: str):
    u = q(f"""SELECT ticker, company_name, sector, is_financial, market_cap, adv_usd_3m AS adv_usd, in_index, mcap_rank, snapshot_date
              FROM {T('gold_universe_monthly')} WHERE snapshot_date = (SELECT max(snapshot_date) FROM {T('gold_universe_monthly')})""")
    cur = q(f"SELECT ticker, weight FROM {T('gold_index_constituents')}")
    aum = float(q(f"SELECT max_by(total_aum_usd, as_of_date) AS a FROM {T('gold_etf_exposure')}")["a"][0])
    fc = q(f"""SELECT ticker, company_name, sector, in_index, mcap_rank, p_add, p_remove, predicted_action, top_drivers, model_version
               FROM {T('gold_recon_predictions')}""")
    journey = q(f"""SELECT (SELECT count(*) FROM {T('bronze_daily_prices')}) AS raw_rows,
                           (SELECT count(*) FROM {T('silver_prices_quarantine')}) AS quarantined,
                           (SELECT count_if(status = 'RECONCILED') || '/' || count(*) FROM {T('recon_market_data')}) AS files_reconciled,
                           (SELECT count(*) FROM {T('gold_universe_monthly')}) AS gold_rows""")
    return u, cur, aum, fc, journey.iloc[0].to_dict()


def entitlement() -> dict:
    try:
        e = q(f"SELECT persona, sector_scope, can_see_mnpi, can_approve FROM {T('entitlements')} WHERE principal = current_user()")
        return e.iloc[0].to_dict() if len(e) else {"persona": "NONE", "can_see_mnpi": False, "can_approve": False, "sector_scope": "-"}
    except Exception:
        return {"persona": "NOT IN ENTITLEMENTS", "can_see_mnpi": False, "can_approve": False, "sector_scope": "-"}


def pg():
    ep = w.postgres.get_endpoint(name=PG_ENDPOINT)
    cred = w.postgres.generate_database_credential(endpoint=PG_ENDPOINT)     # short-lived OAuth token, never stored
    return psycopg.connect(host=ep.status.hosts.host, port=5432, dbname=os.environ.get("PGDATABASE", "nextdaq"),
                           user=os.environ.get("PGUSER", w.config.client_id), password=cred.token, sslmode="require")


def log_event(event: str, **kw):
    """Structured line in the app logs (read back by tools/generate_evidence.py). No emails or tokens."""
    print(json.dumps({"event": event, "persona": ent.get("persona"), "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **kw},
                     default=str), flush=True)


def audit(cur, entity, entity_id, action, detail):
    cur.execute("INSERT INTO ops.audit_log (entity, entity_id, action, actor, detail) VALUES (%s, %s, %s, %s, %s)",
                (entity, entity_id, action, USER, json.dumps(detail, default=str)))


def ask_genie(question: str) -> dict:
    h = {"Authorization": f"Bearer {USER_TOKEN}"}
    base = f"{HOST}/api/2.0/genie/spaces/{GENIE_SPACE}"
    m = requests.post(f"{base}/start-conversation", headers=h, json={"content": question}, timeout=60).json()
    url = f"{base}/conversations/{m['conversation_id']}/messages/{m['message_id']}"
    import time
    for _ in range(60):
        msg = requests.get(url, headers=h, timeout=60).json()
        if msg.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
            break
        time.sleep(3)
    out = {"text": " ".join(a["text"]["content"] for a in msg.get("attachments", []) if a.get("text")), "sql": None, "table": None}
    att = next((a for a in msg.get("attachments", []) if a.get("query")), None)
    if att:
        out["sql"], out["text"] = att["query"]["query"], out["text"] or att["query"].get("description", "")
        r = requests.get(f"{url}/query-result/{att['attachment_id']}", headers=h, timeout=60).json()["statement_response"]
        out["table"] = pd.DataFrame(r["result"].get("data_array", []), columns=[c["name"] for c in r["manifest"]["schema"]["columns"]])
    return out


def ai_summary(facts: dict) -> dict:
    body = {"messages": [{"role": "user", "content": prompts.INSTRUCTIONS + json.dumps(facts)}], "temperature": 0.0,
            "response_format": prompts.RESPONSE_SCHEMA}
    r = w.api_client.do("POST", f"/serving-endpoints/{LLM}/invocations", body=body)
    return json.loads(r["choices"][0]["message"]["content"])


# --------------------------------------------------------------------------------------------- scenario engine
def run_scenario(u, current, aum, rules: engine.Rules, shock_ticker: str | None, shock_pct: float, name: str) -> dict:
    x = u.copy()
    if shock_ticker:
        x.loc[x["ticker"] == shock_ticker, "market_cap"] *= 1 + shock_pct / 100
    members = set(u.loc[u["in_index"], "ticker"])
    prop, _ = engine.build_index(x, members, rules)
    adv = x.set_index("ticker")["adv_usd"]
    kpis, trades = engine.scenario_kpis(current, prop[["ticker", "weight"]], adv, aum)
    k0, _ = engine.scenario_kpis(current, current, adv, aum)
    chk = engine.needs_capping(prop.set_index("ticker")["market_cap"] / prop["market_cap"].sum(), rules)
    ranks = engine.rank_universe(x, rules).set_index("ticker")["rank"]
    trades["rank"] = trades["ticker"].map(ranks)
    trades["company"] = trades["ticker"].map(u.set_index("ticker")["company_name"])
    facts = {"scenario": name, "event": "proposed NextDAQ-100 rebalance", "description": name, "as_of_date": str(u["snapshot_date"].max()),
             "effective_date": EFFECTIVE_DATE, "index": "NextDAQ-100", "aum_tracking_index_usd": round(aum),
             "aum_note": "assets of ETFs and other products tracking the index; trading_impact_usd = assets x weight change",
             "rules": rules.to_dict(),
             "uncapped_concentration": {"max_single_weight_pct": round(chk["max_weight"] * 100, 2), "single_cap_limit_pct": rules.single_cap * 100,
                                        "single_cap_breached": chk["single_breach"], "aggregate_large_weight_pct": round(chk["aggregate_weight"] * 100, 2),
                                        "aggregate_cap_limit_pct": rules.agg_cap * 100, "aggregate_cap_breached": chk["aggregate_breach"]},
             "additions": [{"ticker": t} for t in trades.loc[trades["action"] == "ADD", "ticker"]],
             "removals": [{"ticker": t} for t in trades.loc[trades["action"] == "REMOVE", "ticker"]],
             "kpis_today": {k: round(v, 2) for k, v in k0.items() if k in ("top10_weight_pct", "max_weight_pct", "hhi")},
             "kpis_after": {k: round(v, 2) for k, v in kpis.items()},
             "largest_trades": [{"ticker": r.ticker, "trade_usd": round(r.trade_usd)} for r in trades.head(5).itertuples()]}
    return {"name": name, "rules": rules.to_dict(), "kpis": kpis, "kpis_today": k0, "trades": trades, "facts": facts,
            "shock": {"ticker": shock_ticker, "pct": shock_pct}}


# --------------------------------------------------------------------------------------------- look and feel
NAVY, TEAL, CYAN, AMBER, MIST = "#0B1F3A", "#00A6A0", "#3DD9D0", "#F2A93B", "#F3F6FA"
HERE = os.path.dirname(os.path.abspath(__file__))
LOGO_SVG = open(os.path.join(HERE, "assets", "nextdaq_logo.svg")).read()

st.markdown(f"""
<style>
  .block-container {{ padding-top: 1.2rem; max-width: 1400px; }}
  h1, h2, h3 {{ color: {NAVY}; letter-spacing: -0.01em; }}
  .nd-header {{ display:flex; align-items:center; gap:18px; flex-wrap:wrap; padding:14px 20px; border-radius:14px;
               background: linear-gradient(90deg, {MIST} 0%, #FFFFFF 70%); border:1px solid #E3E9F1; margin-bottom:14px; }}
  .nd-header svg {{ height:46px; width:auto; flex:0 0 auto; }}
  .nd-header .nd-title {{ font-size:1.35rem; font-weight:700; color:{NAVY}; line-height:1.25; }}
  .nd-header .nd-sub {{ font-size:0.9rem; color:#51627A; line-height:1.35; }}
  .nd-grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap:12px; margin: 6px 0 14px 0; }}
  .nd-card {{ background:#FFFFFF; border:1px solid #E3E9F1; border-left:5px solid {TEAL}; border-radius:12px; padding:12px 14px;
             min-width:0; box-shadow: 0 1px 2px rgba(11,31,58,0.05); }}
  .nd-card.amber {{ border-left-color:{AMBER}; }}
  .nd-card.navy {{ border-left-color:{NAVY}; }}
  .nd-card.cyan {{ border-left-color:{CYAN}; }}
  .nd-label {{ font-size:0.78rem; text-transform:uppercase; letter-spacing:0.04em; color:#51627A; overflow-wrap:anywhere; }}
  .nd-value {{ font-size:1.45rem; font-weight:700; color:{NAVY}; line-height:1.2; margin-top:4px; overflow-wrap:anywhere; }}
  .nd-note {{ font-size:0.8rem; color:#51627A; margin-top:4px; line-height:1.3; overflow-wrap:anywhere; }}
  .nd-delta-up {{ color:#B26A00; font-weight:600; }}
  .nd-delta-down {{ color:#00807B; font-weight:600; }}
  .nd-step {{ background:{MIST}; border-radius:12px; padding:10px 12px; border:1px solid #E3E9F1; min-width:0; }}
  .nd-step .nd-num {{ display:inline-block; width:22px; height:22px; border-radius:50%; background:{TEAL}; color:#fff; text-align:center;
                     font-size:0.75rem; line-height:22px; font-weight:700; margin-right:6px; }}
  .nd-step .nd-name {{ font-weight:700; color:{NAVY}; }}
  .nd-step .nd-what {{ font-size:0.82rem; color:#51627A; margin-top:4px; overflow-wrap:anywhere; }}
  .nd-badge {{ display:inline-block; padding:2px 10px; border-radius:999px; font-size:0.78rem; font-weight:600; margin:2px 4px 2px 0; }}
  .nd-ok {{ background:#E0F6F5; color:#00706B; }}
  .nd-warn {{ background:#FDF1DE; color:#8A5A00; }}
  .nd-muted {{ background:#EEF2F7; color:#3B4B63; }}
  .nd-box {{ background:#FFFFFF; border:1px solid #E3E9F1; border-radius:12px; padding:14px 16px; overflow-wrap:anywhere; line-height:1.5; }}
  section[data-testid="stSidebar"] {{ background:{MIST}; }}
  div[data-testid="stDataFrame"] {{ border:1px solid #E3E9F1; border-radius:10px; }}
  .stButton > button {{ border-radius:10px; font-weight:600; }}
  .stButton > button[kind="primary"] {{ background:{TEAL}; border-color:{TEAL}; }}
</style>""", unsafe_allow_html=True)


def usd(x) -> str:
    if x is None or pd.isna(x):
        return "-"
    x = float(x)
    for d, s in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(x) >= d:
            return f"${x / d:,.1f}{s}"
    return f"${x:,.0f}"


def esc(t) -> str:
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def header(title: str, sub: str):
    st.markdown(f'<div class="nd-header">{LOGO_SVG}<div><div class="nd-title">{esc(title)}</div>'
                f'<div class="nd-sub">{esc(sub)}</div></div></div>', unsafe_allow_html=True)


def cards(items):
    """items: (label, value, note, colour) - wraps instead of truncating."""
    html = "".join(f'<div class="nd-card {c}"><div class="nd-label">{esc(l)}</div><div class="nd-value">{esc(v)}</div>'
                   f'<div class="nd-note">{n}</div></div>' for l, v, n, c in items)
    st.markdown(f'<div class="nd-grid">{html}</div>', unsafe_allow_html=True)


def delta(now, before, unit="pp"):
    d = now - before
    if abs(d) < 0.005:
        return "no change vs today"
    cls = "nd-delta-up" if d > 0 else "nd-delta-down"
    return f'<span class="{cls}">{d:+.2f} {unit}</span> vs today'


def badge(text, kind="muted"):
    return f'<span class="nd-badge nd-{kind}">{esc(text)}</span>'


PCT = lambda label: st.column_config.NumberColumn(label, format="%.2f%%")  # noqa: E731
USD = lambda label: st.column_config.NumberColumn(label, format="$%,.0f")  # noqa: E731


def change_table(trades: pd.DataFrame) -> pd.DataFrame:
    t = trades.copy()
    t["weight_after"] = t["weight_after"] * 100
    t["weight_before"] = t["weight_before"] * 100
    return t


# --------------------------------------------------------------------------------------------- page
u, current, aum, fc, journey = load(USER)
ent = entitlement()
mnpi_ok = bool(ent.get("can_see_mnpi"))

with st.sidebar:
    st.logo(os.path.join(HERE, "assets", "nextdaq_logo.svg"), size="large", icon_image=os.path.join(HERE, "assets", "nextdaq_mark.svg"))
    page = st.radio("Go to", ["Overview", "Scenario Lab", "Compare & Approve", "Ask Genie"],
                    captions=["The journey and headline numbers", "Change the rules, see the impact", "Decide and record it", "Questions in plain English"])
    st.divider()
    st.markdown(f"**Signed in as** {esc(USER)}", unsafe_allow_html=True)
    st.markdown(badge(ent["persona"].replace("_", " ").title(), "ok") +
                badge("MNPI cleared" if mnpi_ok else "Not MNPI cleared", "ok" if mnpi_ok else "warn") +
                badge("Can approve" if ent.get("can_approve") else "Cannot approve", "ok" if ent.get("can_approve") else "muted") +
                badge(f"Sectors: {ent['sector_scope']}", "muted"), unsafe_allow_html=True)
    st.caption("Access comes from the Unity Catalog entitlements table. Forecasts and briefs are masked by the platform, not by this app.")

log_event("page_view", page=page, universe_rows=len(u), forecast_rows=len(fc), forecast_unmasked=int(fc["p_add"].notna().sum()),
          mnpi_cleared=mnpi_ok, can_approve=bool(ent.get("can_approve")))
asof = str(u["snapshot_date"].max())

if page == "Overview":
    header("NextDAQ-100 rebalance simulator", f"From raw market data to an approved index decision · data as of {asof} · "
           f"next reconstitution effective {EFFECTIVE_DATE}")
    k0, _ = engine.scenario_kpis(current, current, u.set_index("ticker")["adv_usd"], aum)
    n_add, n_rem = int((fc["predicted_action"] == "ADD").sum()), int((fc["predicted_action"] == "REMOVE").sum())
    cards([("Assets tracking the index", usd(aum), "ETFs and other products (gold_etf_exposure)", "navy"),
           ("Top-10 weight", f"{k0['top10_weight_pct']:.1f}%", "current capped weights", ""),
           ("Largest single weight", f"{k0['max_weight_pct']:.1f}%", "cap trigger 24%", ""),
           ("Concentration (HHI)", f"{k0['hhi']:.0f}", "sum of squared weights x 10,000", "cyan"),
           ("Forecast changes", f"{n_add} adds · {n_rem} removes" if mnpi_ok else "Restricted",
            "MLflow model in Unity Catalog" if mnpi_ok else "masked: not MNPI cleared", "amber")])
    st.subheader("How the data gets here")
    steps = [("Ingest", "Lakeflow", f"{int(journey['raw_rows']):,} raw price rows; {journey['quarantined']} quarantined; {journey['files_reconciled']} files reconciled"),
             ("Govern", "Unity Catalog", "sector row filter, MNPI masks, lineage, governed tags"),
             ("Predict", "ML + GenAI", "add/remove forecast; AI impact summaries, judged before use"),
             ("Operate", "Lakebase", "saved scenarios, approvals and the audit trail"),
             ("Ask", "Genie", "plain-English questions on the same gold tables"),
             ("Decide", "This app", "change rules, compare, submit, approve")]
    st.markdown('<div class="nd-grid">' + "".join(
        f'<div class="nd-step"><span class="nd-num">{i}</span><span class="nd-name">{esc(n)}</span>'
        f'<div class="nd-what"><b>{esc(p)}</b>: {esc(w_)}</div></div>' for i, (n, p, w_) in enumerate(steps, 1)) + "</div>",
        unsafe_allow_html=True)
    st.subheader("Names to watch at the next reconstitution")
    if not mnpi_ok:
        st.warning("You are not cleared for MNPI, so Unity Catalog masks the forecast columns below.")
    watch = fc[fc["predicted_action"].isin(["ADD", "REMOVE", "RESTRICTED"])].sort_values("mcap_rank").head(15).copy()
    watch[["p_add", "p_remove"]] = watch[["p_add", "p_remove"]] * 100
    st.dataframe(watch[["ticker", "company_name", "sector", "mcap_rank", "in_index", "predicted_action", "p_add", "p_remove", "top_drivers"]],
                 hide_index=True, width="stretch",
                 column_config={"ticker": "Ticker", "company_name": st.column_config.TextColumn("Company", width="medium"),
                                "sector": "Sector", "mcap_rank": st.column_config.NumberColumn("Rank", format="%d"),
                                "in_index": "Member", "predicted_action": "Forecast", "p_add": PCT("P(add)"), "p_remove": PCT("P(remove)"),
                                "top_drivers": st.column_config.TextColumn("Why", width="large")})
    st.caption("Source: gold_recon_predictions. The forecast is a ranked watchlist: on the held-out reconstitution it did not beat "
               "a simple rank rule, so it supports, not replaces, the methodology team.")
    try:
        with pg() as conn:
            s = pd.read_sql("SELECT status, count(*) AS n FROM ops.scenarios GROUP BY 1", conn)
        st.markdown("**Scenario workflow (Lakebase):** " + (" ".join(badge(f"{r.status.title()}: {r.n}", "ok" if r.status == "APPROVED" else "muted")
                                                                       for r in s.itertuples()) or badge("No scenarios yet")), unsafe_allow_html=True)
    except Exception as e:  # noqa: BLE001
        st.caption(f"Lakebase not reachable: {type(e).__name__}")

elif page == "Scenario Lab":
    header("Scenario Lab", "Adjust the methodology and see who joins or leaves, how weights change and what ETFs must trade.")
    with st.container(border=True):
        st.markdown("**Rules**")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.caption("Concentration caps")
            agg_cap = st.slider("Aggregate cap trigger (%)", 30, 60, 48, help="Names above 4.5% together may not exceed this") / 100
            agg_target = st.slider("Aggregate target after capping (%)", 25, 50, 40) / 100
            single_target = st.slider("Single-name target (%)", 5, 25, 20) / 100
        with c2:
            st.caption("Eligibility and bands")
            liq = st.select_slider("Liquidity minimum ($M per day)", [1, 5, 10, 25, 50, 100], 5,
                                   help="3-month average daily value traded")
            add_rank = st.slider("Add non-members ranked at or above", 70, 100, 90)
            keep_rank = st.slider("Keep members ranked at or above", 100, 150, 110)
        with c3:
            st.caption("Exclusions and stress test")
            excl = st.multiselect("Exclude sectors", sorted(u["sector"].dropna().unique()))
            big = u.sort_values("market_cap", ascending=False)["ticker"].head(20).tolist()
            shock_t = st.selectbox("Shock one company", ["(none)"] + big, index=0)
            shock_p = st.slider("Move before the reference date (%)", -50, 50, 30)
        name = st.text_input("Scenario name", "My scenario")
    rules = engine.Rules(agg_cap=agg_cap, agg_target=min(agg_target, agg_cap), single_target=single_target,
                         liquidity_min_usd=liq * 1e6, add_rank=add_rank, buffer_rank=keep_rank, exclude_sectors=tuple(excl))
    sc = run_scenario(u, current, aum, rules, None if shock_t == "(none)" else shock_t, shock_p, name)
    k, k0 = sc["kpis"], sc["kpis_today"]
    log_event("scenario_run", name=name, rules=sc["rules"], shock=sc["shock"], kpis={x: round(v, 2) for x, v in k.items()})
    cards([("Additions · removals", f"{k['additions']} · {k['removals']}", "constituent changes", "navy"),
           ("Turnover", f"{k['turnover_pct']:.2f}%", "one-way, by weight", ""),
           ("Top-10 weight", f"{k['top10_weight_pct']:.1f}%", delta(k["top10_weight_pct"], k0["top10_weight_pct"]), ""),
           ("Largest weight", f"{k['max_weight_pct']:.1f}%", delta(k["max_weight_pct"], k0["max_weight_pct"]), "cyan"),
           ("ETF trading impact", usd(k["trading_impact_usd"]), "assets x weight change", "amber"),
           ("Max days to trade", f"{k['max_days_to_trade']:,.1f}", "at 20% of daily volume", "amber" if k["max_days_to_trade"] > 5 else "")])
    ch = change_table(sc["trades"][sc["trades"]["action"].isin(["ADD", "REMOVE"])])
    illiquid = ch[ch["days_to_trade"] > 5]["ticker"].tolist()
    if illiquid:
        st.warning(f"Liquidity check: {', '.join(illiquid)} would take more than 5 days to trade. Try a higher liquidity minimum.")
    t1, t2, t3 = st.tabs(["Additions and removals", "Bubble names (ranks 85-115)", "Largest trades"])
    cfg = {"action": "Change", "ticker": "Ticker", "company": st.column_config.TextColumn("Company", width="medium"),
           "rank": st.column_config.NumberColumn("Rank", format="%d"), "weight_before": PCT("Weight today"),
           "weight_after": PCT("Weight after"), "trade_usd": USD("ETF trade"),
           "days_to_trade": st.column_config.NumberColumn("Days to trade", format="%.1f")}
    with t1:
        st.dataframe(ch[["action", "ticker", "company", "rank", "weight_after", "trade_usd", "days_to_trade"]],
                     hide_index=True, width="stretch", column_config=cfg)
    with t2:
        rk = engine.rank_universe(u, rules)
        bub = rk[rk["rank"].between(85, 115)][["ticker", "company_name", "sector", "rank", "in_index", "market_cap", "adv_usd"]].sort_values("rank")
        st.dataframe(bub, hide_index=True, width="stretch",
                     column_config={"ticker": "Ticker", "company_name": st.column_config.TextColumn("Company", width="medium"),
                                    "sector": "Sector", "rank": st.column_config.NumberColumn("Rank", format="%d"), "in_index": "Member",
                                    "market_cap": USD("Market cap"), "adv_usd": USD("Avg daily value traded")})
    with t3:
        st.dataframe(change_table(sc["trades"].head(10))[["ticker", "action", "weight_before", "weight_after", "trade_usd", "days_to_trade"]],
                     hide_index=True, width="stretch", column_config=cfg)
    st.caption("Engine: src/app/engine.py, the same code that generated the index history and the evaluated batch briefs.")
    a, b, _ = st.columns([1, 1, 3])
    if a.button("Keep as scenario A", type="primary", width="stretch"):
        st.session_state["A"] = sc
        st.toast(f"Saved '{name}' as scenario A")
    if b.button("Keep as scenario B", width="stretch"):
        st.session_state["B"] = sc
        st.toast(f"Saved '{name}' as scenario B")

elif page == "Compare & Approve":
    header("Compare, draft and approve", "Side-by-side quality KPIs, an AI-drafted impact summary, a templated client notice, "
           "and the approval trail in Lakebase.")
    A, B = st.session_state.get("A"), st.session_state.get("B")
    if not (A or B):
        st.info("Keep at least one scenario in the Scenario Lab first.")
    else:
        labels = {"additions": "Additions", "removals": "Removals", "turnover_pct": "Turnover (%)", "top10_weight_pct": "Top-10 weight (%)",
                  "max_weight_pct": "Largest weight (%)", "hhi": "HHI", "trading_impact_usd": "ETF trading impact",
                  "max_days_to_trade": "Max days to trade"}
        comp = {"Metric": list(labels.values())}
        for lbl, s in (("A", A), ("B", B)):
            if s:
                comp[f"{lbl} · {s['name']}"] = [usd(s["kpis"][m]) if m == "trading_impact_usd" else f"{s['kpis'][m]:,.2f}" for m in labels]
        st.dataframe(pd.DataFrame(comp), hide_index=True, width="stretch")
        opts = [x for x in ("A", "B") if st.session_state.get(x)]
        pick = st.radio("Scenario to take forward", opts, horizontal=True, format_func=lambda x: f"{x} · {st.session_state[x]['name']}")
        s = st.session_state[pick]
        left, right = st.columns([3, 2])
        with left:
            st.markdown("**AI impact summary**")
            if st.button("Generate AI summary", type="primary"):
                with st.spinner("Drafting with the same prompt as the evaluated batch job..."):
                    s["brief"] = ai_summary(s["facts"])
                log_event("ai_summary", scenario=s["name"], prompt_version=prompts.PROMPT_VERSION, words=len(s["brief"]["impact_summary"].split()))
            if s.get("brief"):
                st.markdown(f'<div class="nd-box">{esc(s["brief"]["impact_summary"])}</div>', unsafe_allow_html=True)
                st.markdown(" ".join(badge(r, "warn") for r in s["brief"]["key_risks"]), unsafe_allow_html=True)
                st.caption(f"Draft by {LLM}, prompt {prompts.PROMPT_VERSION}. A person reviews every draft before it is used.")
        with right:
            st.markdown("**ETF-issuer notice** " + badge("Draft · pending approval", "warn"), unsafe_allow_html=True)
            st.code(prompts.render_notice(s["facts"]), language=None, wrap_lines=True)
            st.caption("Filled from the scenario facts by a template, not written by AI.")
        if st.button("Submit for approval"):
            sid = f"SCN-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:6]}"
            with pg() as conn, conn.cursor() as cur:
                cur.execute("""INSERT INTO ops.scenarios (scenario_id, name, rules_json, kpis_json, impact_summary, client_notice,
                               status, created_by, submitted_at) VALUES (%s,%s,%s,%s,%s,%s,'SUBMITTED',%s, now())""",
                            (sid, s["name"], json.dumps(s["rules"]), json.dumps(s["kpis"]),
                             (s.get("brief") or {}).get("impact_summary"), prompts.render_notice(s["facts"]), USER))
                audit(cur, "scenario", sid, "SUBMITTED", {"rules": s["rules"], "shock": s["shock"], "kpis": s["kpis"]})
            log_event("scenario_submitted", scenario_id=sid)
            st.success(f"Submitted {sid} for approval. It is stored in Lakebase.")
    st.divider()
    st.subheader("Approval queue")
    with pg() as conn:
        qd = pd.read_sql("SELECT scenario_id, name, status, created_by, submitted_at FROM ops.scenarios ORDER BY submitted_at DESC NULLS LAST LIMIT 20", conn)
    st.dataframe(qd, hide_index=True, width="stretch",
                 column_config={"scenario_id": "Scenario", "name": st.column_config.TextColumn("Name", width="medium"), "status": "Status",
                                "created_by": "Proposed by", "submitted_at": st.column_config.DatetimeColumn("Submitted", format="YYYY-MM-DD HH:mm")})
    pending = qd[qd["status"] == "SUBMITTED"]["scenario_id"].tolist()
    if pending:
        if not ent.get("can_approve"):
            st.info("Only the Head of Index Methodology can approve (entitlements: can_approve).")
        else:
            with st.container(border=True):
                sid = st.selectbox("Scenario to decide", pending)
                comment = st.text_input("Comment for the record")
                c1, c2, _ = st.columns([1, 1, 3])
                for col, decision, kind in ((c1, "APPROVED", "primary"), (c2, "REJECTED", "secondary")):
                    if col.button(decision.title(), type=kind, width="stretch"):
                        with pg() as conn, conn.cursor() as cur:
                            cur.execute("UPDATE ops.scenarios SET status = %s WHERE scenario_id = %s AND status = 'SUBMITTED'", (decision, sid))
                            cur.execute("INSERT INTO ops.approvals (scenario_id, decision, decided_by, comment) VALUES (%s,%s,%s,%s)",
                                        (sid, decision, USER, comment))
                            audit(cur, "scenario", sid, decision, {"comment": comment})
                        log_event("scenario_decision", scenario_id=sid, decision=decision)
                        st.success(f"{sid}: {decision.title()}")
    st.subheader("Audit trail")
    with pg() as conn:
        st.dataframe(pd.read_sql("SELECT at, action, entity_id, actor FROM ops.audit_log ORDER BY at DESC LIMIT 20", conn),
                     hide_index=True, width="stretch",
                     column_config={"at": st.column_config.DatetimeColumn("When", format="YYYY-MM-DD HH:mm:ss"), "action": "Action",
                                    "entity_id": "Scenario", "actor": "By"})

else:
    header("Ask Genie", "Plain-English questions over the governed gold tables, answered with your own identity, so Unity Catalog policies apply.")
    samples = ["Which predicted removals have the highest ETF trading impact?",
               "Which Technology stocks are within 10 ranks of the cutoff on the latest snapshot?",
               "How many additions and removals were there in each of the last 3 annual reconstitutions?"]
    choice = st.pills("Suggested questions", samples, selection_mode="single", default=samples[0])
    qtext = st.text_input("Your question", choice or samples[0])
    if st.button("Ask Genie", type="primary"):
        with st.spinner("Genie is writing SQL..."):
            g = ask_genie(qtext)
        log_event("genie_answer", question=qtext, rows=0 if g["table"] is None else len(g["table"]), sql_returned=bool(g["sql"]))
        if g["text"]:
            st.markdown(f'<div class="nd-box">{esc(g["text"])}</div>', unsafe_allow_html=True)
        if g["table"] is not None:
            st.dataframe(g["table"], hide_index=True, width="stretch")
        if g["sql"]:
            with st.expander("SQL Genie ran"):
                st.code(g["sql"], language="sql", wrap_lines=True)
