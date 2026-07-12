from fastapi import APIRouter, Depends, Response

from . import auth
from .ctl import check_username, run_ctl

router = APIRouter(dependencies=[Depends(auth.require_auth)])


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


@router.get("/api/sessions/{username}/screenshot")
def screenshot(username: str) -> Response:
    proc = run_ctl(["screenshot", check_username(username)], binary=True, timeout=20)
    return Response(content=proc.stdout, media_type="image/png",
                    headers={"Cache-Control": "no-store"})
