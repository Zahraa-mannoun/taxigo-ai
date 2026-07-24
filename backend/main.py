"""
TaxiGo AI backend entry point.

Wires together FastAPI (REST), python-socketio (real-time reminders/
booking events) and the static frontend into a single ASGI app. Railway
(and the Dockerfile CMD) run this module's `socket_app` object.
"""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

import aiofiles
import socketio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from database import check_db_connection, init_db
from routes import analytics, bookings, chat, notifications
from services import ai_agent, reminder_service

# backend/ and frontend/ are siblings both in local dev (repo root) and in
# the production image (Dockerfile at repo root COPYs both under /app/), so
# "parent of this file's directory, then into frontend/" resolves correctly
# in both cases without needing an environment-specific branch.
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = (BASE_DIR.parent / "frontend").resolve()

DEFAULT_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
extra_origin = os.getenv("FRONTEND_ORIGIN")
ALLOWED_ORIGINS = DEFAULT_ORIGINS + ([extra_origin] if extra_origin else [])


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    reminder_service.start(app.state.sio)
    yield
    reminder_service.stop()


app = FastAPI(title="TaxiGo AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Optional shared-secret auth --------------------------------------------
# Off by default (API_SECRET unset) to preserve today's open behavior for
# local dev / anyone who hasn't opted in. Set API_SECRET to require every
# non-exempt request to send a matching X-API-Secret header -- useful if this
# API ends up reachable at a public URL. NOTE: this only covers plain HTTP
# routes; Socket.IO's own ASGI app (wrapping this one) handles its handshake
# before this middleware ever runs, so it is NOT covered by this check.
_UNAUTHENTICATED_PATHS = {
    "/health",
    "/",
    "/manifest.json",
    "/service-worker.js",
    "/config.js",
    "/docs",
    "/redoc",
    "/openapi.json",
}
_UNAUTHENTICATED_PREFIXES = ("/css/", "/js/", "/icons/")


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    secret = os.getenv("API_SECRET")
    path = request.url.path
    if (
        not secret
        or path in _UNAUTHENTICATED_PATHS
        or path.startswith(_UNAUTHENTICATED_PREFIXES)
    ):
        return await call_next(request)
    if request.headers.get("X-API-Secret") != secret:
        return JSONResponse(
            status_code=401,
            content={
                "detail": {
                    "en": "Unauthorized.",
                    "ar": "غير مصرح.",
                    "fr": "Non autorisé.",
                }
            },
        )
    return await call_next(request)


# --- Socket.IO -------------------------------------------------------------
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=ALLOWED_ORIGINS,
)
app.state.sio = sio


@sio.event
async def connect(sid, environ):
    print(f"[socket.io] client connected: {sid}")


@sio.event
async def disconnect(sid):
    print(f"[socket.io] client disconnected: {sid}")


# --- REST routers ------------------------------------------------------------
app.include_router(bookings.router, tags=["bookings"])
app.include_router(analytics.router, tags=["analytics"])
app.include_router(chat.router, tags=["chat"])
app.include_router(notifications.router, tags=["notifications"])


@app.get("/health")
async def health_check():
    db_ok = await check_db_connection()
    ai_ok = await ai_agent.check_ai_connectivity()
    status = "ok" if (db_ok and ai_ok) else "degraded"
    return JSONResponse(
        status_code=200 if db_ok else 503,
        content={"status": status, "database": db_ok, "ai": ai_ok},
    )


# --- Frontend static files ---------------------------------------------------
if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
    app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
    app.mount("/icons", StaticFiles(directory=FRONTEND_DIR / "icons"), name="icons")

    @app.get("/manifest.json")
    async def manifest():
        async with aiofiles.open(FRONTEND_DIR / "manifest.json", mode="r") as f:
            content = await f.read()
        return JSONResponse(content=json.loads(content))

    @app.get("/service-worker.js")
    async def service_worker():
        async with aiofiles.open(FRONTEND_DIR / "service-worker.js", mode="r") as f:
            content = await f.read()
        return HTMLResponse(content=content, media_type="application/javascript")

    @app.get("/config.js")
    async def config_js():
        async with aiofiles.open(FRONTEND_DIR / "config.js", mode="r") as f:
            content = await f.read()
        return HTMLResponse(content=content, media_type="application/javascript")

    @app.get("/")
    async def serve_index():
        async with aiofiles.open(FRONTEND_DIR / "index.html", mode="r", encoding="utf-8") as f:
            content = await f.read()
        return HTMLResponse(content=content)


socket_app = socketio.ASGIApp(sio, other_asgi_app=app)
