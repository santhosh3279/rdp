#!/bin/bash
# Kiosk X session, launched by /etc/xrdp/startwm.sh for members of kioskusers.
# Starts: per-session x11vnc (for admin mirroring), a minimal WM, and the
# browser kiosk loop. The session lives until the admin console logs it out.
[ -r /etc/kiosk/kiosk.conf ] && . /etc/kiosk/kiosk.conf

mkdir -p "$HOME/.kiosk"

xsetroot -solid "${KIOSK_BG:-#1a1a2e}" 2>/dev/null || true

# Snap-packaged Firefox (Ubuntu) cannot read the hidden ~/.Xauthority cookie
# file, so grant X access by local user identity instead -- without this the
# browser dies with "Authorization required ... cannot open display"
xhost +si:localuser:"$(id -un)" >/dev/null 2>&1 || true

# Display :N is mirrored on localhost port 5900+N; the admin app's websocket
# bridge is the only way in from outside.
DNUM="${DISPLAY#:}"
DNUM="${DNUM%%.*}"
x11vnc -display "$DISPLAY" -auth "${XAUTHORITY:-$HOME/.Xauthority}" \
       -localhost -rfbport "$((5900 + DNUM))" -shared -forever -nopw \
       -quiet -bg -o "$HOME/.kiosk/x11vnc.log" 2>/dev/null || true

# Minimal window manager; kiosk config = all windows undecorated + maximized,
# so the browser's tab strip sits at the very top of the screen
openbox --config-file /etc/kiosk/openbox-rc.xml 2>>"$HOME/.kiosk/session.log" &

exec /usr/local/bin/kiosk-browser.sh
