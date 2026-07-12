#!/bin/bash
# Firefox kiosk loop: respawns the browser whenever it exits or is killed.
# "Reset" from the admin console simply kills the browser; this loop brings
# it back with a fresh profile (when KIOSK_FRESH_PROFILE=yes).
#
# Each URL in KIOSK_URLS opens as one tab. userChrome.css strips the UI down
# to just the tab strip -- no address bar, no toolbars, no window buttons.
[ -r /etc/kiosk/kiosk.conf ] && . /etc/kiosk/kiosk.conf

# KIOSK_URL kept for configs written by v1.0
URLS="${KIOSK_URLS:-${KIOSK_URL:-https://example.com}}"

# NOT a dot-dir: snap-packaged Firefox (Ubuntu) may not read hidden dirs in $HOME
PROFILE="$HOME/kiosk-profile"
mkdir -p "$HOME/.kiosk"

USER_NAME="$(id -un)"

# touch mode: global config or per-user "kiosktouch" group membership.
# Re-evaluated on EVERY browser launch, so the admin console's per-user
# toggle applies on "Reset browser" -- no re-login needed.
apply_touch() {
    TOUCH="${KIOSK_TOUCH_MODE:-no}"
    id -nG | tr ' ' '\n' | grep -qx kiosktouch && TOUCH="yes"
    if [ "$TOUCH" = "yes" ]; then
        # touch input handling in Firefox
        export MOZ_USE_XINPUT2=1
        # invisible pointer: a fully transparent cursor THEME, so the pointer
        # stays hidden even while it moves (each touch moves it -- idle-based
        # hiders like unclutter would flash it on every tap, esp. over RDP)
        export XCURSOR_THEME=kiosk-transparent
        # belt and braces: also hide the idle pointer outside the browser
        if ! pgrep -u "$USER_NAME" -x unclutter >/dev/null 2>&1; then
            unclutter --timeout 0 --start-hidden --fork 2>/dev/null \
                || unclutter -idle 0 -root >/dev/null 2>&1 &
        fi
    else
        unset MOZ_USE_XINPUT2 XCURSOR_THEME
        pkill -u "$USER_NAME" -x unclutter 2>/dev/null || true
    fi
}

BROWSER=""
for c in firefox firefox-esr; do
    if command -v "$c" >/dev/null 2>&1; then
        BROWSER="$c"
        break
    fi
done
if [ -z "$BROWSER" ]; then
    echo "kiosk: no firefox binary found" >>"$HOME/.kiosk/browser.log"
    sleep 30
    exit 1
fi

# saved website logins survive profile wipes: logins.json holds the entries,
# key4.db the key that decrypts them -- both are needed
LOGIN_STORE="$HOME/.kiosk/logins"

save_logins() {
    [ -f "$PROFILE/logins.json" ] || return 0
    mkdir -p "$LOGIN_STORE"
    cp -f "$PROFILE/logins.json" "$LOGIN_STORE/" 2>/dev/null || true
    cp -f "$PROFILE/key4.db"     "$LOGIN_STORE/" 2>/dev/null || true
}

restore_logins() {
    [ -f "$LOGIN_STORE/logins.json" ] || return 0
    cp -f "$LOGIN_STORE/logins.json" "$PROFILE/" 2>/dev/null || true
    cp -f "$LOGIN_STORE/key4.db"     "$PROFILE/" 2>/dev/null || true
}

build_profile() {
    # admin "Reset" drops this flag to force a wipe even when
    # KIOSK_FRESH_PROFILE=no (persistent website logins, the default)
    FRESH="${KIOSK_FRESH_PROFILE:-no}"
    if [ -f "$HOME/.kiosk/force-fresh" ]; then
        FRESH="yes"
        rm -f "$HOME/.kiosk/force-fresh"
    fi
    if [ "$FRESH" = "yes" ]; then
        [ "${KIOSK_SAVE_LOGINS:-yes}" = "yes" ] && save_logins
        rm -rf "$PROFILE"
    fi
    mkdir -p "$PROFILE/chrome"
    [ "${KIOSK_SAVE_LOGINS:-yes}" = "yes" ] && restore_logins
    # UI skin + prefs are system-managed: refreshed on every launch so
    # upgrades to /etc/kiosk/* take effect at the next browser start
    cp /etc/kiosk/userChrome.css "$PROFILE/chrome/userChrome.css" 2>/dev/null || true
    cp /etc/kiosk/firefox-user.js "$PROFILE/user.js" 2>/dev/null || true
    # the N default tabs are permanent (no close button); tabs opened from
    # links land after them (insertAfterCurrent=false) and stay closeable
    NTABS=$(echo "$URLS" | wc -w)
    cat >>"$PROFILE/chrome/userChrome.css" <<EOF

/* generated: KIOSK_URLS has $NTABS tabs */
.tabbrowser-tab:nth-child(-n+$NTABS) .tab-close-button {
    display: none !important;
}
EOF
    if [ "${KIOSK_SAVE_LOGINS:-yes}" = "yes" ]; then
        echo 'user_pref("signon.rememberSignons", true);' >>"$PROFILE/user.js"
    else
        echo 'user_pref("signon.rememberSignons", false);' >>"$PROFILE/user.js"
    fi
    if [ "$TOUCH" = "yes" ]; then
        cat >>"$PROFILE/chrome/userChrome.css" <<'EOF'

/* generated: touch mode -- finger-sized tab strip */
.tabbrowser-tab {
    min-height: 44px !important;
}
.tab-close-button {
    width: 28px !important;
    height: 28px !important;
}
EOF
        echo 'user_pref("apz.allow_zooming", true);' >>"$PROFILE/user.js"
        echo 'user_pref("dom.w3c_touch_events.enabled", 1);' >>"$PROFILE/user.js"
    fi
}

while true; do
    apply_touch
    build_profile
    # shellcheck disable=SC2086
    "$BROWSER" --profile "$PROFILE" --no-remote --new-instance $URLS \
        >"$HOME/.kiosk/browser.log" 2>&1
    sleep "${KIOSK_RESTART_DELAY:-2}"
done
