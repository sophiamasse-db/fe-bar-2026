#!/usr/bin/env bash
# Demo / P10: land the held-back trading days like the vendor would - data files first, manifests LAST.
# The nextdaq_rebalance_cycle job has a file-arrival trigger on landing/price_manifests/, so it starts on its own.
set -eo pipefail
PROFILE="${DATABRICKS_PROFILE:-fe-bar-2026}"
L="dbfs:/Volumes/fe_bar_2026_kelemen_catalog/nextdaq_index/landing"
TMP=$(mktemp -d)
databricks fs cp -r "$L/holdback" "$TMP/holdback" -p "$PROFILE" >/dev/null
for f in "$TMP"/holdback/prices/*/*.csv; do
  m=$(basename "$(dirname "$f")")
  databricks fs cp "$f" "$L/prices/$m/$(basename "$f")" -p "$PROFILE" && echo "landed data  $(basename "$f")"
done
for f in "$TMP"/holdback/price_manifests/*.json; do
  databricks fs cp "$f" "$L/price_manifests/$(basename "$f")" -p "$PROFILE" && echo "landed manifest $(basename "$f")"
done
date -u +"landed at %Y-%m-%dT%H:%M:%SZ"
rm -rf "$TMP"
