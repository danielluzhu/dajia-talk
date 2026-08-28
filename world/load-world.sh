#!/usr/bin/env bash
# Loads the built world panel into ClickHouse Cloud (run build-world.js first).
#
#   CH_URL="https://<service>.clickhouse.cloud:8443" \
#   CH_ADMIN_USER="default" CH_ADMIN_PASSWORD="..." ./world/load-world.sh
set -euo pipefail
: "${CH_URL:?}"; : "${CH_ADMIN_USER:=default}"; : "${CH_ADMIN_PASSWORD:?}"
DIR="$(cd "$(dirname "$0")" && pwd)"

sql() {
  curl -sS --fail-with-body "$CH_URL/" --user "$CH_ADMIN_USER:$CH_ADMIN_PASSWORD" --data-binary "$1"
  echo
}

echo "-> tables"
sql "CREATE TABLE IF NOT EXISTS dajia.world_answers (q UInt16, name String, kind String, choice Int32, text String) ENGINE = MergeTree ORDER BY q"
sql "CREATE TABLE IF NOT EXISTS dajia.world (q UInt16, digest String) ENGINE = ReplacingMergeTree ORDER BY q"
sql "GRANT SELECT ON dajia.world TO dajia_app"
sql "GRANT SELECT ON dajia.world_answers TO dajia_app"

echo "-> reload data (idempotent)"
sql "TRUNCATE TABLE dajia.world_answers"
sql "TRUNCATE TABLE dajia.world"
curl -sS --fail-with-body "$CH_URL/?query=INSERT%20INTO%20dajia.world_answers%20FORMAT%20JSONEachRow" \
  --user "$CH_ADMIN_USER:$CH_ADMIN_PASSWORD" --data-binary @"$DIR/world_answers.jsonl"
curl -sS --fail-with-body "$CH_URL/?query=INSERT%20INTO%20dajia.world%20FORMAT%20JSONEachRow" \
  --user "$CH_ADMIN_USER:$CH_ADMIN_PASSWORD" --data-binary @"$DIR/world.jsonl"

echo "-> counts"
sql "SELECT kind, count() FROM dajia.world_answers GROUP BY kind"
sql "SELECT count() FROM dajia.world"
