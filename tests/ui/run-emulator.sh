#!/usr/bin/env bash
set -euo pipefail
package=br.com.trackfit.piloto
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
adb shell pm grant "$package" android.permission.POST_NOTIFICATIONS
adb shell am start -W -n "$package/br.com.trackfit.MainActivity"
node tests/ui/emulator.cjs
