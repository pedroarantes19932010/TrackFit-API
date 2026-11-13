#!/bin/sh
# Execute no host Docker com restic e um repositório remoto inicializado.
set -eu
: "${RESTIC_REPOSITORY:?Configure um destino remoto restic}"
: "${RESTIC_PASSWORD_FILE:?Configure o arquivo privado da senha}"
umask 077
cd "$(dirname "$0")"
work=$(mktemp -d)
remote="/tmp/trackfit-backup-$(basename "$work").sqlite3"
cleanup() { docker compose exec -T api rm -f "$remote" || true; rm -rf "$work"; }
trap cleanup EXIT
docker compose exec -T api python -m server.backup /data/trackfit.sqlite3 "$remote"
docker compose cp "api:$remote" "$work/trackfit.sqlite3"
restic backup --stdin --stdin-filename trackfit.sqlite3 --tag trackfit <"$work/trackfit.sqlite3"
restic check
