from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from . import auth
from .ctl import check_username, run_ctl
from .sessions import kiosk_group_members, list_sessions

router = APIRouter(dependencies=[Depends(auth.require_auth)])


class NewUser(BaseModel):
    username: str
    password: str


class Password(BaseModel):
    password: str


def _check_password(password: str) -> str:
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="password must be at least 6 characters")
    if "\n" in password:
        raise HTTPException(status_code=400, detail="invalid character in password")
    return password


@router.get("/api/users")
def get_users() -> list[dict]:
    online = {s["user"] for s in list_sessions()}
    return [{"username": u, "online": u in online} for u in kiosk_group_members()]


@router.post("/api/users", status_code=201)
def add_user(body: NewUser) -> dict:
    run_ctl(["adduser", check_username(body.username)],
            stdin=_check_password(body.password) + "\n")
    return {"ok": True}


@router.post("/api/users/{username}/password")
def set_password(username: str, body: Password) -> dict:
    run_ctl(["setpass", check_username(username)],
            stdin=_check_password(body.password) + "\n")
    return {"ok": True}


@router.delete("/api/users/{username}")
def delete_user(username: str) -> dict:
    run_ctl(["deluser", check_username(username)], timeout=60)
    return {"ok": True}
