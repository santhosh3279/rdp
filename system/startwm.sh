#!/bin/sh
# xrdp session dispatcher, installed by kiosk-admin.
# The distribution original is preserved as /etc/xrdp/startwm.sh.orig.
if [ -r /etc/profile ]; then
    . /etc/profile
fi

# Members of "kioskusers" get the locked-down browser kiosk
if id -nG "$(id -un)" | tr ' ' '\n' | grep -qx kioskusers; then
    exec /usr/local/bin/kiosk-session.sh
fi

# Everyone else (admins, developers) gets a normal desktop session
if [ -r /etc/default/locale ]; then
    . /etc/default/locale
    export LANG LANGUAGE
fi
exec /bin/sh /etc/X11/Xsession
