# TaxiGo AI

A conversational AI dispatch assistant for independent taxi drivers in Lebanon. Instead of filling out forms, the driver just chats — in English, Lebanese Arabic, or French — to add trips, update schedules, track earnings, and get reminded before pickups.

> Screenshots: _add screenshots of the chat panel, bookings sidebar, and weekly summary here before publishing._

## Features

- 💬 **Natural-language dispatch** — "Book Ali tomorrow 3pm from Hamra to the airport" just works, in English, Lebanese Arabic (script or Arabizi), or French.
- 🧠 **Groq-powered agent** (`llama-3.3-70b-versatile`) classifies each message into one of 8 actions and extracts the details; all confirmations/errors are deterministic, bilingual templates — never AI-hallucinated text.
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
├── backend/
│   ├── main.py                  # FastAPI + Socket.IO ASGI app, static frontend serving
│   ├── database.py              # async engine/session config
│   ├── models.py                # ORM model + Pydantic v2 schemas
│   ├── routes/                  # bookings, analytics, chat, notifications
│   ├── services/                # ai_agent, conflict_detector, reminder_service
│   ├── alembic/                 # migrations (async-aware env.py)
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   ├── js/{translations,voice,charts,notifications,app}.js
│   ├── manifest.json
│   ├── service-worker.js
│   └── icons/
├── railway.toml
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
| `GROQ_API_KEY` | API key from [console.groq.com](https://console.groq.com); powers the chat agent (`llama-3.3-70b-versatile`). |
| `DATABASE_URL` | PostgreSQL connection string. Accepts `postgres://`, `postgresql://`, or `postgresql+asyncpg://` — normalized to the asyncpg driver automatically. |
| `FRONTEND_ORIGIN` | (optional) An additional CORS origin to allow, e.g. your deployed frontend's URL, on top of the built-in localhost origins. |

## Deploying to Railway

This repo ships a `railway.toml` and `backend/Dockerfile` that build **from the `backend/` directory as the Docker build context** (so `COPY requirements.txt .` etc. resolve correctly). In the Railway dashboard:

1. Create a new service from this repo, and set the service's **Root Directory** to `backend/` in Settings → Service. This makes the build context match the Dockerfile.
2. Add the `GROQ_API_KEY` and `DATABASE_URL` environment variables (Railway's Postgres plugin can inject `DATABASE_URL` automatically — just make sure it ends up in `postgresql+asyncpg://` form, or let `database.py`'s normalization handle `postgres://`/`postgresql://`).
3. Set `FRONTEND_ORIGIN` to wherever your frontend is hosted.
4. Deploy. Railway will use `healthcheckPath = "/health"` from `railway.toml` to verify the deploy.
5. Run `alembic upgrade head` against the production database (via Railway's shell, or a one-off job) — or rely on the automatic `create_all` bootstrap in `init_db()` for a first deploy.

**Important production note on the frontend:** because the Docker build context is scoped to `backend/`, the `frontend/` folder is **not** included in the production container image — only the API ships in that image. This is intentional and mirrors the CORS setup already in `main.py` (`FRONTEND_ORIGIN`): deploy `frontend/` separately as a static site (Railway static service, Netlify, Vercel, GitHub Pages, or even the same VM behind a reverse proxy) and point it at your API's URL. Locally, the backend conveniently serves the frontend directly (see above) since both folders sit side by side on disk — that convenience just doesn't carry over into the scoped Docker build.

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
| `GET` | `/` | Serves the frontend (local dev; see deployment note above). |

Interactive Swagger docs are also available at `/docs` (and ReDoc at `/redoc`) whenever the backend is running.

## Contributing

1. Fork/branch from `main`.
2. Keep backend changes covered by the existing patterns: business logic and templated bilingual responses live in `services/`, routes stay thin.
3. Keep frontend text going through `js/translations.js` — never hardcode user-facing strings elsewhere.
4. Run the backend's syntax/import checks and exercise the affected endpoints before opening a PR.
5. Open a PR describing the change and, for UI changes, include a screenshot or short clip.
