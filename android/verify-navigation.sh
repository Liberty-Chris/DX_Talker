#!/usr/bin/env bash
set +e
gradle connectedDebugAndroidTest --stacktrace
result=$?
adb pull /sdcard/Android/data/club.dxtalker.android/files/screenshots screenshots
exit "$result"
