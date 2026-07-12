"""WebSocket <-> VNC TCP bridge, so noVNC in the admin UI can reach the
per-session x11vnc (which listens on localhost only). Auth is the same
session cookie as the rest of the API."""
import asyncio

from fastapi import APIRouter, WebSocket

from . import auth
from .ctl import NAME_RE
from .sessions import find_session

router = APIRouter()


@router.websocket("/ws/vnc/{username}")
async def vnc_ws(ws: WebSocket, username: str):
    if not auth.ws_authenticated(ws):
        await ws.close(code=4401)
        return
    if not NAME_RE.match(username):
        await ws.close(code=4400)
        return
    session = await asyncio.to_thread(find_session, username)
    if not session:
        await ws.close(code=4404)
        return
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", session["vnc_port"])
    except OSError:
        await ws.close(code=4502)
        return

    await ws.accept(subprotocol="binary")

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
