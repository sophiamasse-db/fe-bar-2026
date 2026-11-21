-- BRONZE: every source exactly as landed (all strings), plus source file and load time.
-- Incremental with Auto Loader (STREAM read_files). Column names are only renamed to snake_case.

CREATE OR REFRESH STREAMING TABLE bronze_security_master
COMMENT 'Exchange symbol directory rows as landed (public)'
AS SELECT
  `Symbol` AS symbol, `Security Name` AS security_name, `Market Category` AS market_category,
  `Test Issue` AS test_issue, `Financial Status` AS financial_status, `ETF` AS etf_flag,
  _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${landing_path}/public/security_master/', format => 'csv', sep => '|',
                       header => true, inferSchema => false);

CREATE OR REFRESH STREAMING TABLE bronze_sec_companies
COMMENT 'SEC ticker / CIK / exchange map, one row per listed line, in published order (public)'
AS SELECT pos AS sec_row_position, r[0] AS cik, r[1] AS company_name, r[2] AS ticker, r[3] AS exchange,
  _source_file, _ingested_at
FROM (
  SELECT posexplode(data) AS (pos, r), _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
  FROM STREAM read_files('${landing_path}/public/sec_companies/', format => 'json', multiLine => true,
                         schemaHints => 'data ARRAY<ARRAY<STRING>>')
);

CREATE OR REFRESH STREAMING TABLE bronze_sec_submissions
COMMENT 'SEC submissions extract: SIC industry code per filer (public)'
AS SELECT cik, name, sic, sicDescription AS sic_description, entityType AS entity_type,
  _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${landing_path}/public/sec_sic/', format => 'json',
                       schemaHints => 'cik STRING, sic STRING, sicDescription STRING');

CREATE OR REFRESH STREAMING TABLE bronze_sec_facts
COMMENT 'SEC XBRL frames: one row per filer x fact x period (shares outstanding, public float)'
AS SELECT tag, uom, ccp AS frame, d.cik, d.entityName AS entity_name, d.start AS period_start, d.end AS period_end, d.val AS value,
  d.accn AS accession, _source_file, _ingested_at
FROM (
  SELECT tag, uom, ccp, explode(data) AS d, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
  FROM STREAM read_files('${landing_path}/public/sec_facts/', format => 'json', multiLine => true,
                         schemaHints => 'data ARRAY<STRUCT<accn STRING, cik STRING, entityName STRING, loc STRING, start STRING, end STRING, val STRING>>',
                         schemaEvolutionMode => 'rescue')
);

CREATE OR REFRESH STREAMING TABLE bronze_daily_prices
COMMENT 'Market data vendor price files as landed (synthetic), all columns as strings'
AS SELECT TradeDate AS trade_date, Ticker AS ticker, Open AS open, High AS high, Low AS low, Close AS close,
  Volume AS volume, Currency AS currency,
  regexp_extract(_metadata.file_path, '([^/]+)$', 1) AS _file_name,
  _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${landing_path}/prices/', format => 'csv', header => true, inferSchema => false);

CREATE OR REFRESH STREAMING TABLE bronze_price_manifest
COMMENT 'Control totals sent by the market data vendor after each price file'
AS SELECT file_name, period, record_count, volume_total, source_system,
  _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${landing_path}/price_manifests/', format => 'json',
                       schemaHints => 'record_count BIGINT, volume_total BIGINT');

CREATE OR REFRESH STREAMING TABLE bronze_index_history
COMMENT 'Index administrator change log as landed (synthetic); uses `symbol`, not `ticker`'
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${landing_path}/index_history/', format => 'csv', header => true, inferSchema => false);

CREATE OR REFRESH STREAMING TABLE bronze_etf_aum
COMMENT 'Monthly assets of products tracking the NextDAQ-100 (synthetic), one row per product x month'
AS SELECT as_of_date, p.product_code, p.product_name, p.aum_usd, _source_file, _ingested_at
FROM (
  SELECT as_of_date, explode(products) AS p, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
  FROM STREAM read_files('${landing_path}/etf_aum/', format => 'json',
                         schemaHints => 'products ARRAY<STRUCT<product_code STRING, product_name STRING, aum_usd DOUBLE>>')
);
