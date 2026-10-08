#!/usr/bin/env sh
# Create deploy/compose/.env from .env.example, replacing __GENERATE__ with random secrets.
# Does nothing if .env already exists.
set -eu
cd "$(dirname "$0")"

if [ -f .env ]; then
  echo ".env already exists; leaving it unchanged"
  exit 0
fi

gen() { LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c "$1"; }

: > .env
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in
    KIBANA_ENCRYPTION_KEY=__GENERATE__) echo "KIBANA_ENCRYPTION_KEY=$(gen 48)" >> .env ;;
    *=__GENERATE__) echo "${line%%=*}=$(gen 24)" >> .env ;;
    *) echo "$line" >> .env ;;
  esac
done < .env.example
chmod 600 .env
echo "created deploy/compose/.env (Kibana login: elastic / ELASTIC_PASSWORD in .env)"
