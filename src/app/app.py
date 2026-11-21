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

st.set_page_config(page_title="NextDAQ-100 Rebalance Simulator", layout="wide")
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


# --------------------------------------------------------------------------------------------- UI
u, current, aum, fc, journey = load(USER)
ent = entitlement()
st.sidebar.title("NextDAQ-100")
st.sidebar.caption(f"Signed in as **{USER}**")
st.sidebar.write(f"Persona: **{ent['persona']}**  \nSector scope: {ent['sector_scope']}  \nMNPI cleared: {ent['can_see_mnpi']}  \n"
                 f"Can approve: {ent['can_approve']}")
st.sidebar.caption("Access comes from the Unity Catalog entitlements table; the forecast and briefs are masked by the platform.")
page = st.sidebar.radio("Screen", ["Overview", "Scenario Lab", "Compare & Approve", "Ask Genie"])
mnpi_ok = bool(ent.get("can_see_mnpi"))
log_event("page_view", page=page, universe_rows=len(u), forecast_rows=len(fc), forecast_unmasked=int(fc["p_add"].notna().sum()),
          mnpi_cleared=mnpi_ok, can_approve=bool(ent.get("can_approve")))

if page == "Overview":
    st.title("NextDAQ-100 rebalance: from raw data to an approved decision")
    st.caption(f"Data as of {u['snapshot_date'].max()} · next reconstitution effective {EFFECTIVE_DATE}")
    cols = st.columns(6)
    steps = [("Raw files", f"{journey['raw_rows']:,} price rows", "UC volume, Auto Loader"),
             ("Lakeflow", f"{journey['quarantined']} rows quarantined", f"{journey['files_reconciled']} files reconciled"),
             ("Unity Catalog", "MNPI masked", "sector row filter + masks"),
             ("ML + GenAI", f"{(fc['predicted_action'] == 'ADD').sum()} adds / {(fc['predicted_action'] == 'REMOVE').sum()} removes",
              "forecast (masked if not cleared)"),
             ("Lakebase", "scenarios + approvals", "operational store"), ("Genie", "plain-English Q&A", "governed gold")]
    for c, (a, b, d) in zip(cols, steps):
        c.metric(a, b)
        c.caption(d)
    k0, _ = engine.scenario_kpis(current, current, u.set_index("ticker")["adv_usd"], aum)
    m = st.columns(4)
    m[0].metric("Assets tracking the index", f"${aum / 1e9:,.0f}B")
    m[1].metric("Top-10 weight", f"{k0['top10_weight_pct']:.1f}%")
    m[2].metric("Largest single weight", f"{k0['max_weight_pct']:.1f}%")
    m[3].metric("Concentration (HHI)", f"{k0['hhi']:.0f}")
    st.subheader("Names to watch for the next reconstitution")
    st.caption("Source: gold_recon_predictions (MLflow model in Unity Catalog). Probabilities are MNPI and masked for users not cleared.")
    watch = fc[fc["predicted_action"].isin(["ADD", "REMOVE"]) | (fc["predicted_action"] == "RESTRICTED")]
    if not mnpi_ok:
        st.warning("You are not cleared for MNPI: forecast columns are masked by Unity Catalog.")
    st.dataframe(watch.sort_values("mcap_rank").head(15), hide_index=True, use_container_width=True)
    try:
        with pg() as conn:
            s = pd.read_sql("SELECT status, count(*) AS scenarios FROM ops.scenarios GROUP BY 1", conn)
        st.caption("Scenario workflow (Lakebase): " + (", ".join(f"{r.status}: {r.scenarios}" for r in s.itertuples()) or "none yet"))
    except Exception as e:  # noqa: BLE001
        st.caption(f"Lakebase not reachable: {type(e).__name__}")

elif page == "Scenario Lab":
    st.title("Scenario Lab")
    st.caption("Adjust the methodology and see who joins or leaves and how weights change. Engine: src/app/engine.py "
               "(the same code that generated the index history and the batch AI briefs).")
    c1, c2, c3 = st.columns(3)
    agg_cap = c1.slider("Aggregate cap trigger (%)", 30, 60, 48) / 100
    agg_target = c1.slider("Aggregate target after capping (%)", 25, 50, 40) / 100
    single_target = c1.slider("Single-name target (%)", 5, 25, 20) / 100
    liq = c2.select_slider("Liquidity minimum (3-month avg daily value traded)", [1, 5, 10, 25, 50, 100], 5)
    add_rank = c2.slider("Add band: non-members ranked at or above", 70, 100, 90)
    keep_rank = c2.slider("Keep band: members ranked at or above", 100, 150, 110)
    excl = c3.multiselect("Exclude sectors", sorted(u["sector"].dropna().unique()))
    big = u.sort_values("market_cap", ascending=False)["ticker"].head(20).tolist()
    shock_t = c3.selectbox("Stress test: shock one company", ["(none)"] + big, index=0)
    shock_p = c3.slider("Price move before the reference date (%)", -50, 50, 30)
    rules = engine.Rules(agg_cap=agg_cap, agg_target=min(agg_target, agg_cap), single_target=single_target,
                         liquidity_min_usd=liq * 1e6, add_rank=add_rank, buffer_rank=keep_rank, exclude_sectors=tuple(excl))
    name = st.text_input("Scenario name", "My scenario")
    sc = run_scenario(u, current, aum, rules, None if shock_t == "(none)" else shock_t, shock_p, name)
    k, k0 = sc["kpis"], sc["kpis_today"]
    log_event("scenario_run", name=name, rules=sc["rules"], shock=sc["shock"], kpis={x: round(v, 2) for x, v in k.items()})
    m = st.columns(6)
    m[0].metric("Additions / removals", f"{k['additions']} / {k['removals']}")
    m[1].metric("Turnover", f"{k['turnover_pct']:.2f}%")
    m[2].metric("Top-10 weight", f"{k['top10_weight_pct']:.1f}%", f"{k['top10_weight_pct'] - k0['top10_weight_pct']:+.2f} pp")
    m[3].metric("Largest weight", f"{k['max_weight_pct']:.1f}%", f"{k['max_weight_pct'] - k0['max_weight_pct']:+.2f} pp")
    m[4].metric("ETF trading impact", f"${k['trading_impact_usd'] / 1e9:,.1f}B")
    m[5].metric("Max days to trade (20% of volume)", f"{k['max_days_to_trade']:,.1f}")
    ch = sc["trades"][sc["trades"]["action"].isin(["ADD", "REMOVE"])][["action", "ticker", "company", "rank", "weight_after", "trade_usd", "days_to_trade"]]
    st.subheader("Additions and removals")
    st.dataframe(ch, hide_index=True, use_container_width=True)
    st.subheader("Bubble names (ranked 85-115)")
    rk = engine.rank_universe(u, rules)
    bubble = rk[rk["rank"].between(85, 115)][["ticker", "company_name", "sector", "rank", "in_index", "market_cap", "adv_usd"]].sort_values("rank")
    st.dataframe(bubble, hide_index=True, use_container_width=True)
    st.subheader("Largest trades")
    st.dataframe(sc["trades"].head(10)[["ticker", "action", "weight_before", "weight_after", "trade_usd", "days_to_trade"]], hide_index=True)
    a, b = st.columns(2)
    if a.button("Keep as scenario A"):
        st.session_state["A"] = sc
    if b.button("Keep as scenario B"):
        st.session_state["B"] = sc
    st.caption("Scenarios A and B are compared on the next screen.")

elif page == "Compare & Approve":
    st.title("Compare scenarios, draft the notice, submit for approval")
    A, B = st.session_state.get("A"), st.session_state.get("B")
    if not (A or B):
        st.info("Keep at least one scenario in the Scenario Lab first.")
    else:
        rows = {"metric": ["additions", "removals", "turnover_pct", "top10_weight_pct", "max_weight_pct", "hhi", "trading_impact_usd", "max_days_to_trade"]}
        for lbl, s in (("A", A), ("B", B)):
            if s:
                rows[f"{lbl}: {s['name']}"] = [round(s["kpis"][m], 2) for m in rows["metric"]]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        pick = st.radio("Scenario to submit", [x for x in ("A", "B") if st.session_state.get(x)], horizontal=True)
        s = st.session_state[pick]
        if st.button("Generate AI summary"):
            with st.spinner("Drafting with the same prompt as the evaluated batch job..."):
                s["brief"] = ai_summary(s["facts"])
            log_event("ai_summary", scenario=s["name"], prompt_version=prompts.PROMPT_VERSION, words=len(s["brief"]["impact_summary"].split()))
        if s.get("brief"):
            st.markdown(f"**AI impact summary (draft, prompt {prompts.PROMPT_VERSION}):** {s['brief']['impact_summary']}")
            st.markdown("**Key risks:** " + "; ".join(s["brief"]["key_risks"]))
        st.markdown("**ETF-issuer notice (templated from the facts, not AI-written):**")
        st.code(prompts.render_notice(s["facts"]))
        if st.button("Submit for approval"):
            sid = f"SCN-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:6]}"
            with pg() as conn, conn.cursor() as cur:
                cur.execute("""INSERT INTO ops.scenarios (scenario_id, name, rules_json, kpis_json, impact_summary, client_notice,
                               status, created_by, submitted_at) VALUES (%s,%s,%s,%s,%s,%s,'SUBMITTED',%s, now())""",
                            (sid, s["name"], json.dumps(s["rules"]), json.dumps(s["kpis"]),
                             (s.get("brief") or {}).get("impact_summary"), prompts.render_notice(s["facts"]), USER))
                audit(cur, "scenario", sid, "SUBMITTED", {"rules": s["rules"], "shock": s["shock"], "kpis": s["kpis"]})
            log_event("scenario_submitted", scenario_id=sid)
            st.success(f"Submitted {sid} for approval (stored in Lakebase).")
    st.divider()
    st.subheader("Approval queue (Lakebase)")
    with pg() as conn:
        qd = pd.read_sql("SELECT scenario_id, name, status, created_by, submitted_at FROM ops.scenarios ORDER BY submitted_at DESC NULLS LAST LIMIT 20", conn)
    st.dataframe(qd, hide_index=True, use_container_width=True)
    pending = qd[qd["status"] == "SUBMITTED"]["scenario_id"].tolist()
    if pending:
        if not ent.get("can_approve"):
            st.info("Only the Head of Index Methodology can approve (entitlements: can_approve).")
        else:
            sid = st.selectbox("Scenario", pending)
            comment = st.text_input("Comment")
            c1, c2 = st.columns(2)
            for col, decision in ((c1, "APPROVED"), (c2, "REJECTED")):
                if col.button(decision.title()):
                    with pg() as conn, conn.cursor() as cur:
                        cur.execute("UPDATE ops.scenarios SET status = %s WHERE scenario_id = %s AND status = 'SUBMITTED'", (decision, sid))
                        cur.execute("INSERT INTO ops.approvals (scenario_id, decision, decided_by, comment) VALUES (%s,%s,%s,%s)",
                                    (sid, decision, USER, comment))
                        audit(cur, "scenario", sid, decision, {"comment": comment})
                    log_event("scenario_decision", scenario_id=sid, decision=decision)
                    st.success(f"{sid}: {decision}")
    st.subheader("Audit log (Lakebase)")
    with pg() as conn:
        st.dataframe(pd.read_sql("SELECT at, entity, entity_id, action, actor FROM ops.audit_log ORDER BY at DESC LIMIT 20", conn),
                     hide_index=True, use_container_width=True)

else:
    st.title("Ask Genie")
    st.caption("Genie space over the governed gold tables, asked with your own identity, so Unity Catalog policies apply.")
    samples = ["Which predicted removals have the highest ETF trading impact?",
               "Which Technology stocks are within 10 ranks of the cutoff on the latest snapshot?",
               "How many additions and removals were there in each of the last 3 annual reconstitutions?"]
    qtext = st.text_input("Question", samples[0])
    st.caption("Try: " + " · ".join(samples[1:]))
    if st.button("Ask"):
        with st.spinner("Genie is writing SQL..."):
            g = ask_genie(qtext)
        log_event("genie_answer", question=qtext, rows=0 if g["table"] is None else len(g["table"]), sql_returned=bool(g["sql"]))
        st.markdown(g["text"] or "")
        if g["table"] is not None:
            st.dataframe(g["table"], hide_index=True, use_container_width=True)
        if g["sql"]:
            with st.expander("SQL Genie ran"):
                st.code(g["sql"], language="sql")
