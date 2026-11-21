-- COMPLETENESS: compare the vendor's control totals with what landed, loaded and was quarantined.

CREATE OR REFRESH MATERIALIZED VIEW recon_market_data (
  CONSTRAINT reconciled EXPECT (status = 'RECONCILED')      -- warn: a BREAK is visible, not fatal
)
COMMENT 'One row per vendor price file: control count/volume vs landed, loaded and quarantined rows'
AS WITH landed AS (
  SELECT _file_name, count(*) AS landed_rows, sum(CAST(volume AS BIGINT)) AS landed_volume
  FROM bronze_daily_prices GROUP BY _file_name
), loaded AS (
  SELECT _file_name, count(*) AS loaded_rows FROM silver_prices GROUP BY _file_name
), quarantined AS (
  SELECT _file_name, count(*) AS quarantined_rows FROM silver_prices_quarantine GROUP BY _file_name
)
SELECT m.file_name, m.period, m.record_count AS control_count, coalesce(l.landed_rows, 0) AS landed_rows,
  coalesce(ld.loaded_rows, 0) AS loaded_rows, coalesce(q.quarantined_rows, 0) AS quarantined_rows,
  m.volume_total AS control_volume, l.landed_volume,
  CASE
    WHEN l.landed_rows IS NULL THEN 'MISSING_FILE'
    WHEN l.landed_rows = m.record_count AND l.landed_volume = m.volume_total
         AND coalesce(ld.loaded_rows, 0) + coalesce(q.quarantined_rows, 0) = l.landed_rows THEN 'RECONCILED'
    ELSE 'BREAK'
  END AS status
FROM bronze_price_manifest m
LEFT JOIN landed l ON l._file_name = m.file_name
LEFT JOIN loaded ld ON ld._file_name = m.file_name
LEFT JOIN quarantined q ON q._file_name = m.file_name;
