-- GOLD: business-ready tables for the methodology team, Genie and the app.

CREATE OR REFRESH MATERIALIZED VIEW gold_universe_monthly
COMMENT 'One row per security per month-end (latest trading day for the current month): market cap, liquidity, eligibility, rank and index membership. Market cap uses only shares known on that date.'
AS WITH px AS (
  SELECT ticker, trade_date, close,
    avg(close * volume) OVER (PARTITION BY ticker ORDER BY trade_date ROWS BETWEEN 62 PRECEDING AND CURRENT ROW) AS adv_usd_3m,
    count(*) OVER (PARTITION BY ticker ORDER BY trade_date ROWS BETWEEN 62 PRECEDING AND CURRENT ROW) AS obs_3m,
    max(trade_date) OVER (PARTITION BY date_trunc('MONTH', trade_date)) AS month_last_day
  FROM silver_prices
), me AS (
  SELECT * FROM px WHERE trade_date = month_last_day
), sh AS (
  SELECT me.ticker, me.trade_date,
    coalesce(max_by(CASE WHEN s.known_date <= me.trade_date THEN s.shares END,
                    CASE WHEN s.known_date <= me.trade_date THEN s.known_date END),
             min_by(s.shares, s.known_date)) AS shares
  FROM me JOIN silver_securities sec ON sec.ticker = me.ticker JOIN silver_shares s ON s.cik = sec.cik
  GROUP BY me.ticker, me.trade_date
), mem AS (
  SELECT me.ticker, me.trade_date, max_by(e.action, e.effective_date) AS last_action
  FROM me JOIN silver_index_events e
    ON e.ticker = me.ticker AND e.effective_date <= me.trade_date AND e.action IN ('ADD', 'REMOVE')
  GROUP BY me.ticker, me.trade_date
), base AS (
  SELECT me.trade_date AS snapshot_date, me.ticker, sec.company_name, sec.sector, sec.is_financial,
    me.close, sh.shares, me.close * sh.shares AS market_cap, me.adv_usd_3m,
    coalesce(mem.last_action = 'ADD', false) AS in_index,
    (NOT sec.is_financial AND me.adv_usd_3m >= 5000000 AND me.obs_3m >= 20 AND sh.shares > 0) AS eligible
  FROM me JOIN silver_securities sec ON sec.ticker = me.ticker
  JOIN sh ON sh.ticker = me.ticker AND sh.trade_date = me.trade_date
  LEFT JOIN mem ON mem.ticker = me.ticker AND mem.trade_date = me.trade_date
), ranked AS (
  SELECT *, CASE WHEN eligible THEN rank() OVER (PARTITION BY snapshot_date
                 ORDER BY CASE WHEN eligible THEN market_cap END DESC NULLS LAST, ticker) END AS mcap_rank
  FROM base
)
SELECT *, mcap_rank - 100 AS ranks_from_cutoff,
  close / lag(close, 1) OVER (PARTITION BY ticker ORDER BY snapshot_date) - 1 AS return_1m,
  close / lag(close, 3) OVER (PARTITION BY ticker ORDER BY snapshot_date) - 1 AS return_3m,
  lag(mcap_rank, 3) OVER (PARTITION BY ticker ORDER BY snapshot_date) AS mcap_rank_3m_ago
FROM ranked;

CREATE OR REFRESH MATERIALIZED VIEW gold_index_constituents
COMMENT 'Current NextDAQ-100 baseline: members at the latest snapshot with market-cap and capped weights (two-stage cap: names above 4.5% scaled to 40% when they exceed 48%, others capped at the lower of 4.4% and the smallest large weight)'
AS WITH latest AS (
  SELECT * FROM gold_universe_monthly
  WHERE in_index AND snapshot_date = (SELECT max(snapshot_date) FROM gold_universe_monthly)
), w0 AS (
  SELECT *, market_cap / sum(market_cap) OVER () AS weight_uncapped FROM latest
), g AS (
  SELECT *, weight_uncapped > 0.045 AS is_large,
    sum(CASE WHEN weight_uncapped > 0.045 THEN weight_uncapped ELSE 0 END) OVER () AS large_sum FROM w0
), s2 AS (
  SELECT *, large_sum > 0.48 AS stage2,
    CASE WHEN large_sum <= 0.48 THEN weight_uncapped
         WHEN is_large THEN weight_uncapped * 0.40 / large_sum
         ELSE weight_uncapped * 0.60 / (1 - large_sum) END AS w1 FROM g
), s3 AS (
  SELECT *, LEAST(0.044, coalesce(min(CASE WHEN is_large THEN w1 END) OVER (), 0.044)) AS small_cap FROM s2
), p1 AS (
  SELECT *, CASE WHEN stage2 AND NOT is_large AND w1 > small_cap THEN small_cap
                 WHEN stage2 AND NOT is_large THEN w1 + w1 / sum(CASE WHEN NOT is_large AND w1 <= small_cap THEN w1 END) OVER ()
                      * sum(CASE WHEN NOT is_large AND w1 > small_cap THEN w1 - small_cap ELSE 0 END) OVER ()
                 ELSE w1 END AS w2 FROM s3
), p2 AS (
  SELECT *, CASE WHEN stage2 AND NOT is_large AND w2 > small_cap THEN small_cap
                 WHEN stage2 AND NOT is_large THEN w2 + w2 / sum(CASE WHEN NOT is_large AND w2 <= small_cap THEN w2 END) OVER ()
                      * sum(CASE WHEN NOT is_large AND w2 > small_cap THEN w2 - small_cap ELSE 0 END) OVER ()
                 ELSE w2 END AS w3 FROM p1
)
SELECT snapshot_date, ticker, company_name, sector, close, shares, market_cap, adv_usd_3m, mcap_rank,
  weight_uncapped, LEAST(w3, CASE WHEN stage2 AND NOT is_large THEN small_cap ELSE 1 END) AS weight,
  is_large AS in_aggregate_cap_group
FROM p2;

CREATE OR REFRESH MATERIALIZED VIEW gold_reconstitution_history
COMMENT 'Every past index change (initial composition, annual reconstitutions, special rebalances) with the rank and market cap on the reference date'
AS SELECT e.effective_date, e.announcement_date, e.reference_date, e.event_type, e.action, e.ticker,
  s.company_name, s.sector, e.weight_after, u.mcap_rank AS rank_at_reference, u.market_cap AS market_cap_at_reference,
  u.adv_usd_3m AS adv_usd_3m_at_reference
FROM silver_index_events e
LEFT JOIN silver_securities s ON s.ticker = e.ticker
LEFT JOIN gold_universe_monthly u ON u.ticker = e.ticker AND u.snapshot_date = e.reference_date;

CREATE OR REFRESH MATERIALIZED VIEW gold_etf_exposure
COMMENT 'Monthly assets (USD) of each product tracking the NextDAQ-100 and the total; drives the estimated ETF trading impact (AUM x weight change)'
AS SELECT as_of_date, product_code, product_name, aum_usd,
  sum(aum_usd) OVER (PARTITION BY as_of_date) AS total_aum_usd
FROM silver_etf_aum;
