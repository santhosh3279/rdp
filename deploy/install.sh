#!/bin/bash
# kiosk-admin installer AND upgrader -- idempotent by design.
#
#   Fresh install : sudo bash deploy/install.sh
#   Upgrade       : unpack/pull the new version, run the same command again.
#
# What survives an upgrade untouched:
#   /etc/kiosk/kiosk.conf        (kiosk URL & behavior)
#   /etc/kiosk-admin/*           (admin password, cookie secret, TLS certs)
#   All kiosk user accounts and their live RDP sessions (xrdp is not restarted)
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "run as root: sudo bash deploy/install.sh" >&2
    exit 1
fi

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(cat "$SRC/VERSION")"
APP_DIR=/opt/kiosk-admin
CONF_DIR=/etc/kiosk-admin

OLD_VERSION="none"
[[ -f "$APP_DIR/VERSION" ]] && OLD_VERSION="$(cat "$APP_DIR/VERSION")"
echo "== kiosk-admin: installing $VERSION (currently: $OLD_VERSION) =="

echo "-- packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -yq xrdp xorgxrdp openbox x11vnc xdotool imagemagick \
    x11-xserver-utils xdg-utils numlockx novnc python3-venv rsync openssl
apt-get install -yq unclutter-xfixes 2>/dev/null || apt-get install -yq unclutter
# server installs ship almost no fonts -- without these, websites render in
# ugly fallbacks and non-Latin text (Indic scripts, emoji, ...) shows as boxes
apt-get install -yq fontconfig fonts-liberation fonts-dejavu fonts-noto-core \
    fonts-noto-color-emoji fonts-indic
apt-get install -yq firefox-esr 2>/dev/null || apt-get install -yq firefox

echo "-- users and groups"
groupadd -f kioskusers
if ! id kioskadmin &>/dev/null; then
    useradd -r -M -d /nonexistent -s /usr/sbin/nologin kioskadmin
fi

echo "-- system scripts"
install -m 755 "$SRC/system/kiosk-session.sh"   /usr/local/bin/kiosk-session.sh
install -m 755 "$SRC/system/kiosk-browser.sh"   /usr/local/bin/kiosk-browser.sh
install -m 750 "$SRC/system/kiosk-ctl"          /usr/local/bin/kiosk-ctl
install -m 755 "$SRC/deploy/kiosk-admin-passwd" /usr/local/bin/kiosk-admin-passwd

echo "-- kiosk config (preserved on upgrade)"
mkdir -p /etc/kiosk
if [[ ! -f /etc/kiosk/kiosk.conf ]]; then
    install -m 644 "$SRC/system/kiosk.conf" /etc/kiosk/kiosk.conf
    echo "   created /etc/kiosk/kiosk.conf -- set KIOSK_URLS there"
fi

echo "-- browser skin, prefs, policies, window manager config"
install -m 644 "$SRC/system/userChrome.css"   /etc/kiosk/userChrome.css
install -m 644 "$SRC/system/firefox-user.js"  /etc/kiosk/firefox-user.js
install -m 644 "$SRC/system/openbox-rc.xml"   /etc/kiosk/openbox-rc.xml
for d in /etc/firefox/policies \
         /usr/lib/firefox-esr/distribution \
         /usr/lib/firefox/distribution; do
    mkdir -p "$d"
    install -m 644 "$SRC/system/firefox-policies.json" "$d/policies.json"
done

echo "-- xrdp session dispatcher"
if [[ -f /etc/xrdp/startwm.sh && ! -f /etc/xrdp/startwm.sh.orig ]]; then
    cp /etc/xrdp/startwm.sh /etc/xrdp/startwm.sh.orig
fi
install -m 755 "$SRC/system/startwm.sh" /etc/xrdp/startwm.sh

echo "-- web app -> $APP_DIR"
mkdir -p "$APP_DIR"
rsync -a --delete "$SRC/app/"    "$APP_DIR/app/"
rsync -a --delete "$SRC/static/" "$APP_DIR/static/"
cp "$SRC/VERSION" "$APP_DIR/VERSION"
if [[ ! -d "$APP_DIR/venv" ]]; then
    python3 -m venv "$APP_DIR/venv"
fi
"$APP_DIR/venv/bin/pip" install -q --upgrade pip
"$APP_DIR/venv/bin/pip" install -q -r "$SRC/requirements.txt"

echo "-- admin config (preserved on upgrade)"
mkdir -p "$CONF_DIR/certs"
if [[ ! -f "$CONF_DIR/secret.key" ]]; then
    openssl rand -hex 32 > "$CONF_DIR/secret.key"
fi
if [[ ! -f "$CONF_DIR/certs/cert.pem" ]]; then
    openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
        -subj "/CN=$(hostname)" \
        -keyout "$CONF_DIR/certs/key.pem" \
        -out "$CONF_DIR/certs/cert.pem" 2>/dev/null
fi
ADMIN_PW=""
if [[ ! -f "$CONF_DIR/admin.passwd" ]]; then
    ADMIN_PW="$(openssl rand -base64 12)"
    "$APP_DIR/venv/bin/python" -c '
import sys, bcrypt
print(bcrypt.hashpw(sys.argv[1].encode(), bcrypt.gensalt()).decode())
' "$ADMIN_PW" > "$CONF_DIR/admin.passwd"
fi
chown -R root:kioskadmin "$CONF_DIR"
chmod 750 "$CONF_DIR" "$CONF_DIR/certs"
chmod 640 "$CONF_DIR/secret.key" "$CONF_DIR/admin.passwd" "$CONF_DIR"/certs/*.pem

echo "-- console user store (preserved on upgrade)"
mkdir -p /var/lib/kiosk-admin
if [[ ! -f /var/lib/kiosk-admin/webusers.json ]]; then
    echo '{}' > /var/lib/kiosk-admin/webusers.json
fi
chown -R kioskadmin:kioskadmin /var/lib/kiosk-admin
chmod 700 /var/lib/kiosk-admin
chmod 600 /var/lib/kiosk-admin/webusers.json

echo "-- sudoers"
install -m 440 "$SRC/deploy/sudoers-kioskadmin" /etc/sudoers.d/kioskadmin
visudo -cf /etc/sudoers.d/kioskadmin >/dev/null

echo "-- services"
install -m 644 "$SRC/deploy/kiosk-admin.service" /etc/systemd/system/kiosk-admin.service
systemctl daemon-reload
systemctl enable xrdp >/dev/null 2>&1 || true
systemctl start xrdp 2>/dev/null || true          # never RESTARTED here: live sessions survive upgrades
systemctl enable kiosk-admin >/dev/null 2>&1
systemctl restart kiosk-admin

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo
echo "== done: kiosk-admin $VERSION =="
echo "   admin console : https://${IP:-<this-host>}:8443"
if [[ -n "$ADMIN_PW" ]]; then
    echo "   admin password: $ADMIN_PW   (change with: sudo kiosk-admin-passwd)"
else
    echo "   admin password: unchanged   (reset with: sudo kiosk-admin-passwd)"
fi
echo "   kiosk tabs    : edit KIOSK_URLS in /etc/kiosk/kiosk.conf, then 'Reset' users from the console"
echo "   RDP           : port 3389 -- kiosk users get the locked browser session"
