from fastapi import APIRouter, Depends

from . import auth
from .ctl import check_username, run_ctl

# session controls are admin-only; viewers get watch/control via VNC only
router = APIRouter(dependencies=[Depends(auth.require_admin)])


@router.post("/api/sessions/{username}/refresh")
def refresh(username: str) -> dict:
    """Soft hard-refresh: sends Ctrl+Shift+R to the user's browser."""
    run_ctl(["refresh", check_username(username)])
    return {"ok": True}


@router.post("/api/sessions/{username}/restart-browser")
def restart_browser(username: str) -> dict:
    """Full reset: kills the browser; the kiosk loop relaunches it with a fresh profile."""
    run_ctl(["restart-browser", check_username(username)])
    return {"ok": True}


@router.post("/api/sessions/{username}/logout")
def logout_session(username: str) -> dict:
    run_ctl(["logout", check_username(username)], timeout=60)
    return {"ok": True}
