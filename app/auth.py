import base64
import hashlib
import hmac
import json
import os
import time

import bcrypt
from fastapi import HTTPException, Request, WebSocket

from . import config

ROLES = ("admin", "viewer")


def _secret() -> bytes:
    with open(config.SECRET_FILE, "rb") as f:
        return f.read().strip()


def _sign(payload: str) -> str:
    return hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()


# ---------- console user store ----------
# The built-in "admin" account lives in admin.passwd (root-managed, see
# kiosk-admin-passwd). Additional console users live in webusers.json,
# writable by the app: {"<name>": {"hash": "<bcrypt>", "role": "admin|viewer"}}

def load_webusers() -> dict:
    try:
        with open(config.WEBUSERS_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_webusers(users: dict) -> None:
    tmp = config.WEBUSERS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(users, f, indent=2)
    os.replace(tmp, config.WEBUSERS_FILE)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_login(username: str, password: str) -> str | None:
    """Returns the account's role, or None if the credentials are wrong."""
    if username == "admin":
        try:
            with open(config.ADMIN_PASSWD_FILE) as f:
                stored = f.read().strip()
            if bcrypt.checkpw(password.encode(), stored.encode()):
                return "admin"
        except (OSError, ValueError):
            pass
        return None
    entry = load_webusers().get(username)
    if not entry:
        return None
    try:
        if bcrypt.checkpw(password.encode(), entry["hash"].encode()):
            return entry.get("role") if entry.get("role") in ROLES else "viewer"
    except (KeyError, TypeError, ValueError):
        pass
    return None


# ---------- session tokens ----------

def make_token(username: str, role: str) -> str:
    exp = int(time.time()) + config.SESSION_TTL
    payload = base64.urlsafe_b64encode(
        f"{exp}|{username}|{role}".encode()).decode().rstrip("=")
    return f"{payload}.{_sign(payload)}"


def parse_token(token: str | None) -> dict | None:
    if not token or "." not in token:
        return None
    payload, sig = token.rsplit(".", 1)
    if not hmac.compare_digest(sig, _sign(payload)):
        return None
    try:
        raw = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)).decode()
        exp_s, username, role = raw.split("|", 2)
        if int(exp_s) <= time.time() or role not in ROLES:
            return None
    except (ValueError, UnicodeDecodeError):
        return None
    return {"username": username, "role": role}


def require_auth(request: Request) -> dict:
    ident = parse_token(request.cookies.get(config.COOKIE_NAME))
    if not ident:
        raise HTTPException(status_code=401, detail="not authenticated")
    return ident


def require_admin(request: Request) -> dict:
    ident = require_auth(request)
    if ident["role"] != "admin":
        raise HTTPException(status_code=403, detail="admin access required")
    return ident


def ws_authenticated(ws: WebSocket) -> bool:
    return parse_token(ws.cookies.get(config.COOKIE_NAME)) is not None
