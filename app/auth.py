import hashlib
import hmac
import time

import bcrypt
from fastapi import HTTPException, Request, WebSocket

from . import config


def _secret() -> bytes:
    with open(config.SECRET_FILE, "rb") as f:
        return f.read().strip()


def _sign(payload: str) -> str:
    return hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()


def make_token() -> str:
    exp = str(int(time.time()) + config.SESSION_TTL)
    return f"{exp}.{_sign(exp)}"


def token_valid(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    exp, sig = token.rsplit(".", 1)
    if not hmac.compare_digest(sig, _sign(exp)):
        return False
    try:
        return int(exp) > time.time()
    except ValueError:
        return False


def verify_password(password: str) -> bool:
    try:
        with open(config.ADMIN_PASSWD_FILE) as f:
            stored = f.read().strip()
        return bcrypt.checkpw(password.encode(), stored.encode())
    except (OSError, ValueError):
        return False


def require_auth(request: Request) -> None:
    if not token_valid(request.cookies.get(config.COOKIE_NAME)):
        raise HTTPException(status_code=401, detail="not authenticated")


def ws_authenticated(ws: WebSocket) -> bool:
    return token_valid(ws.cookies.get(config.COOKIE_NAME))
