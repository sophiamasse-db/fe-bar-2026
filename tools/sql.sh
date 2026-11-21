#!/usr/bin/env bash
# Run one SQL statement on the bundle's warehouse and print a Markdown table. Usage: tools/sql.sh "<sql>"
set -euo pipefail
PROFILE="${DATABRICKS_PROFILE:-fe-bar-2026}"; WH="${WAREHOUSE_ID:-0b1ef599493d9600}"
python3 -c 'import json,sys;print(json.dumps({"warehouse_id":sys.argv[1],"statement":sys.argv[2],"wait_timeout":"50s","on_wait_timeout":"CONTINUE","catalog":"fe_bar_2026_kelemen_catalog","schema":"nextdaq_index"}))' "$WH" "$1" > /tmp/_stmt.json
R=$(databricks api post /api/2.0/sql/statements --json @/tmp/_stmt.json -p "$PROFILE")
ID=$(echo "$R" | python3 -c 'import sys,json;print(json.load(sys.stdin)["statement_id"])')
while echo "$R" | python3 -c 'import sys,json;s=json.load(sys.stdin)["status"]["state"];sys.exit(0 if s in("PENDING","RUNNING") else 1)'; do
  sleep 3; R=$(databricks api get /api/2.0/sql/statements/$ID -p "$PROFILE"); done
echo "$R" | python3 -c '
import sys,json
r=json.load(sys.stdin); st=r["status"]
if st["state"]!="SUCCEEDED": print("ERROR:", st.get("error",{}).get("message","")[:800]); sys.exit(1)
cols=[c["name"] for c in r["manifest"]["schema"]["columns"]]; rows=r.get("result",{}).get("data_array",[]) or []
print("| "+" | ".join(cols)+" |"); print("|"+"---|"*len(cols))
for row in rows: print("| "+" | ".join("" if v is None else str(v) for v in row)+" |")'
