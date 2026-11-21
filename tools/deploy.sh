#!/usr/bin/env bash
# Deploy the bundle, then sync job source code into the UC `code` volume.
# Jobs run code from the volume because serverless reads of bundle workspace files were unreliable here.
set -euo pipefail
PROFILE="${DATABRICKS_PROFILE:-fe-bar-2026}"
CODE_VOL="/Volumes/fe_bar_2026_kelemen_catalog/nextdaq_index/code"
cd "$(dirname "$0")/.."
databricks bundle deploy -p "$PROFILE"
for d in data app ai serve governance; do
  [ -d "src/$d" ] || continue
  databricks fs cp -r --overwrite "src/$d" "dbfs:$CODE_VOL/src/$d" -p "$PROFILE" >/dev/null
done
echo "Synced src/ to $CODE_VOL/src"
