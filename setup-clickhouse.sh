#!/usr/bin/env bash
# Dajia Talks: set up the ClickHouse Cloud backend.
#
# Usage:
#   CH_URL="https://<service>.clickhouse.cloud:8443" \
#   CH_ADMIN_USER="default" \
#   CH_ADMIN_PASSWORD="..." \
#   ./setup-clickhouse.sh
#
# Creates the dajia database + rooms table and a sandboxed `dajia_app` user
# with a freshly generated password, then prints the BACKEND config to paste
# into index.html. Admin credentials are only used here; they never go in the
# page.
set -euo pipefail

: "${CH_URL:?set CH_URL to the service HTTPS endpoint, e.g. https://xxx.clickhouse.cloud:8443}"
: "${CH_ADMIN_USER:=default}"
: "${CH_ADMIN_PASSWORD:?set CH_ADMIN_PASSWORD (the service admin password)}"

# hex core plus fixed caps/special to satisfy Cloud password policy; only
# sed- and URL-safe characters
APP_PASSWORD="DT!$(openssl rand -hex 12)x"

run_sql() {
  curl -sS --fail-with-body "$CH_URL/" \
    --user "$CH_ADMIN_USER:$CH_ADMIN_PASSWORD" \
    --data-binary "$1"
  echo
}

echo "-> creating database, table, app user..."
# The HTTP interface takes one statement per request, so split on ';'
# (comment lines stripped; the SQL contains no string literals with ';').
sed "s/{APP_PASSWORD}/$APP_PASSWORD/" "$(dirname "$0")/setup-clickhouse.sql" \
  | grep -v '^\s*--' \
  | tr '\n' ' ' \
  | tr ';' '\n' \
  | while IFS= read -r stmt; do
      if [ -n "$(echo "$stmt" | tr -d '[:space:]')" ]; then
        run_sql "$stmt"
      fi
    done

echo "-> smoke test as dajia_app..."
curl -sS --fail-with-body "$CH_URL/?add_http_cors_header=1&user=dajia_app&password=$APP_PASSWORD" \
  --data-binary "SELECT count() FROM dajia.rooms"

echo
echo "Done. Paste into index.html:"
echo "  var BACKEND = {type:\"clickhouse\", url:\"$CH_URL\", user:\"dajia_app\", pass:\"$APP_PASSWORD\"};"
