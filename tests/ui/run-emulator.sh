#!/usr/bin/env bash
set -euo pipefail
package=br.com.trackfit.piloto
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
adb shell pm grant "$package" android.permission.POST_NOTIFICATIONS
adb shell am start -W -n "$package/br.com.trackfit.MainActivity"
docker run -d --name trackfit-emulator-api -p 127.0.0.1:8032:8000 trackfit-test
trap 'docker rm -f trackfit-emulator-api trackfit-emulator-restored >/dev/null 2>&1 || true' EXIT
for attempt in {1..30}; do
  if curl -fsS http://127.0.0.1:8032/health >/dev/null; then break; fi
  sleep 1
done
TRACKFIT_TEST_CODE=$(docker exec trackfit-emulator-api python -m server.bootstrap --name TreinadorTeste | tail -1)
export TRACKFIT_TEST_CODE
adb reverse tcp:8032 tcp:8032
node tests/ui/emulator.cjs
