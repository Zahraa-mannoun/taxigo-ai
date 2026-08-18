# TaxiGo AI

A conversational AI dispatch assistant for independent taxi drivers in Lebanon. Instead of filling out forms, the driver just chats  in English, Lebanese Arabic, or French  to add trips, update schedules, track earnings, and get reminded before pickups.



## Features

- 💬 **Natural-language dispatch** — "Book Ali tomorrow 3pm from Hamra to the airport" just works, in English, Lebanese Arabic (script or Arabizi), or French.
- 🧠 **Groq-powered agent** (`openai/gpt-oss-20b`, configurable via `GROQ_MODEL`) classifies each message into one of 8 actions and extracts the details; all confirmations/errors are deterministic, bilingual templates — never AI-hallucinated text.
- ⚠️ **Automatic conflict detection** — warns when two trips land within 60 minutes of each other, with a one-tap "book anyway" override.
- ⏰ **Smart reminders** — a background job pings the driver (and every connected device, via Socket.IO) 28–32 minutes before each pickup, once per trip.
- 📊 **Earnings you can trust** — "Earned" (completed trips only) vs. "Projected" (all active trips) are always kept separate; cancelled trips never count.
- 🌍 **Trilingual UI** — English / Arabic (full RTL) / French, with a language toggle that re-renders everything including the AI's own replies.
- 🎙️ **Voice in, voice out** — Web Speech API mic input and text-to-speech, with locale fallback chains per language.
- 📱 **Fully responsive** — bottom-nav mobile layout, collapsible-sidebar tablet layout, fixed dual-pane desktop layout.
- 🌓 **Dark/light theme**, 🔔 **notification bell** with history, 🧾 **per-client history panel**, 📈 **Chart.js weekly earnings chart**, 🖨️ **one-tap PDF export** of today's schedule.
- 👋 **First-run onboarding** (3 steps, skippable, shown once).
- 📴 **Installable PWA** with offline app-shell caching.

## Tech stack

**Backend:** Python, FastAPI, python-socketio (ASGI), SQLAlchemy 2.0 (async) + asyncpg, PostgreSQL, Alembic, Groq SDK, Pydantic v2, aiofiles.
**Frontend:** Vanilla JS (no build step), CSS custom properties, Chart.js (CDN), Socket.IO client (CDN), Web Speech API, Google Fonts (Inter + Space Grotesk).

## Project structure

```
TaxiGo-AI-Production/
├── Dockerfile                    # single-service build: bundles backend/ + frontend/
├── .dockerignore
├── backend/
│   ├── main.py                  # FastAPI + Socket.IO ASGI app, static frontend serving
│   ├── database.py              # async engine/session config
│   ├── models.py                # ORM model + Pydantic v2 schemas
│   ├── timezone_utils.py        # Lebanon-timezone now()/today() helpers
│   ├── routes/                  # bookings, analytics, chat, notifications
│   ├── services/                # ai_agent, conflict_detector, reminder_service
│   ├── alembic/                 # migrations (async-aware env.py)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── config.js                # API_BASE / API_SECRET overrides for split-domain deploys
│   ├── css/styles.css
│   ├── js/{translations,voice,charts,notifications,app}.js
│   ├── manifest.json
│   ├── service-worker.js
│   └── icons/
├── railway.toml
├── DEPLOYMENT.md
└── .gitignore
```

## Local development setup

### 1. Prerequisites
- Python 3.11+
- A PostgreSQL database (local install, Docker, or a hosted free tier e.g. Railway/Supabase/Neon)
- A [Groq API key](https://console.groq.com) (free tier available)

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set GROQ_API_KEY and DATABASE_URL

# create the schema (either works; init_db() also auto-creates tables on first boot)
alembic upgrade head

uvicorn main:socket_app --reload --port 8000
```

The API is now at `http://localhost:8000`. Visiting it in a browser also serves the frontend directly (see note below).

### 3. Frontend

The frontend is static — no build step. Two ways to run it locally:

- **Simplest:** just open `http://localhost:8000/` — the FastAPI backend serves `frontend/` directly when the folder is present alongside `backend/` (this is how local dev works out of the box).
- **Separate dev server** (useful for live-reload tooling): serve `frontend/` with any static file server, e.g. `npx serve frontend` or the VS Code "Live Server" extension, and set `FRONTEND_ORIGIN` in the backend `.env` to that origin so CORS allows it.

### 4. Environment variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | API key from [console.groq.com](https://console.groq.com); powers the chat agent. |
| `GROQ_MODEL` | (optional) Groq model id for the chat agent. Defaults to `openai/gpt-oss-20b`; Groq deprecated the previous default, `llama-3.3-70b-versatile`, on 2026-06-17. |
| `DATABASE_URL` | PostgreSQL connection string. Accepts `postgres://`, `postgresql://`, or `postgresql+asyncpg://` — normalized to the asyncpg driver automatically. |
| `FRONTEND_ORIGIN` | (optional) An additional CORS origin to allow, e.g. a separately-hosted frontend's URL, on top of the built-in localhost origins. |
| `DEV_MODE` | (optional) Set to `1`/`true` to auto-create tables on startup via `create_all()` — convenient for a throwaway local dev database. Leave unset in production; Alembic (`alembic upgrade head`) should be the only source of schema truth there. |
| `API_SECRET` | (optional) If set, every request (except static assets and `/health`) must include a matching `X-API-Secret` header. Leave unset to keep the API open (the default). If set, also set `window.TAXIGO_API_SECRET` in `frontend/config.js` to the same value. |

## Deploying to Railway

> **See [DEPLOYMENT.md](DEPLOYMENT.md) for the full step-by-step guide.** Short version below.

This repo ships a single `Dockerfile` **at the repo root** and a matching `railway.toml` that build both `backend/` and `frontend/` into one container — the backend serves the frontend directly, so there's no separate frontend host to configure and no manual "Root Directory" dashboard setting to remember.

1. Connect this repo as a new Railway service — no Root Directory change needed, the root `Dockerfile` is used automatically per `railway.toml`.
2. Add the `GROQ_API_KEY` and `DATABASE_URL` environment variables (Railway's Postgres plugin can inject `DATABASE_URL` automatically — just make sure it ends up in `postgresql+asyncpg://` form, or let `database.py`'s normalization handle `postgres://`/`postgresql://`).
3. Deploy. Railway will use `healthcheckPath = "/health"` from `railway.toml` to verify the deploy.
4. Run `alembic upgrade head` against the production database (via Railway's shell, or a one-off job). Do **not** set `DEV_MODE` in production — see the table above.

If you'd rather host the frontend separately anyway (e.g. a CDN in front of a static export), that's still supported: set `frontend/config.js`'s `window.TAXIGO_API_URL` to the API's URL, and set `FRONTEND_ORIGIN` on the backend to the frontend's origin for CORS.

## API documentation

All endpoints return JSON. Error responses use structured, bilingual `detail` objects (`{"en": "...", "ar": "...", "fr": "..."}`) rather than raw exceptions.

| Method | Path | Description |
|---|---|---|
| `POST` | `/chat` | Main AI agent endpoint. Body: `{ message, conversation_history, lang }`. Returns `{ reply, action, booking?, bookings?, conflict?, summary?, refresh }`. |
| `GET` | `/bookings` | Active bookings (`confirmed` + `in_progress`). |
| `GET` | `/bookings/completed` | Completed bookings. |
| `GET` | `/bookings/history` | All non-cancelled bookings. |
| `PATCH` | `/bookings/{id}/status` | Update status. Body: `{ status }`. |
| `DELETE` | `/bookings/{id}` | Cancel a booking (soft delete — sets `status=cancelled`). |
| `POST` | `/force-book` | Create a booking even if it conflicts with an existing trip. |
| `GET` | `/clients/{name}/history` | A client's trip history and total earnings. |
| `GET` | `/analytics/weekly` | Last 7 days of earnings/trip counts. |
| `POST` | `/analytics/export` | Export the schedule as JSON. Body: `{ scope: "today" \| "week" \| "all" }`. |
| `GET` | `/notifications/recent` | Recent reminder notifications (backfills the bell panel on page load). |
| `GET` | `/health` | Health check — DB and Groq connectivity. |
| `GET` | `/` | Serves the frontend (both local dev and the bundled production image). |

Interactive Swagger docs are also available at `/docs` (and ReDoc at `/redoc`) whenever the backend is running.

## Contributing

1. Fork/branch from `main`.
2. Keep backend changes covered by the existing patterns: business logic and templated bilingual responses live in `services/`, routes stay thin.
3. Keep frontend text going through `js/translations.js` — never hardcode user-facing strings elsewhere.
4. Run the backend's syntax/import checks and exercise the affected endpoints before opening a PR.
5. Open a PR describing the change and, for UI changes, include a screenshot or short clip.
