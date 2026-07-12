"""Discover live xrdp kiosk sessions by scanning Xorg processes."""
import grp
import re
import subprocess

from fastapi import APIRouter, Depends, Response

from . import auth, config
from .ctl import check_username, run_ctl

# viewer-accessible: session list, thumbnails (and the VNC bridge in vncws.py)
router = APIRouter(dependencies=[Depends(auth.require_auth)])

_XORG_RE = re.compile(r"(?:^|/)Xorg\s+:(\d+)")


def kiosk_group_members() -> list[str]:
    try:
        return sorted(grp.getgrnam(config.KIOSK_GROUP).gr_mem)
    except KeyError:
        return []


def list_sessions() -> list[dict]:
    members = set(kiosk_group_members())
    ps = subprocess.run(["ps", "-eo", "user:32,pid,etimes,args"],
                        capture_output=True, text=True)
    sessions: list[dict] = []
    browser_users: set[str] = set()
    for line in ps.stdout.splitlines()[1:]:
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        user, _pid, etimes, args = parts
        if "kiosk-profile" in args:
            browser_users.add(user)
        m = _XORG_RE.search(args)
        if m and user in members:
            display = int(m.group(1))
            sessions.append({
                "user": user,
                "display": display,
                "vnc_port": config.VNC_BASE_PORT + display,
                "uptime": int(etimes),
            })
    for s in sessions:
        s["browser_running"] = s["user"] in browser_users
    return sorted(sessions, key=lambda s: s["user"])


def find_session(username: str) -> dict | None:
    for s in list_sessions():
        if s["user"] == username:
            return s
    return None


@router.get("/api/sessions")
def get_sessions() -> list[dict]:
    return list_sessions()


@router.get("/api/sessions/{username}/screenshot")
def screenshot(username: str) -> Response:
    proc = run_ctl(["screenshot", check_username(username)], binary=True, timeout=20)
    return Response(content=proc.stdout, media_type="image/png",
                    headers={"Cache-Control": "no-store"})
