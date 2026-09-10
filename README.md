# card2lead

Event-based business-card lead capture.

An authorised user logs in, picks an **event**, photographs a business card
(read by **Groq**), reviews the fields, and saves them as one row in a
**Google Sheet** — one tab per event. An **admin** creates events, controls who
can access each one, and manages the "Assigned To" name list.

- **Backend:** Python / FastAPI. SQLite for metadata (users, events, access
  grants, the assignee list, audit log, dedupe keys). Google Sheets for the
  leads themselves.
- **Frontend:** React / Vite. Served by the backend in production (one origin,
  one URL).
- **Plan:** [`plan.md`](plan.md). Rationale: [`suggestions.md`](suggestions.md).
- **Deploy:** [`DEPLOY.md`](DEPLOY.md).
- **API examples:** [`card2lead.postman_collection.json`](card2lead.postman_collection.json)
  · live docs at `/docs` when the server is running.
- **First prototype (frozen, reference only):** [`intial_stage/`](intial_stage/).

**Status:** all seven build phases are complete — backend, frontend and the
one-container image. Deploy per [`DEPLOY.md`](DEPLOY.md).

## The flow

```
register ──▶ admin grants you event access ──▶ log in ──▶ pick event
                                                              │
                                     ┌────────────────────────┘
                                     ▼
        photograph a card ──▶ Groq reads it ──▶ review / edit ──▶ SAVE
                                                              │
                                                              ▼
                                   one row in that event's Google Sheet tab
                          Timestamp │ User Email │ Event │ Name │ Company │
                          Title │ Email │ Phone │ Notes │ Assigned To
```

## API

| Method &amp; path | Who | What |
|---|---|---|
| `GET /health` | anyone | liveness + whether Groq / Sheets are configured |
| `POST /auth/register` | anyone | self-serve account (email + password ≥ 8) → JWT |
| `POST /auth/login` | anyone | → JWT (7-day) |
| `GET /auth/me` | logged in | current user |
| `POST /auth/forgot-password` · `/reset-password` | anyone | stubbed until SMTP |
| `POST /events` | admin | create an event **and** its Google Sheet tab |
| `GET /events` · `GET /events/{id}` | admin: all · user: assigned only | list / detail |
| `PATCH /events/{id}` | admin | edit description / location / organizer / dates / active |
| `GET /events/{id}/access` | admin | who can use this event |
| `POST /events/{id}/access` `{email}` | admin | grant access (user must have registered) |
| `DELETE /events/{id}/access/{userId}` | admin | revoke |
| `GET /me/events` | logged in | events this user may use (the picker) |
| `GET /assignees` | logged in | active names for the "Assigned To" dropdown |
| `GET /assignees?all=true` · `POST /assignees` · `DELETE /assignees/{id}` | admin | manage the list (remove is soft) |
| `POST /events/{id}/scan` | event access | multipart `image` → `{name, company, title, email, phone}`; not saved |
| `POST /events/{id}/leads` | event access | reviewed fields + `assigned_to` + `request_id` → one Sheet row; a repeated `request_id` is a no-op |

All non-auth routes need `Authorization: Bearer <token>`.

## Run it locally

### 1. Backend (`:8000`)

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate     macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit .env — at least ADMIN_PASSWORD
uvicorn app.main:app --reload --port 8000
```

- Health: <http://localhost:8000/health>  ·  API docs: <http://localhost:8000/docs>
- With no `GROQ_API_KEY`, card reading runs in **mock mode** (returns sample data).
- With no `GOOGLE_SHEET_ID`, saves are accepted but not written to a sheet.

### 2. Frontend (`:5173`, dev only)

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The Vite dev server proxies `/auth`, `/events`,
`/me`, `/assignees` to the backend on `:8000`.

### One-container run (frontend + API together, like production)

```bash
cp backend/.env.example backend/.env      # edit it; put the Google key in backend/secrets/gsa.json
docker compose up --build                 # -> http://localhost:8000
```

## First-time setup

1. **Admin** — set `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `backend/.env`. The admin
   is created on first boot; the password is kept in sync with the env value
   afterwards (so it's also the recovery path).
2. **Google Sheet** — create one Google Sheet, enable the Google Sheets API on a
   Google Cloud project, create a service account, download its JSON key to
   `backend/secrets/gsa.json`, and share the sheet with the service account's
   email as **Editor**. Put the sheet id in `GOOGLE_SHEET_ID`.
3. **Groq** — put your key in `GROQ_API_KEY` (leave blank for mock mode).
4. Log in as admin → create an event → grant users access → they log in and scan.

## Tests

```bash
cd backend
pip install pytest
python -m pytest -q          # 46 tests, no network needed
```

## Project layout

```
backend/app/
  core/      config, logging + audit, rate limiter, security (hash + JWT)
  db/        SQLite engine + SQLModel tables
  auth/      register / login / me / admin seed
  events/    admin: create / edit events (+ create a Sheet tab per event)
  assignees/ admin-managed "Assigned To" list
  access/    grant / revoke per-event access; require_event_access dependency
  groq/      Groq vision client + per-minute/day quota guard
  scan/      POST /events/{id}/scan  (image -> fields, not saved)
  leads/     POST /events/{id}/leads (reviewed fields -> one Sheet row)
  sheets/    Google Sheets client + serialised, retrying row writer
frontend/src/
  screens/   Login, EventPicker, Landing, Camera, Review, Success
  lib/       api (token-aware fetch), auth (token store), image, blur
```

## Configuration

Every setting is an environment variable — see
[`backend/.env.example`](backend/.env.example) and
[`frontend/.env.example`](frontend/.env.example). `.env` files and the service
-account key are git-ignored; nothing secret is committed.
