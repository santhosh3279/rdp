"""Bridge to the privileged kiosk-ctl helper (runs via a scoped sudoers entry)."""
import re
import subprocess

from fastapi import HTTPException

from . import config

NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


def check_username(username: str) -> str:
    if not NAME_RE.match(username):
        raise HTTPException(status_code=400, detail="invalid username")
    return username


def run_ctl(args: list[str], stdin: str | None = None, binary: bool = False,
            timeout: int = 30) -> subprocess.CompletedProcess:
    cmd = [config.SUDO, "-n", config.KIOSK_CTL, *args]
    try:
        if binary:
            proc = subprocess.run(cmd, input=stdin.encode() if stdin else None,
                                  capture_output=True, timeout=timeout)
        else:
            proc = subprocess.run(cmd, input=stdin, capture_output=True,
                                  text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail=f"kiosk-ctl {args[0]} timed out")
    if proc.returncode != 0:
        err = proc.stderr
        if isinstance(err, bytes):
            err = err.decode(errors="replace")
        raise HTTPException(status_code=500, detail=err.strip() or "kiosk-ctl failed")
    return proc
