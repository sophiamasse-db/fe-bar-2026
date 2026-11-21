# 06 — Unity Catalog governance

Generated 2026-11-21 17:49 UTC by tools/generate_evidence.py from the live workspace.

Proves access is enforced by the platform per persona from an entitlements table (row filter by sector, MNPI column masks, MNPI row gate), verified as my own user switched through each persona AND as a separate non-admin service principal; plus tags and lineage from system tables.

## Same query, three personas (my entitlements row switched, then restored)

| persona | sector_scope | can_see_mnpi | universe_rows | forecast_rows_visible | forecast_sectors | p_add_unmasked | action_restricted | briefs_visible |
|---|---|---|---|---|---|---|---|---|
| HEAD_OF_METHODOLOGY | ALL | True | 63944 | 1015 | 10 | 1015 | 0 | 8 |
| METHODOLOGY_ANALYST | Technology | True | 63944 | 216 | 1 | 216 | 0 | 8 |
| CLIENT_SERVICES | ALL | False | 63944 | 1015 | 10 | 0 | 1015 | 0 |

## Non-admin identity (service principal, temporary grants then revoked)

Job run 908783369469312 (SUCCESS), run_as = service principal `nextdaq-access-tester` (Client Services: no MNPI).

| check | status | result / error class |
|---|---|---|
| identity | OK | {"has_identity": true, "is_human_user": false} |
| public_gold_read | OK | {"rows": 63944} |
| forecast_rows_and_masks | OK | {"rows_visible": 1015, "p_add_not_null": 0, "action_restricted": 1015, "drivers_restricted": 1015} |
| join_on_masked_column | OK | {"likely_adds_found": 0} |
| mnpi_briefs_rows | OK | {"rows_visible": 0} |
| protected_table_read | ERROR | INSUFFICIENT_PERMISSIONS (20216 chars, content not logged) |
| probe_table_read_same_permissions | ERROR | INSUFFICIENT_PERMISSIONS (20219 chars, content not logged) |

After revoke:

| remaining_grants_for_tester |
|---|
| 0 |

## Policies attached

| table_name | policy | target_columns |
|---|---|---|
| gold_recon_predictions | fe_bar_2026_kelemen_catalog.nextdaq_index.f_sector_scope | sector |
| gold_recon_predictions | p_add <- fe_bar_2026_kelemen_catalog.nextdaq_index.f_mask_mnpi_double |  |
| gold_recon_predictions | p_remove <- fe_bar_2026_kelemen_catalog.nextdaq_index.f_mask_mnpi_double |  |
| gold_recon_predictions | predicted_action <- fe_bar_2026_kelemen_catalog.nextdaq_index.f_mask_mnpi_string |  |
| gold_recon_predictions | top_drivers <- fe_bar_2026_kelemen_catalog.nextdaq_index.f_mask_mnpi_string |  |
| gold_scenario_briefs | fe_bar_2026_kelemen_catalog.nextdaq_index.f_mnpi_gate | scenario_id |
| scenario_presets | fe_bar_2026_kelemen_catalog.nextdaq_index.f_mnpi_gate | scenario_id |

## Tags

| table_name | tag_name | tag_value |
|---|---|---|
| gold_etf_exposure | domain | finance |
| gold_etf_exposure | nextdaq_area | index_licensing |
| gold_etf_exposure | nextdaq_sensitivity | internal |
| gold_index_constituents | domain | finance |
| gold_index_constituents | nextdaq_area | index_methodology |
| gold_index_constituents | nextdaq_sensitivity | published_index_data |
| gold_recon_predictions | domain | finance |
| gold_recon_predictions | nextdaq_area | index_methodology |
| gold_recon_predictions | nextdaq_sensitivity | mnpi |
| gold_reconstitution_history | domain | finance |
| gold_reconstitution_history | nextdaq_area | index_methodology |
| gold_reconstitution_history | nextdaq_sensitivity | published_index_data |
| gold_scenario_briefs | domain | finance |
| gold_scenario_briefs | nextdaq_area | index_methodology |
| gold_scenario_briefs | nextdaq_sensitivity | mnpi |
| gold_universe_monthly | domain | finance |
| gold_universe_monthly | nextdaq_area | index_methodology |
| gold_universe_monthly | nextdaq_sensitivity | public_market_data |
| scenario_presets | domain | finance |
| scenario_presets | nextdaq_area | index_methodology |
| scenario_presets | nextdaq_sensitivity | mnpi |

## Lineage into gold (system.access.table_lineage)

| source | target | events |
|---|---|---|
| silver_etf_aum | gold_etf_exposure | 8 |
| gold_universe_monthly | gold_index_constituents | 7 |
| gold_universe_monthly | gold_reconstitution_history | 7 |
| silver_index_events | gold_reconstitution_history | 7 |
| silver_securities | gold_reconstitution_history | 7 |
| scenario_presets | gold_scenario_briefs | 5 |
| silver_index_events | gold_universe_monthly | 7 |
| silver_prices | gold_universe_monthly | 7 |
| silver_securities | gold_universe_monthly | 7 |
| silver_shares | gold_universe_monthly | 7 |
