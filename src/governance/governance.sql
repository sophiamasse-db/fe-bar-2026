-- Unity Catalog governance for the NextDAQ-100 simulator. Idempotent; run every cycle after the AI tasks.
-- Policy: public market data (gold_universe_monthly, constituents, history, ETF assets) is open to the index org.
--         Forward-looking index decisions are MNPI: add/remove forecasts and scenario briefs are limited to people
--         cleared for MNPI, and analysts see forecasts only for the sectors they cover.
-- Access is data: one row per principal in `entitlements`. Function bodies need literal object names.
-- The job owner (the Head of Methodology who runs this task) is seeded with current_user(); no emails in code.

USE CATALOG fe_bar_2026_kelemen_catalog;
USE SCHEMA nextdaq_index;

CREATE TABLE IF NOT EXISTS entitlements (
  principal STRING NOT NULL COMMENT 'User email or service principal application id (current_user())',
  persona STRING NOT NULL COMMENT 'METHODOLOGY_ANALYST | HEAD_OF_METHODOLOGY | CLIENT_SERVICES | ADMIN',
  sector_scope STRING NOT NULL COMMENT 'ALL or one sector, e.g. Technology',
  can_see_mnpi BOOLEAN NOT NULL COMMENT 'Cleared for pre-announcement (MNPI) index information',
  can_approve BOOLEAN NOT NULL COMMENT 'May approve scenarios in the app',
  updated_at TIMESTAMP
) COMMENT 'Who may see what. Access changes are row changes, not code changes.';

MERGE INTO entitlements t
USING (SELECT current_user() AS principal, 'HEAD_OF_METHODOLOGY' AS persona, 'ALL' AS sector_scope,
              true AS can_see_mnpi, true AS can_approve) s
ON t.principal = s.principal
WHEN NOT MATCHED THEN INSERT (principal, persona, sector_scope, can_see_mnpi, can_approve, updated_at)
  VALUES (s.principal, s.persona, s.sector_scope, s.can_see_mnpi, s.can_approve, current_timestamp());

CREATE OR REPLACE FUNCTION f_sector_scope(sector STRING)
RETURNS BOOLEAN
COMMENT 'Row filter: the caller covers this sector (or ALL)'
RETURN EXISTS (SELECT 1 FROM fe_bar_2026_kelemen_catalog.nextdaq_index.entitlements e
               WHERE e.principal = current_user() AND (e.sector_scope = 'ALL' OR e.sector_scope = sector));

CREATE OR REPLACE FUNCTION f_mnpi_gate(any_key STRING)
RETURNS BOOLEAN
COMMENT 'Row filter: the caller is cleared for MNPI'
RETURN EXISTS (SELECT 1 FROM fe_bar_2026_kelemen_catalog.nextdaq_index.entitlements e
               WHERE e.principal = current_user() AND e.can_see_mnpi);

CREATE OR REPLACE FUNCTION f_mask_mnpi_double(v DOUBLE)
RETURNS DOUBLE
COMMENT 'Column mask: NULL unless the caller is cleared for MNPI'
RETURN CASE WHEN EXISTS (SELECT 1 FROM fe_bar_2026_kelemen_catalog.nextdaq_index.entitlements e
                         WHERE e.principal = current_user() AND e.can_see_mnpi) THEN v END;

CREATE OR REPLACE FUNCTION f_mask_mnpi_string(v STRING)
RETURNS STRING
COMMENT 'Column mask: RESTRICTED unless the caller is cleared for MNPI'
RETURN CASE WHEN EXISTS (SELECT 1 FROM fe_bar_2026_kelemen_catalog.nextdaq_index.entitlements e
                         WHERE e.principal = current_user() AND e.can_see_mnpi) THEN v ELSE 'RESTRICTED' END;

-- Forecast: sector-scoped rows, MNPI columns masked for anyone not cleared
ALTER TABLE gold_recon_predictions SET ROW FILTER f_sector_scope ON (sector);
ALTER TABLE gold_recon_predictions ALTER COLUMN p_add SET MASK f_mask_mnpi_double;
ALTER TABLE gold_recon_predictions ALTER COLUMN p_remove SET MASK f_mask_mnpi_double;
ALTER TABLE gold_recon_predictions ALTER COLUMN predicted_action SET MASK f_mask_mnpi_string;
ALTER TABLE gold_recon_predictions ALTER COLUMN top_drivers SET MASK f_mask_mnpi_string;

-- Scenario facts and AI briefs: whole rows are MNPI
ALTER TABLE gold_scenario_briefs SET ROW FILTER f_mnpi_gate ON (scenario_id);
ALTER TABLE scenario_presets SET ROW FILTER f_mnpi_gate ON (scenario_id);

-- Tags and business descriptions
ALTER TABLE gold_recon_predictions SET TAGS ('nextdaq_sensitivity' = 'mnpi', 'domain' = 'finance', 'nextdaq_area' = 'index_methodology');
ALTER TABLE gold_scenario_briefs SET TAGS ('nextdaq_sensitivity' = 'mnpi', 'domain' = 'finance', 'nextdaq_area' = 'index_methodology');
ALTER TABLE scenario_presets SET TAGS ('nextdaq_sensitivity' = 'mnpi', 'domain' = 'finance', 'nextdaq_area' = 'index_methodology');
ALTER TABLE gold_recon_predictions ALTER COLUMN p_add SET TAGS ('mnpi' = 'true');
ALTER TABLE gold_recon_predictions ALTER COLUMN p_remove SET TAGS ('mnpi' = 'true');
ALTER TABLE gold_recon_predictions ALTER COLUMN predicted_action SET TAGS ('mnpi' = 'true');
ALTER TABLE gold_universe_monthly SET TAGS ('nextdaq_sensitivity' = 'public_market_data', 'domain' = 'finance', 'nextdaq_area' = 'index_methodology');
ALTER TABLE gold_index_constituents SET TAGS ('nextdaq_sensitivity' = 'published_index_data', 'domain' = 'finance', 'nextdaq_area' = 'index_methodology');
ALTER TABLE gold_reconstitution_history SET TAGS ('nextdaq_sensitivity' = 'published_index_data', 'domain' = 'finance', 'nextdaq_area' = 'index_methodology');
ALTER TABLE gold_etf_exposure SET TAGS ('nextdaq_sensitivity' = 'internal', 'domain' = 'finance', 'nextdaq_area' = 'index_licensing');

COMMENT ON COLUMN gold_recon_predictions.p_add IS 'Probability the security is ADDED at the next reconstitution (non-members). MNPI.';
COMMENT ON COLUMN gold_recon_predictions.p_remove IS 'Probability the security is REMOVED at the next reconstitution (members). MNPI.';
COMMENT ON COLUMN gold_recon_predictions.predicted_action IS 'ADD / REMOVE / HOLD at the cross-validated thresholds. MNPI.';
COMMENT ON COLUMN gold_recon_predictions.top_drivers IS 'Plain-language reasons: rank vs the 90 add / 110 keep bands, momentum, liquidity.';
COMMENT ON COLUMN gold_universe_monthly.mcap_rank IS 'Rank by market cap among eligible securities on the snapshot date (1 = largest).';
COMMENT ON COLUMN gold_universe_monthly.ranks_from_cutoff IS 'mcap_rank - 100; negative = inside the top 100.';
COMMENT ON COLUMN gold_universe_monthly.adv_usd_3m IS '3-month average daily value traded in USD (liquidity).';
COMMENT ON COLUMN gold_universe_monthly.in_index IS 'Member of the NextDAQ-100 on the snapshot date.';
COMMENT ON COLUMN gold_index_constituents.weight IS 'Capped index weight (0-1) for the current baseline.';
COMMENT ON COLUMN gold_etf_exposure.total_aum_usd IS 'Assets of all products tracking the index on that date (USD).';

SELECT 'governance applied' AS status;
