#!/usr/bin/env bash
set -euo pipefail
package="$PWD/dist/DXTalker-Ubuntu-amd64.deb"
settings="$HOME/.config/dxtalker"
if [[ -e "$settings" ]] || dpkg-query -s dxtalker >/dev/null 2>&1; then
  echo 'Use a clean disposable account for installer verification' >&2
  exit 1
fi
sudo apt-get install -y "$package"
test -x /opt/dxtalker/DXTalker
test -L /usr/bin/dxtalker
desktop-file-validate /usr/share/applications/dxtalker.desktop
export DXTALKER_REPORT="$PWD/ubuntu-installed-smoke.json"
dbus-run-session -- bash -euo pipefail -c '
  printf "%s" "synthetic-unlock-password" | gnome-keyring-daemon --unlock --components=secrets
  xvfb-run -a /opt/dxtalker/DXTalker --self-test "$DXTALKER_REPORT"
'
mkdir -p "$settings"
printf 'preserve' > "$settings/installer-check.txt"
sudo apt-get install --reinstall -y "$package"
test "$(cat "$settings/installer-check.txt")" = preserve
test -x /opt/dxtalker/DXTalker
sudo apt-get remove -y dxtalker
test ! -e /opt/dxtalker/DXTalker
test ! -e /usr/share/applications/dxtalker.desktop
test ! -e /usr/bin/dxtalker
test "$(cat "$settings/installer-check.txt")" = preserve
printf '{"ok":true,"install":true,"upgrade":true,"user_data_preserved":true,"remove":true}\n' > ubuntu-installer-smoke.json
