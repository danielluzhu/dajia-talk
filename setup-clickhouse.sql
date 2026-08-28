-- Dajia Talks: ClickHouse Cloud backend setup.
-- Run as an admin user (setup-clickhouse.sh does this for you).
-- {APP_PASSWORD} is substituted by the setup script.

CREATE DATABASE IF NOT EXISTS dajia;

-- One row per save; ReplacingMergeTree keeps the newest row per room id,
-- and the app reads with FINAL so it always sees the latest save.
CREATE TABLE IF NOT EXISTS dajia.rooms
(
    id      String,
    data    String,
    updated DateTime64(3) DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(updated)
ORDER BY id;

-- The sandboxed user embedded in the public page. It can only read and append
-- rooms — no ALTER, DROP, TRUNCATE, or access to anything else.
CREATE USER IF NOT EXISTS dajia_app IDENTIFIED BY '{APP_PASSWORD}'
    SETTINGS max_result_rows = 100 READONLY,
             max_execution_time = 10 READONLY,
             max_query_size = 1048576 READONLY;

GRANT SELECT, INSERT ON dajia.rooms TO dajia_app;

-- Per-day discussion threads ("Table talk"): append-only, one row per message.
CREATE TABLE IF NOT EXISTS dajia.chat
(
    room   String,
    day    String,
    id     String,
    member String,
    text   String,
    at     DateTime64(3) DEFAULT now64(3)
)
ENGINE = MergeTree
ORDER BY (room, day, at);

GRANT SELECT, INSERT ON dajia.chat TO dajia_app;

-- Keep a runaway client (or a vandal who reads the page source) rate-limited.
CREATE QUOTA IF NOT EXISTS dajia_app_quota
    KEYED BY ip_address
    FOR INTERVAL 1 hour MAX queries = 3000
    TO dajia_app;
