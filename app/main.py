import os

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import auth, config
from .control import router as control_router
from .sessions import router as sessions_router
from .users import router as users_router
from .vncws import router as vnc_router
from .webusers import router as webusers_router

app = FastAPI(title="Kiosk Admin", docs_url=None, redoc_url=None, openapi_url=None)

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class LoginBody(BaseModel):
    username: str = "admin"
    password: str


@app.post("/api/login")
def login(body: LoginBody, response: Response) -> dict:
    username = body.username.strip() or "admin"
    role = auth.verify_login(username, body.password)
    if not role:
        raise HTTPException(status_code=401, detail="wrong username or password")
    response.set_cookie(config.COOKIE_NAME, auth.make_token(username, role),
                        max_age=config.SESSION_TTL, httponly=True,
                        samesite="lax", secure=config.COOKIE_SECURE)
    return {"ok": True, "role": role}


@app.get("/api/me")
def me(ident: dict = Depends(auth.require_auth)) -> dict:
    return ident


@app.post("/api/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(config.COOKIE_NAME)
    return {"ok": True}


@app.get("/api/version")
def version() -> dict:
    try:
        with open(os.path.join(_BASE, "VERSION")) as f:
            return {"version": f.read().strip()}
    except OSError:
        return {"version": "dev"}


app.include_router(sessions_router)
app.include_router(users_router)
app.include_router(webusers_router)
app.include_router(control_router)
app.include_router(vnc_router)

if os.path.isdir(config.NOVNC_DIR):
    app.mount("/novnc", StaticFiles(directory=config.NOVNC_DIR), name="novnc")
app.mount("/", StaticFiles(directory=os.path.join(_BASE, "static"), html=True), name="static")
