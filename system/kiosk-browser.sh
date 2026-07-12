#!/bin/bash
# Chromium kiosk loop: respawns the browser whenever it exits or is killed.
# "Full reset" from the admin console simply kills the browser; this loop
# brings it back with a fresh profile (when KIOSK_FRESH_PROFILE=yes).
[ -r /etc/kiosk/kiosk.conf ] && . /etc/kiosk/kiosk.conf

URL="${KIOSK_URL:-https://example.com}"
PROFILE="$HOME/.kiosk/profile"
mkdir -p "$HOME/.kiosk"

BROWSER=""
for c in chromium chromium-browser google-chrome; do
    if command -v "$c" >/dev/null 2>&1; then
        BROWSER="$c"
        break
    fi
done
if [ -z "$BROWSER" ]; then
    echo "kiosk: no chromium/chrome binary found" >>"$HOME/.kiosk/browser.log"
    sleep 30
    exit 1
fi

while true; do
    [ "${KIOSK_FRESH_PROFILE:-yes}" = "yes" ] && rm -rf "$PROFILE"
    "$BROWSER" \
        --kiosk \
        --no-first-run \
        --noerrdialogs \
        --disable-infobars \
        --disable-session-crashed-bubble \
        --disable-features=TranslateUI \
        --overscroll-history-navigation=0 \
        --user-data-dir="$PROFILE" \
        "$URL" >"$HOME/.kiosk/browser.log" 2>&1
    sleep "${KIOSK_RESTART_DELAY:-2}"
done
