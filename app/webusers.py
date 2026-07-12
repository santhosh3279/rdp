"""Console (web UI) accounts with roles. Admin-only management.

admin  - full control
viewer - dashboard + live view/control of screens only; no kiosk-user
         management, no refresh/reset/logout controls
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from . import auth
from .ctl import NAME_RE

router = APIRouter(dependencies=[Depends(auth.require_admin)])


class NewWebUser(BaseModel):
    username: str
    password: str
    role: str = "viewer"


class Password(BaseModel):
    password: str


def _check_name(username: str) -> str:
    if not NAME_RE.match(username):
        raise HTTPException(status_code=400, detail="invalid username")
    if username == "admin":
        raise HTTPException(status_code=400,
                            detail="'admin' is built in (sudo kiosk-admin-passwd)")
    return username


def _check_password(password: str) -> str:
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="password must be at least 6 characters")
    return password


@router.get("/api/webusers")
def list_webusers() -> list[dict]:
    users = [{"username": "admin", "role": "admin", "builtin": True}]
    for name, entry in sorted(auth.load_webusers().items()):
        users.append({"username": name,
                      "role": entry.get("role", "viewer"),
                      "builtin": False})
    return users


@router.post("/api/webusers", status_code=201)
def add_webuser(body: NewWebUser) -> dict:
    if body.role not in auth.ROLES:
        raise HTTPException(status_code=400, detail="role must be admin or viewer")
    users = auth.load_webusers()
    if _check_name(body.username) in users:
        raise HTTPException(status_code=409, detail="console user already exists")
    users[body.username] = {"hash": auth.hash_password(_check_password(body.password)),
                            "role": body.role}
    auth.save_webusers(users)
    return {"ok": True}


@router.post("/api/webusers/{username}/password")
def set_webuser_password(username: str, body: Password) -> dict:
    users = auth.load_webusers()
    if _check_name(username) not in users:
        raise HTTPException(status_code=404, detail="no such console user")
    users[username]["hash"] = auth.hash_password(_check_password(body.password))
    auth.save_webusers(users)
    return {"ok": True}


@router.delete("/api/webusers/{username}")
def delete_webuser(username: str) -> dict:
    users = auth.load_webusers()
    if _check_name(username) not in users:
        raise HTTPException(status_code=404, detail="no such console user")
    del users[username]
    auth.save_webusers(users)
    return {"ok": True}
