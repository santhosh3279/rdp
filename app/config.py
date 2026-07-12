import os

# Overridable for development: KIOSK_ADMIN_CONF=./devconf uvicorn app.main:app
CONF_DIR = os.environ.get("KIOSK_ADMIN_CONF", "/etc/kiosk-admin")

SECRET_FILE = os.path.join(CONF_DIR, "secret.key")
ADMIN_PASSWD_FILE = os.path.join(CONF_DIR, "admin.passwd")

KIOSK_GROUP = "kioskusers"
VNC_BASE_PORT = 5900

COOKIE_NAME = "kiosk_session"
SESSION_TTL = 12 * 3600
# Cookie is Secure by default (the service runs TLS); set KIOSK_ADMIN_HTTP=1 for plain-http dev
COOKIE_SECURE = os.environ.get("KIOSK_ADMIN_HTTP") != "1"

NOVNC_DIR = "/usr/share/novnc"
SUDO = "/usr/bin/sudo"
KIOSK_CTL = "/usr/local/bin/kiosk-ctl"
