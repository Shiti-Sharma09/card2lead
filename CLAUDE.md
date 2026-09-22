# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## What this is

**card2lead** — event-based business-card lead capture.

An authorised user logs in, picks an **event**, photographs a business card
→ **Groq** reads the 5 fields (name, company, title, email, phone) → user
reviews/edits and picks an **Assigned To** name → the lead is appended as one
row to that event's tab in a **Google Sheet**. An **admin** creates events,
grants/revokes per-event access by email, and manages the Assigned To list.

- **Backend:** Python 3.12 / FastAPI. **SQLite** holds metadata (users, events,
  per-event access grants, the assignee list, audit log, idempotency keys).
  **Google Sheets** holds the leads themselves — one spreadsheet, one tab per
  event.
- **Frontend:** React 18 + Vite 5 + Tailwind 3, no TypeScript. Served by the
  backend in production (one origin, one URL — no CORS to configure).
- **Auth:** JWT (7-day, no refresh). Admin seeded from env on first boot.
- **LLM:** Groq vision, model from `GROQ_MODEL` (default `qwen/qwen3.8-27b`).

Environment is **Windows + PowerShell**. The repo root **is** a git repo
(`github.com/Shiti-Sharma09/card2lead`, public). Design docs: `plan.md`
(the *how*), `suggestions.md` (the *why*), `DEPLOY.md` (hosting). API examples:
`card2lead.postman_collection.json`.

The earlier single-user Gemini+Excel prototype is frozen in `intial_stage/`
for reference only — nothing there is used by this app. See
`intial_stage/HOW_TO_RUN.md`.

## Commands

No helper scripts — run things directly.

```powershell
# Backend on :8000
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env          # then edit .env (at least ADMIN_PASSWORD)
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# Frontend dev server on :5173 (proxies /auth,/events,/me,/assignees -> :8000)
cd frontend
npm install
npm run dev

# Tests — real pytest, 46 tests, in-memory SQLite, no network needed
cd backend
.\.venv\Scripts\python.exe -m pytest -q

# Full app in one container (frontend + API on :8000), like production
docker compose up --build
```

- Health: <http://localhost:8000/health>  ·  live API docs: <http://localhost:8000/docs>
- Frontend build only: `cd frontend; npm run build`. No frontend lint/test setup.

## Mock / degraded modes (important)

- **`GROQ_API_KEY` empty** → `groq.is_mock()` is true; `POST /events/{id}/scan`
  returns realistic sample fields. The whole flow (login, scan, review, save)
  works with no key. Adding the key later needs no code change.
- **`GOOGLE_SHEET_ID` empty** → `sheets.is_configured()` is false; `POST
  /events/{id}/leads` is accepted and logged as `SHEET_WRITE_SKIPPED` but no
  row is written. Event creation skips making a tab.
- Tests run with both empty, so they never hit the network.

## Architecture

### Backend (`backend/app/`, FastAPI, **sync** route handlers)

Handlers are `def` not `async def` on purpose — Starlette runs them in a
threadpool so blocking Groq / Google / SQLite work never stalls the event loop.

| Module | Responsibility |
|---|---|
| `core/config.py` | one `@lru_cache`d `Settings` from `backend/.env` (pydantic-settings). `startup_warnings()` nags on weak prod config. |
| `core/logging.py` | structured lines to stdout **and** a rotating `logs/app.log`. `log_event(action, session=…, actor=…, **detail)` also writes an `audit_log` row. Never logs secrets. |
| `core/security.py` | bcrypt hash/verify (72-byte cap); JWT `HS256` encode/decode. |
| `core/rate_limit.py` | tiny in-process fixed-window limiter as a FastAPI dependency (`rate_limit(name, perMin)`); auto-disabled when `APP_ENV=test`. |
| `db/base.py` + `db/models.py` | SQLite engine (StaticPool for the in-memory test DB) + SQLModel tables: `User`, `Event`, `Assignee`, `EventAccess`, `IdempotencyKey`, `AuditLog`. `init_db()` = `create_all` on startup (no migration tool yet). |
| `auth/` | `POST /auth/register` (self-serve, pw ≥ 8 → JWT), `/auth/login`, `GET /auth/me`, `/auth/forgot-password` + `/auth/reset-password` (**stubbed** until SMTP). `seed_admin()` creates the admin from `ADMIN_EMAIL`/`ADMIN_PASSWORD` on first boot and re-syncs its password to the env value afterwards (so the env var is the recovery path). Token invalidation without a blocklist: `users.password_changed_at` vs the token `iat`. |
| `events/` | admin only: `POST /events` (creates the event **and** its Google Sheet tab, stores the tab id; Google failure → 502, no event created), `GET /events`, `GET /events/{id}`, `PATCH /events/{id}`. Event `name` + `slug` unique; `name` is not editable (tied to the tab). |
| `assignees/` | the admin-managed "Assigned To" list. `GET /assignees` (active, any user), `?all=true` / `POST` / `DELETE` (admin). Remove is soft (`is_active=false`); re-adding a removed name reactivates it. Seeded from `SEED_ASSIGNEES` (default `NITISH,HARSHAD`). |
| `access/` | `event_access` table, unique `(user_id, event_id)`. `POST /events/{id}/access {email}` (grant; 404 if the person hasn't registered), `DELETE …/access/{userId}` (revoke), `GET …/access` (list). `GET /me/events` feeds the picker. `deps.require_event_access(event_id)` guards scan/leads: admin passes; others need an **active** event **and** a grant; denials log `ACCESS_DENIED`. |
| `groq/client.py` | one **non-streaming** vision call. `parse_fields()` tolerates ```json fences, stray prose, and alternate key names (`company_name`, `mail_address`, `phone_number`, `designation`, …). One retry + 1s backoff, then `GroqError` → 502. |
| `groq/quota.py` | process-wide fixed-window guard, `GROQ_MAX_PER_MIN` / `GROQ_MAX_PER_DAY` (25 / 1000). Exceeded → 429, logged `RATE_LIMIT_HIT`. Skipped in mock mode. |
| `scan/router.py` | `POST /events/{id}/scan` (multipart `image`, `require_event_access`): reject empty / over `MAX_UPLOAD_MB` → `lib/image_prep` (EXIF-rotate, downscale ≤1600px, JPEG; HEIC via pillow-heif) → quota → Groq → `lib/normalize` (email lowercased/deduped, phone forced to `+91 XXXXX XXXXX`) → `{mock, fields}`. **Does not save.** |
| `leads/router.py` + `leads/service.py` | `POST /events/{id}/leads` (`require_event_access`): body = reviewed fields + `assigned_to` + `request_id`. Dedupe on `request_id` via `idempotency_keys` — the key is **claimed (unique constraint) before the write**, so a double-tap can't make two rows; a failed write releases the claim so a retry works; a repeat returns the first result as `duplicate:true`. Validates: `name` required, `assigned_to` must be a currently-active name (422), email format if given (422). Row = `[IST timestamp, user email, event name, name, company, title, email, phone, notes, assigned_to]`. |
| `sheets/client.py` | service-account auth (`GOOGLE_SERVICE_ACCOUNT_FILE`), one spreadsheet (`GOOGLE_SHEET_ID`). `create_event_tab()` sanitises the name (strips `[ ] : * ? / \`, 95-char cap), de-dupes with a ` (2)` suffix, adds the tab, writes the header row. |
| `sheets/writer.py` | `append_row()` — all appends serialised through a process-wide `threading.Lock`; up to 3 attempts with exponential backoff; values written **RAW** so a card value like `=cmd()` can't become a live formula. Every attempt fails → `SheetsError` → the route returns 502 and never reports a false success. Single-process only; a multi-worker deploy would need a cross-process lock. |
| `main.py` | registers the routers; if a built frontend exists (`FRONTEND_DIST` → `../frontend/dist` → `/app/frontend_dist`) it is mounted at `/` **last**, so it never shadows an API route. This is what serves app + API from one origin. |

**The Google Sheet tab columns** (per event):
`Timestamp | User Email | Event | Name | Company | Title | Email | Phone | Notes | Assigned To`
Timestamp + User Email are set server-side from the session — never sent by the client.

**Audit events** worth grepping in `logs/app.log`: `USER_REGISTERED`,
`USER_LOGIN`, `LOGIN_FAILED`, `ADMIN_SEEDED`/`ADMIN_SYNCED`, `EVENT_CREATED`,
`SHEET_TAB_CREATED`, `ASSIGNEE_ADDED`/`_REMOVED`/`_REACTIVATED`,
`ACCESS_GRANTED`/`_REVOKED`/`_DENIED`, `GROQ_REQUEST`/`GROQ_FAILED`,
`RATE_LIMIT_HIT`, `LEAD_SUBMITTED`, `SHEET_WRITE_OK`/`_FAILED`/`_SKIPPED`,
`DUPLICATE_IGNORED`.

### Frontend (`frontend/src/`)

`App.jsx` is a single state machine over one `screen` string:
`booting → login → events → landing → camera | (upload) → processing → review → success`.

- On boot an existing token (`localStorage`, via `lib/auth.js`) is validated
  with `GET /auth/me`.
- `lib/api.js` is the only place that talks to the backend. It attaches
  `Authorization: Bearer <token>`; **any 401 clears the token and the app
  returns to the login screen**. Endpoints: `login`, `register`, `fetchMe`,
  `fetchMyEvents`, `fetchAssignees`, `scanCard(eventId, blob)`,
  `saveLead(eventId, payload)`.
- `screens/Login.jsx` — email + password, "create account" toggle.
  `screens/EventPicker.jsx` — from `GET /me/events`; "no access yet — ask your
  admin, then refresh" when empty.
- `screens/Review.jsx` — **no confidence scores / "please verify" UI**. Plain
  editable fields + Notes. Assigned To dropdown from `GET /assignees`. A fresh
  `request_id` (`crypto.randomUUID`) is generated per scan and sent with the
  save; a duplicate shows "Already saved".
- `lib/blur.js` runs a **client-side** sharpness check in `Camera.jsx` before
  capture (independent of anything server-side). `lib/image.js` downscales to
  JPEG. The captured image is an in-memory object URL — **never uploaded to
  storage or persisted**.
- `API_BASE` defaults to `''` (same origin in prod; the Vite proxy in
  `vite.config.js` covers dev).

## Configuration

`backend/.env` (copy from `backend/.env.example`):

| Var | Default | Effect |
|---|---|---|
| `APP_ENV` | `dev` | `prod` = stricter startup warnings; `test` disables the rate limiter |
| `DATABASE_URL` | `sqlite:///./app.db` | SQLite file; use `sqlite:///./data/app.db` + a mounted volume to persist |
| `JWT_SECRET` | `dev-only-change-me` | token signing — set a long random value in prod |
| `JWT_EXPIRES_DAYS` | `7` | token lifetime |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | `admin@example.com` / *(empty)* | seed + recovery for the admin; blank password → seed skipped |
| `GROQ_API_KEY` | *(empty)* | empty → mock extraction |
| `GROQ_MODEL` | `qwen/qwen3.8-27b` | swap model, no code change |
| `GROQ_MAX_PER_MIN` / `GROQ_MAX_PER_DAY` | `25` / `1000` | Groq quota guard |
| `GROQ_TIMEOUT_S` | `30` | per-call timeout |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | `./secrets/gsa.json` | Sheets API key (git-ignored; on Render a Secret File at `/etc/secrets/gsa.json`) |
| `GOOGLE_SHEET_ID` | *(empty)* | the one spreadsheet; empty → writes skipped |
| `MAX_UPLOAD_MB` | `12` | reject larger uploads |
| `SEED_ASSIGNEES` | `NITISH,HARSHAD` | initial Assigned To names (first boot only) |
| `TIMEZONE` | `Asia/Kolkata` | how the Timestamp column is written |
| `CORS_ORIGINS` | `*` | fine when the backend also serves the frontend |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASS` / `SMTP_FROM` | *(empty)* | forgot-password (not wired yet) |

`frontend/.env` (copy from `frontend/.env.example`): `VITE_API_BASE` (empty =
same origin / proxy), `VITE_API_PROXY` (dev proxy target, default
`http://localhost:8000`), `VITE_BLUR_THRESHOLD` (client blur cutoff).

Git-ignored: `backend/.env`, `frontend/.env`, `backend/secrets/`, `*.db`,
`logs/`, build output, and the old-prototype `intial_stage/` inputs. Nothing
secret is committed.

## Deploy

One multi-stage `Dockerfile` at the repo root builds the React app, then the
API image that serves both on `$PORT` (default 8000). `DEPLOY.md` has the
Render steps (Docker runtime, env-var table, the Google key as a Secret File,
free-tier caveats) and a small-VM alternative. `docker-compose.yml` runs the
same image locally with SQLite on a named volume.
