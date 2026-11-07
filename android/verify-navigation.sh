#!/usr/bin/env bash
set +e
gradle connectedDebugAndroidTest --stacktrace
result=$?
adb pull /sdcard/Pictures/DXTalker-verification screenshots
exit "$result"
