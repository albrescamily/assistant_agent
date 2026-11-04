#!/bin/bash
# Creates the agent's read-only user. Runs after 01-schema.sql and 02-load.sql.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v ro_user="$AGENT_DB_USER" -v ro_password="$AGENT_DB_PASSWORD" -v db="$POSTGRES_DB" <<'EOSQL'
CREATE ROLE :"ro_user" LOGIN PASSWORD :'ro_password';
GRANT CONNECT ON DATABASE :"db" TO :"ro_user";
GRANT USAGE ON SCHEMA public TO :"ro_user";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO :"ro_user";
-- tables created later are readable too
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO :"ro_user";
EOSQL
