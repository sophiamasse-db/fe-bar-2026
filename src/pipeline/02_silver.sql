-- SILVER: typed, trimmed, deduplicated and conformed. Rejected rows go to quarantine with a reason.

CREATE OR REFRESH MATERIALIZED VIEW silver_securities (
  CONSTRAINT has_sector EXPECT (sic IS NOT NULL),                       -- warn: planted missing SIC
  CONSTRAINT has_ticker EXPECT (ticker IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'One row per issuer (primary listed line): security master + SEC ticker map + SIC sector'
AS WITH sm AS (
  SELECT trim(symbol) AS ticker, trim(security_name) AS security_name, market_category
  FROM bronze_security_master
  WHERE test_issue = 'N' AND etf_flag = 'N' AND symbol NOT LIKE 'File Creation%'
    AND security_name RLIKE 'Common Stock|Ordinary Share|American Depositary Shares|Class A|Class B|Class C'
    AND NOT security_name RLIKE 'Warrant|Right|Unit|Preferred|Notes|Debenture'
), sec AS (
  SELECT CAST(cik AS INT) AS cik, company_name, ticker, sec_row_position,
         row_number() OVER (PARTITION BY cik ORDER BY sec_row_position) AS line_rank
  FROM bronze_sec_companies WHERE exchange = 'Nasdaq'
), sub AS (
  SELECT CAST(cik AS INT) AS cik, nullif(trim(sic), '') AS sic, nullif(trim(sic_description), '') AS sic_description
  FROM bronze_sec_submissions
)
SELECT sm.ticker, sec.cik, sec.company_name, sm.security_name, sm.market_category,
  CAST(sub.sic AS INT) AS sic, sub.sic_description,
  CASE
    WHEN sub.sic IS NULL THEN 'Unclassified'
    WHEN CAST(sub.sic AS INT) BETWEEN 6000 AND 6799 THEN 'Financials'
    WHEN CAST(sub.sic AS INT) IN (3570,3571,3572,3575,3576,3577,3578,3579) OR CAST(sub.sic AS INT) BETWEEN 3670 AND 3679
      OR CAST(sub.sic AS INT) BETWEEN 7370 AND 7379 OR CAST(sub.sic AS INT) BETWEEN 3810 AND 3829 THEN 'Technology'
    WHEN CAST(sub.sic AS INT) BETWEEN 4800 AND 4899 OR CAST(sub.sic AS INT) BETWEEN 7810 AND 7829
      OR CAST(sub.sic AS INT) BETWEEN 2710 AND 2741 THEN 'Communication Services'
    WHEN CAST(sub.sic AS INT) BETWEEN 2830 AND 2836 OR CAST(sub.sic AS INT) BETWEEN 3840 AND 3851
      OR CAST(sub.sic AS INT) BETWEEN 8000 AND 8099 OR CAST(sub.sic AS INT) BETWEEN 8730 AND 8734 THEN 'Health Care'
    WHEN CAST(sub.sic AS INT) BETWEEN 1300 AND 1399 OR CAST(sub.sic AS INT) BETWEEN 2900 AND 2999 THEN 'Energy'
    WHEN CAST(sub.sic AS INT) BETWEEN 4900 AND 4999 THEN 'Utilities'
    WHEN CAST(sub.sic AS INT) BETWEEN 5000 AND 5999 OR CAST(sub.sic AS INT) BETWEEN 7000 AND 7299
      OR CAST(sub.sic AS INT) BETWEEN 3710 AND 3716 OR CAST(sub.sic AS INT) BETWEEN 2000 AND 2399 THEN 'Consumer'
    WHEN CAST(sub.sic AS INT) BETWEEN 2800 AND 2829 OR CAST(sub.sic AS INT) BETWEEN 1000 AND 1499 THEN 'Materials'
    ELSE 'Industrials'
  END AS sector,
  coalesce(CAST(sub.sic AS INT) BETWEEN 6000 AND 6799, false) AS is_financial
FROM sm JOIN sec ON sm.ticker = sec.ticker AND sec.line_rank = 1
JOIN sub ON sub.cik = sec.cik;

CREATE OR REFRESH MATERIALIZED VIEW silver_shares (
  CONSTRAINT positive_shares EXPECT (shares > 0) ON VIOLATION DROP ROW
)
COMMENT 'Shares outstanding per filer and period, point in time (known_date = period end + 14 days). Cover-page count; weighted-average basic shares only for filers with no cover-page count (dual-class filers report per class).'
AS WITH f AS (
  SELECT CAST(cik AS INT) AS cik, CAST(period_end AS DATE) AS period_end, tag,
         CAST(max(CAST(value AS DOUBLE)) AS BIGINT) AS shares
  FROM bronze_sec_facts
  WHERE tag IN ('EntityCommonStockSharesOutstanding', 'WeightedAverageNumberOfSharesOutstandingBasic')
  GROUP BY ALL
), has_cover AS (
  SELECT DISTINCT cik FROM f WHERE tag = 'EntityCommonStockSharesOutstanding'
)
SELECT f.cik, f.period_end, date_add(f.period_end, 14) AS known_date, f.shares,
  CASE WHEN f.tag = 'EntityCommonStockSharesOutstanding' THEN 'COVER_PAGE' ELSE 'WEIGHTED_AVERAGE_FALLBACK' END AS shares_source
FROM f LEFT JOIN has_cover h ON h.cik = f.cik
WHERE f.tag = 'EntityCommonStockSharesOutstanding' OR h.cik IS NULL;

-- Typed prices with a duplicate counter; the clean table and the quarantine both read this view.
CREATE OR REFRESH MATERIALIZED VIEW silver_prices_typed
COMMENT 'Internal: typed price rows with duplicate sequence number'
AS SELECT CAST(trade_date AS DATE) AS trade_date, upper(trim(ticker)) AS ticker,
  CAST(open AS DOUBLE) AS open, CAST(high AS DOUBLE) AS high, CAST(low AS DOUBLE) AS low,
  CAST(nullif(trim(close), '') AS DOUBLE) AS close, CAST(volume AS BIGINT) AS volume, currency,
  _file_name, _source_file, _ingested_at,
  row_number() OVER (PARTITION BY CAST(trade_date AS DATE), upper(trim(ticker)) ORDER BY _ingested_at, _source_file) AS dup_seq
FROM bronze_daily_prices;

CREATE OR REFRESH MATERIALIZED VIEW silver_prices (
  CONSTRAINT unique_ticker_day EXPECT (dup_seq = 1) ON VIOLATION DROP ROW,
  CONSTRAINT valid_close EXPECT (close IS NOT NULL AND close > 0) ON VIOLATION DROP ROW,
  CONSTRAINT valid_volume EXPECT (volume >= 0) ON VIOLATION DROP ROW
)
COMMENT 'Clean daily prices and volume: one row per ticker x trading day'
AS SELECT * FROM silver_prices_typed;

CREATE OR REFRESH MATERIALIZED VIEW silver_prices_quarantine
COMMENT 'Price rows rejected by silver_prices expectations, with the reason, so nothing disappears silently'
AS SELECT *, CASE WHEN dup_seq > 1 THEN 'DUPLICATE_TICKER_DAY'
                  WHEN close IS NULL THEN 'MISSING_CLOSE'
                  WHEN close <= 0 THEN 'NON_POSITIVE_CLOSE'
                  ELSE 'NEGATIVE_VOLUME' END AS reject_reason
FROM silver_prices_typed
WHERE dup_seq > 1 OR close IS NULL OR close <= 0 OR volume < 0;

CREATE OR REFRESH MATERIALIZED VIEW silver_index_events (
  CONSTRAINT clean_ticker EXPECT (ticker RLIKE '^[A-Z][A-Z0-9.]*$') ON VIOLATION DROP ROW
)
COMMENT 'Index changes conformed to market-data naming (symbol -> ticker, trimmed, upper case)'
AS SELECT upper(trim(symbol)) AS ticker, symbol AS symbol_as_received,
  CAST(effective_date AS DATE) AS effective_date, CAST(announcement_date AS DATE) AS announcement_date,
  CAST(reference_date AS DATE) AS reference_date, event_type, action, CAST(weight_after AS DOUBLE) AS weight_after
FROM bronze_index_history;

CREATE OR REFRESH MATERIALIZED VIEW silver_etf_aum
COMMENT 'Monthly assets per product tracking the index'
AS SELECT CAST(as_of_date AS DATE) AS as_of_date, product_code, product_name, CAST(aum_usd AS DOUBLE) AS aum_usd
FROM bronze_etf_aum;
