"""WebSocket <-> VNC TCP bridge, so noVNC in the admin UI can reach the
per-session x11vnc (which listens on localhost only). Auth is the same
session cookie as the rest of the API."""
import asyncio
import logging

from fastapi import APIRouter, WebSocket

from . import auth
from .ctl import NAME_RE
from .sessions import find_session

router = APIRouter()
log = logging.getLogger("uvicorn.error")


@router.websocket("/ws/vnc/{username}")
async def vnc_ws(ws: WebSocket, username: str):
    if not auth.ws_authenticated(ws):
        log.warning("vnc bridge: rejected unauthenticated request for %s", username)
        await ws.close(code=4401)
        return
    if not NAME_RE.match(username):
        await ws.close(code=4400)
        return
    session = await asyncio.to_thread(find_session, username)
    if not session:
        log.warning("vnc bridge: no active session for %s", username)
        await ws.close(code=4404)
        return
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", session["vnc_port"])
    except OSError:
        log.warning("vnc bridge: x11vnc not reachable on 127.0.0.1:%s for %s",
                    session["vnc_port"], username)
        await ws.close(code=4502)
        return

    # Old noVNC requests the "binary" subprotocol, noVNC 1.3+ requests none.
    # Echoing a subprotocol the client did not ask for makes browsers abort
    # the handshake, so only send it back when it was offered.
    offered = [p.strip() for p in
               (ws.headers.get("sec-websocket-protocol") or "").split(",") if p.strip()]
    await ws.accept(subprotocol="binary" if "binary" in offered else None)
    log.info("vnc bridge: %s connected to 127.0.0.1:%s", username, session["vnc_port"])

    async def ws_to_vnc():
        while True:
            data = await ws.receive_bytes()
            writer.write(data)
            await writer.drain()

    async def vnc_to_ws():
        while True:
            data = await reader.read(65536)
            if not data:
                break
            await ws.send_bytes(data)

    tasks = [asyncio.create_task(ws_to_vnc()), asyncio.create_task(vnc_to_ws())]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for t in tasks:
            t.cancel()
        writer.close()
        try:
            await ws.close()
        except Exception:
            pass
