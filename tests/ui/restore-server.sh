#!/usr/bin/env bash
# Restore into a different container with a fresh writable filesystem.
set -euo pipefail
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
docker exec trackfit-emulator-api python -m server.backup /data/trackfit.sqlite3 /tmp/backup.sqlite3
docker cp trackfit-emulator-api:/tmp/backup.sqlite3 "$work/backup.sqlite3"
docker stop trackfit-emulator-api >/dev/null
docker run -d --name trackfit-emulator-restored -p 127.0.0.1:8032:8000 trackfit-test sh -c '
  until test -e /tmp/ready; do sleep 0.2; done
  exec python -m uvicorn server.app:create_app --factory --host 0.0.0.0 --port 8000 --no-access-log
' >/dev/null
docker exec -i trackfit-emulator-restored sh -c 'umask 077; cat > /data/trackfit.sqlite3 && touch /tmp/ready' < "$work/backup.sqlite3"
for attempt in {1..30}; do
  if curl -fsS http://127.0.0.1:8032/health >/dev/null 2>&1; then exit 0; fi
  sleep 1
done
exit 1
