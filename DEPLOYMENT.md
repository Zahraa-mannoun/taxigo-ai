# Deploying TaxiGo AI to Railway

This is the full step-by-step guide. The short version lives in `README.md`.

> **The single most important thing to get right:** trip times are Lebanon
> wall-clock time, and the reminder service's 28–32 minute window is
> unforgiving of timezone drift. The Dockerfile sets `TZ=Asia/Beirut` and the
> backend uses `zoneinfo`-based helpers everywhere it needs "now"/"today" —
> you don't need to configure anything extra for this, but if you ever change
> how this app is built/run outside the provided Dockerfile, make sure that
> guarantee travels with it.

## 1. Prerequisites

- A [Railway](https://railway.app) account.
- A [Groq API key](https://console.groq.com) (free tier available, but see
  the quota note at the bottom of this doc).
- A PostgreSQL database. Railway can provision one for you (step 3 below).

## 2. Create the service

1. In Railway, **New Project → Deploy from GitHub repo**, and pick this repo.
2. Railway will detect `railway.toml` at the repo root automatically:
   ```toml
   [build]
   builder = "dockerfile"
   dockerfilePath = "Dockerfile"

   [deploy]
   startCommand = "cd backend && uvicorn main:socket_app --host 0.0.0.0 --port $PORT"
   healthcheckPath = "/health"
   ```
   **No manual "Root Directory" setting is needed** — the Dockerfile lives at
   the repo root and copies both `backend/` and `frontend/` into the image
   itself (see the root `Dockerfile`). This is different from an earlier
   version of this project, which required setting Root Directory to
   `backend/`; that requirement no longer applies.

## 3. Add PostgreSQL

1. In the same Railway project, **New → Database → PostgreSQL**.
2. Railway injects a `DATABASE_URL` into your service automatically (as a
   reference variable). `database.py` normalizes `postgres://` and
   `postgresql://` URLs to the `postgresql+asyncpg://` form it needs, so
   Railway's default format works without editing it.

## 4. Set environment variables

On the backend service, add:

| Variable | Value |
|---|---|
| `GROQ_API_KEY` | Your key from console.groq.com |
| `DATABASE_URL` | Usually auto-populated by the Postgres plugin (step 3) |
| `FRONTEND_ORIGIN` | Only needed if you're **also** hosting the frontend somewhere else (see "Split-domain deploys" below) |

Do **not** set `DEV_MODE` in production — leave it unset so Alembic
migrations (next step) are the only source of schema truth.

## 5. Run the database migration

The container does not run migrations automatically on boot (by design —
auto-migrating on every deploy is risky). After the first successful deploy:

```bash
railway run --service <your-service-name> bash -c "cd backend && alembic upgrade head"
```

(or open a shell via the Railway dashboard and run `cd backend && alembic upgrade head` directly).

## 6. Deploy and verify

1. Trigger a deploy (push to your connected branch, or click Deploy in the dashboard).
2. Once live, check `https://<your-app>.up.railway.app/health` — it should
   return `{"status":"ok","database":true,"ai":true}`. Railway also polls
   this path itself per `healthcheckPath` in `railway.toml`.
3. Open `https://<your-app>.up.railway.app/` — the full app (frontend +
   backend, one origin) should load directly.

## Split-domain deploys (optional)

If you'd rather host the frontend separately (a CDN, Vercel, Netlify, GitHub
Pages) instead of using the bundled single-service image:

1. Deploy `frontend/` to your static host of choice as-is.
2. Edit `frontend/config.js` on that host:
   ```javascript
   window.TAXIGO_API_URL = 'https://your-api.up.railway.app';
   ```
3. Set `FRONTEND_ORIGIN` on the Railway backend service to your frontend's
   URL, so CORS allows it.
4. If you've also set `API_SECRET` on the backend (see below), set
   `window.TAXIGO_API_SECRET` in `frontend/config.js` to the same value.

Note: the service worker's offline caching only works same-origin — a
split-domain frontend loses the "view schedule while offline" feature,
since a service worker can't meaningfully cache cross-origin API responses.

## Locking down the API (optional)

By default the API has no authentication — anyone with the URL can create,
modify, or cancel bookings, or use the AI chat (which costs Groq quota). If
your Railway URL will be public/discoverable and you don't want that:

1. Set `API_SECRET` on the backend service to a random string.
2. Set `window.TAXIGO_API_SECRET` in `frontend/config.js` to the same value.
3. Every request except static assets and `/health` now requires a matching
   `X-API-Secret` header, enforced in `main.py`'s `auth_middleware`.

This does **not** cover the Socket.IO connection (used for live reminders/booking
updates) — Socket.IO's handshake is handled before this middleware runs. If you
need to fully lock down a public deployment, treat the live-update channel as
still-open and don't rely on `API_SECRET` alone for anything sensitive.

## About Groq's free-tier quota

The free tier caps out at 100,000 tokens/day. This is easy to hit purely from
health checks and normal testing — `/health` calls Groq for real (cached for
5 minutes to limit this), and each chat message costs a few hundred to a few
thousand tokens depending on conversation history length. If you see the
assistant reply with "having trouble reaching the AI service," check your
[Groq console usage page](https://console.groq.com/settings/billing) before
assuming something is broken — it's very likely you're rate-limited, and it
resets on a rolling basis. Consider the paid Dev Tier before relying on this
for real daily driving use.
