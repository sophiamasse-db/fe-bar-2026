#!/usr/bin/env bash
# Non-admin access test (FE Bar P05). Grants TEMPORARY read on the approved tables to the Client Services service
# principal, runs the nextdaq_access_test job AS that principal, then revokes and prints the effective grants.
set -eo pipefail
cd "$(dirname "$0")/.."
SP="${TESTER_SP:-ecdea4a2-ebe7-45a1-ae4e-e00598744b5c}"
S="fe_bar_2026_kelemen_catalog.nextdaq_index"
q(){ echo "> $1"; tools/sql.sh "$1" | tail -n +3; }
q "MERGE INTO $S.entitlements t USING (SELECT '$SP' AS principal) s ON t.principal = s.principal
   WHEN MATCHED THEN UPDATE SET persona='CLIENT_SERVICES', sector_scope='ALL', can_see_mnpi=false, can_approve=false, updated_at=current_timestamp()
   WHEN NOT MATCHED THEN INSERT (principal, persona, sector_scope, can_see_mnpi, can_approve, updated_at) VALUES ('$SP','CLIENT_SERVICES','ALL',false,false,current_timestamp())"
q "CREATE TABLE IF NOT EXISTS $S.zz_access_probe COMMENT 'Harmless probe: same (no) grants as the protected table' AS SELECT 1 AS x"
echo "== GRANT (temporary)"
for g in "USE CATALOG ON CATALOG fe_bar_2026_kelemen_catalog" "USE SCHEMA ON SCHEMA $S" \
         "READ VOLUME ON VOLUME $S.code" "SELECT ON TABLE $S.gold_universe_monthly" \
         "SELECT ON TABLE $S.gold_recon_predictions" "SELECT ON TABLE $S.gold_scenario_briefs"; do
  q "GRANT $g TO \`$SP\`"; done
echo "== RUN as service principal"
databricks bundle run nextdaq_access_test -p "${DATABRICKS_PROFILE:-fe-bar-2026}" 2>&1 | grep -E "TERMINATED|FAILED" || true
echo "== REVOKE"
for g in "SELECT ON TABLE $S.gold_scenario_briefs" "SELECT ON TABLE $S.gold_recon_predictions" \
         "SELECT ON TABLE $S.gold_universe_monthly" "READ VOLUME ON VOLUME $S.code" \
         "USE SCHEMA ON SCHEMA $S" "USE CATALOG ON CATALOG fe_bar_2026_kelemen_catalog"; do
  q "REVOKE $g FROM \`$SP\`"; done
echo "== Remaining grants for the service principal on the schema's tables (expect none)"
q "SELECT count(*) AS remaining_table_grants FROM system.information_schema.table_privileges WHERE grantee = '$SP' AND table_schema = 'nextdaq_index'"
