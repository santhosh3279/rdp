#!/bin/bash
# Removes kiosk-admin. Configs and kiosk user accounts are kept unless --purge.
#   sudo bash deploy/uninstall.sh          # remove app, keep configs (easy reinstall)
#   sudo bash deploy/uninstall.sh --purge  # also remove /etc/kiosk* configs
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "run as root: sudo bash deploy/uninstall.sh" >&2
    exit 1
fi
PURGE=0
[[ "${1:-}" == "--purge" ]] && PURGE=1

systemctl disable --now kiosk-admin 2>/dev/null || true
rm -f /etc/systemd/system/kiosk-admin.service
systemctl daemon-reload

rm -f /etc/sudoers.d/kioskadmin
rm -f /usr/local/bin/kiosk-session.sh /usr/local/bin/kiosk-browser.sh \
      /usr/local/bin/kiosk-ctl /usr/local/bin/kiosk-admin-passwd
rm -rf /opt/kiosk-admin

for d in /etc/chromium/policies/managed \
         /etc/chromium-browser/policies/managed \
         /etc/opt/chrome/policies/managed; do
    rm -f "$d/kiosk-admin.json"
done

if [[ -f /etc/xrdp/startwm.sh.orig ]]; then
    mv /etc/xrdp/startwm.sh.orig /etc/xrdp/startwm.sh
fi

if [[ $PURGE -eq 1 ]]; then
    rm -rf /etc/kiosk-admin /etc/kiosk
    userdel kioskadmin 2>/dev/null || true
    echo "configs purged. Kiosk user accounts were kept; remove each with:"
    echo "  sudo userdel -r <username>"
fi

echo "kiosk-admin removed (xrdp itself was left installed)"
