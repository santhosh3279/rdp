# kiosk-admin — RDP browser-kiosk server with a web management console

Turns an Ubuntu/Debian machine into a multi-user RDP kiosk server:

- Users connect over **RDP (port 3389)** and get a **locked-down browser with a
  fixed set of tabs (5 by default)** — the tab strip at the top of the screen is
  the *only* visible UI: no address bar, no menus, no settings, no devtools,
  no downloads.
- Admins open the **web console (https://server:8443)** to:
  - see every logged-in session at a glance (lightweight "online" cards —
    no screenshot polling, so the dashboard costs almost no bandwidth)
  - **mirror and control** any user's screen in the browser (noVNC)
  - **hard-refresh** a user's page (Ctrl+Shift+R) or **reset** their browser
    (kill + relaunch with a clean profile)
  - **add / delete kiosk users** and set passwords
  - **log out** any session
  - manage **console accounts with roles**: `admin` (full control) or
    `viewer` (watch & control screens only — no user management, no
    refresh/reset/logout; enforced server-side)

## Architecture

```
RDP clients ──► xrdp ──► per-user Xorg session (:10, :11, …)
                              ├─► Firefox, tab-strip-only UI (respawn loop = self-healing)
                              └─► x11vnc on 127.0.0.1:59<display> (mirroring)

Admin browser ──► kiosk-admin (FastAPI, TLS :8443, runs as "kioskadmin")
                     ├─ /api/sessions        list sessions (Xorg process scan)
                     ├─ /api/users           add/delete users, set passwords
                     ├─ /api/sessions/…      refresh / reset / logout / screenshot
                     └─ /ws/vnc/<user>       websocket bridge → x11vnc → noVNC UI
```

Every privileged operation goes through **one** root helper, `kiosk-ctl`,
allowed by **one** sudoers line. The helper validates usernames and refuses to
touch accounts outside the `kioskusers` group. VNC never leaves localhost; the
only ways in are RDP (3389) and the authenticated admin console (8443).

## Install

On the target machine (Ubuntu 22.04/24.04 or Debian 12):

```sh
git clone <this-repo> kiosk-admin && cd kiosk-admin   # or unpack the tarball
sudo bash deploy/install.sh
```

(`make install` does the same if you have `make`; fresh servers usually don't.)

The installer prints the admin console URL and a **generated admin password**
— save it, or set your own right away:

```sh
sudo kiosk-admin-passwd
```

Then set the kiosk tabs in `/etc/kiosk/kiosk.conf` (`KIOSK_URLS="url1 url2 …"`,
one URL per tab, 5 by default), open `https://<server>:8443`, and click
**+ Add user**. That user can immediately log in with any RDP client and lands
in the browser kiosk.

The TLS certificate is self-signed by default (browser warning is expected);
drop real certs into `/etc/kiosk-admin/certs/{cert.pem,key.pem}` and
`sudo systemctl restart kiosk-admin` to replace them.

## Upgrade = reinstall

The installer is idempotent — upgrading is just running it again with newer
sources:

```sh
git pull                      # or unpack the new tarball over this directory
sudo bash deploy/install.sh   # or: make upgrade
```

Guaranteed to survive an upgrade untouched:

| What | Where |
|---|---|
| Kiosk URL & behavior | `/etc/kiosk/kiosk.conf` (never overwritten) |
| Admin password, cookie secret, TLS certs | `/etc/kiosk-admin/` (never overwritten) |
| Kiosk user accounts & home dirs | normal system users |
| **Live RDP sessions** | xrdp is never restarted by the installer |

What the upgrade replaces: the web app in `/opt/kiosk-admin/`, the scripts in
`/usr/local/bin/`, `/etc/xrdp/startwm.sh`, Firefox policies/skin/prefs, the
systemd unit, and python dependencies inside the venv. Only the admin console service
restarts (a second or two of downtime for admins; users notice nothing).
Session scripts take effect on each user's *next* login.

To ship a version to an offline machine: bump `VERSION`, run `make package`,
copy the tarball, unpack, `make install`.

## Uninstall

```sh
sudo bash deploy/uninstall.sh           # removes app + scripts, KEEPS configs
sudo bash deploy/uninstall.sh --purge   # also removes /etc/kiosk and /etc/kiosk-admin
```

(`make uninstall` / `make purge` are equivalent.)

Kiosk user accounts are never deleted automatically; remove them per-user
with `sudo userdel -r <name>` (or from the web UI before uninstalling).

## Repository layout

```
app/                 FastAPI backend (auth, sessions, users, control, VNC bridge)
static/              Admin UI (dashboard, noVNC viewer) — no build step
system/              Target-machine pieces: startwm.sh, kiosk session/browser
                     scripts, kiosk-ctl root helper, kiosk.conf, Firefox
                     policies + userChrome.css (tab-strip-only UI), openbox config
deploy/              install.sh / uninstall.sh, systemd unit, sudoers,
                     kiosk-admin-passwd
docs/                Installation & user guide: kiosk-admin-guide.pdf
                     (source: guide.html — regenerate with `make pdf`)
Makefile             install / upgrade / uninstall / purge / package / pdf
VERSION              single source of truth for the release version
```

## How the moving parts fit

- **Session start**: xrdp runs `/etc/xrdp/startwm.sh`; members of `kioskusers`
  are dispatched to `kiosk-session.sh` (everyone else still gets a normal
  desktop). The session script starts x11vnc on `127.0.0.1:5900+display`,
  a minimal openbox, then `exec`s the browser loop.
- **Self-healing browser**: `kiosk-browser.sh` relaunches Firefox whenever it
  exits, opening one tab per URL in `KIOSK_URLS`. The profile persists by
  default (`KIOSK_FRESH_PROFILE=no`), so users **stay signed in to websites**
  across browser restarts and RDP logins/logouts; set `yes` to wipe it on
  every launch instead. "Reset" from the console always wipes — clearing
  cookies/history, restoring the full tab set, and any wedged state.
- **Saved website logins** (`KIOSK_SAVE_LOGINS=yes`, the default): Firefox
  offers to save passwords for the kiosk sites (the "Save login?" popup shows
  just below the tab strip after signing in), and the launch script carries
  `logins.json` + `key4.db` across profile wipes — so saved logins survive
  browser restarts and admin Resets while everything else stays disposable.
  Set to `no` to forbid password saving entirely. The nav bar is squashed to
  1px rather than hidden precisely for this: Firefox suppresses the popup if
  its toolbar anchor is invisible (fixed in v1.8.1).
- **Tab-strip-only UI**: `userChrome.css` (copied into each profile at launch)
  collapses the address bar, toolbars, window buttons, and the new-tab (+)
  button; `firefox-user.js` merges tabs into the titlebar and openbox renders
  the window undecorated and maximized — so the tabs are the topmost pixels on
  the screen and nothing else is reachable. Firefox enterprise policies
  additionally disable devtools, private browsing, about:config, and password
  saving.
- **Touch-screen mode**: hides the mouse pointer on the kiosk screen with a
  fully **transparent cursor theme** — invisible even while the pointer moves
  (idle-hiders like unclutter flash the cursor on every tap; unclutter still
  runs as a fallback), enables Firefox touch input handling
  (`MOZ_USE_XINPUT2`, touch events, pinch zoom), and enlarges the tab strip
  to finger size. Enabled
  globally (`KIOSK_TOUCH_MODE=yes`) or per user via the "Touch screen"
  checkbox in the console or the live viewer's toolbar (= `kiosktouch` group
  membership). Touch state is re-evaluated on every browser launch, so a
  toggle applies on Reset — no re-login needed. The live viewer additionally
  has its own "touch screen" checkbox for admins mirroring *from* a touch
  device (finger-sized toolbar + dot cursor).
- **Permanent vs link-opened tabs**: the launch script appends a generated CSS
  rule hiding the close button on the first N tab positions (N = the
  `KIOSK_URLS` count), and prefs force link-opened tabs to always append
  *after* the defaults — so the default tabs are permanent while tabs the user
  opens by clicking links keep a close button and can be dismissed normally.
- **Refresh vs Reset**: *Refresh* injects Ctrl+Shift+R via `xdotool` (run as
  the session user, so X authentication is a non-issue). *Reset* kills the
  browser and lets the loop respawn it clean — it always wipes the profile,
  even with `KIOSK_FRESH_PROFILE=no` (persistent website logins), via a
  force-fresh flag dropped by `kiosk-ctl`.
- **Mirroring**: session cards are plain "online" tiles (no screenshot
  polling — bandwidth and server CPU stay flat as sessions grow);
  clicking a card opens the noVNC viewer, which speaks RFB over
  `/ws/vnc/<user>` — a websocket↔TCP bridge inside the app, protected by the
  same login cookie. A "view only" toggle switches between watching and
  controlling.
- **noVNC** comes from the distro package (`/usr/share/novnc`), so it gets
  security updates via `apt` like everything else.

## Tuning & troubleshooting

- **One session per user**: xrdp's default policy reuses a user's existing
  session when they reconnect with the same color depth. If you see duplicate
  sessions, set `Policy=Default` and `KillDisconnected=false` in
  `/etc/xrdp/sesman.ini` and restart xrdp (off-hours — this drops sessions).
- **Firewall**: allow 3389 and 8443 only, e.g.
  `ufw allow 3389/tcp && ufw allow 8443/tcp && ufw enable`.
- **Logs**: admin app `journalctl -u kiosk-admin`; per-user kiosk logs in
  `~<user>/.kiosk/{browser.log,x11vnc.log,session.log}`.
- **Screenshot/refresh fails with "no active session"**: the user has no Xorg
  process — they disconnected and `KillDisconnected` reaped the session.
- **Snap Firefox** (Ubuntu): works; the profile deliberately lives at
  `~/kiosk-profile` (not a hidden dot-directory, which snap confinement can't
  read), and policies are installed to `/etc/firefox/policies` plus both
  `distribution/` directories so deb, esr, and snap builds all pick them up.
- **Upgrading from v1.0** (single-URL Chromium kiosk): existing
  `/etc/kiosk/kiosk.conf` files keep working (`KIOSK_URL` = one tab); add a
  `KIOSK_URLS="…"` line to get the 5-tab layout.
