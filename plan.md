# Execution Plan — standalone event-based backend

**What we're building:** a small FastAPI backend + the existing React app.
Authorised users log in, pick an event, photograph a business card
(**read by Groq**), review the fields, and save them as a row in a
**Google Sheet** — one tab per event. An **admin** creates events, controls who
can access each one, and manages the list of names in the "Assigned To"
dropdown.

The *why* behind every choice is in `suggestions.md`. This file is the *how* —
the build order, what each step delivers, and how you verify it.

The earlier prototype is kept, untouched, in `intial_stage/` for reference only
(`intial_stage/HOW_TO_RUN.md`). Nothing in it is used by this build.

---

## 1. The plan at a glance


| # | Phase              | Goal (plain words)                                                                                                              | You can test it by                                                                                  | Needs from you first                   |
| - | ------------------ | ------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | -------------------------------------- |
| 0 | **Skeleton**       | App boots, logs, health check, runs in Docker                                                                                   | Open`/health` → `{"status":"ok"}`                                                                  | Repo name + private/public             |
| 1 | **Login**          | Self-register + log in; admin account exists; tokens work                                                                       | Register → log in → call`/auth/me` with the token                                                 | Admin email + password to seed         |
| 2 | **Events & lists** | Admin creates/edits events (each gets its own Sheet tab) and manages the "Assigned To" name list                                | Admin creates "Test Event" → new tab with headers appears in your Sheet; admin adds/removes a name | Google service-account JSON + Sheet ID |
| 3 | **Access control** | Admin assigns/revokes users per event; unassigned users are blocked                                                             | User gets 403 on an event → admin assigns → 200 → revoke → 403                                  | —                                     |
| 4 | **Groq scan**      | Send a card photo, get back name / company / title / email / phone                                                              | Upload a dummy card → correct fields back (or sample data with no key)                             | Groq API key (received)                |
| 5 | **Save to Sheet**  | Reviewed card → one row in the right event tab, with the user's email + timestamp + Assigned To; double-taps don't double-save | Save a card → row in the correct tab; submit twice → still one row                                | —                                     |
| 6 | **Frontend**       | React app gets login + event picker + admin-managed Assigned To dropdown, points at the new backend                             | Full run on your phone: login → pick event → scan → review → save                               | Where the frontend will be hosted      |
| 7 | **Docs + deploy**  | README, Postman collection, deploy steps; live on Render                                                                        | Open the public URL, do a full run                                                                  | Render account connected to the repo   |

Each phase is one pull request, done **in order** — each builds on the last and
is testable on its own. Relative effort: 0 = S, 1–6 = M each, 7 = S. Nothing is
large — that's deliberate.

---

## 2. Architecture (short)

```
  React app (phone / browser)
     |  1. POST /auth/login              -> JWT (7 days)
     |  2. GET  /me/events               -> events this user may use   (event dropdown)
     |  3. GET  /assignees               -> current names              (Assigned To dropdown)
     |  4. POST /scan   (image + event)  -> Groq reads the card -> fields
     |  5. POST /leads  (fields + event) -> one row in that event's Sheet tab
     v
  FastAPI backend  (single instance)
     |-- SQLite (one file): users, events, access grants, assignee names, audit log, dedupe keys
     |-- Groq API: one non-streaming call per card
     |-- Google Sheets API: ONE spreadsheet, ONE TAB per event, append rows
```

- **Two stores on purpose:** leads go to Google Sheets (for the sales team);
  everything else is SQLite (fast checks on every request).
- **Single backend instance.** No scaling, no Redis, no queue service.
- **Model id, keys, URLs all come from `.env`** — never hard-coded.

---

## 3. Data model

### SQLite tables


| Table              | Fields                                                                                                                                             | Notes                                                                                                              |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `users`            | id, email (unique), password_hash, role (`admin`/`user`), is_active, created_at, password_changed_at                                               | admin seeded from`.env` on first boot                                                                              |
| `events`           | id, name (unique), slug, description, location, organizer, start_date, end_date, is_active, google_tab_id, google_tab_name, created_at, created_by | `google_tab_id` = numeric id of the tab we created in the Sheet                                                    |
| `event_access`     | id, user_id, event_id, granted_by, granted_at                                                                                                      | unique (user_id, event_id); delete row = revoke                                                                    |
| `assignees`        | id, name (unique), is_active, created_at, created_by                                                                                               | the "Assigned To" dropdown;**admin can add / remove** — removing sets `is_active = false` so past rows stay valid |
| `audit_log`        | id, ts, actor_email, action, detail (JSON), ip                                                                                                     | mirrored to stdout; never contains secrets                                                                         |
| `idempotency_keys` | id, key, user_id, result_ref, created_at                                                                                                           | rejects double submits; old rows pruned                                                                            |

Schema is created automatically on startup — small enough that no migration tool
is needed yet.

### Google Sheet layout

**One spreadsheet** (you create it once, share it with the service account).
When an admin creates an event, we add a **tab** named after it and write this
header row:

```
Timestamp | User Email | Event | Name | Company | Title | Email | Phone | Notes | Assigned To
```

- `Timestamp` and `User Email` are set by the server from the logged-in
  session — never sent by the client.
- `Event` repeats the tab name (useful if tabs are later merged/exported).
- `Assigned To` is chosen on the review screen from the **admin-managed list**.
- Tab names are auto-cleaned (Google forbids `[ ] : * ? / \`, 100-char max,
  must be unique). We store the tab's numeric id so renaming an event later
  won't break the link.
- No card images are stored.

---

## 4. API surface


| Method + path                              | Who                               | Purpose                                                    |
| ------------------------------------------ | --------------------------------- | ---------------------------------------------------------- |
| `GET /health`                              | anyone                            | liveness check                                             |
| `POST /auth/register`                      | anyone                            | self-serve account (email + password, min 8)               |
| `POST /auth/login`                         | anyone                            | → JWT (7 days)                                            |
| `GET /auth/me`                             | logged in                         | current user info                                          |
| `POST /auth/forgot-password`               | anyone                            | **stub in Phase 1**, real once SMTP is set (email OTP)     |
| `POST /auth/reset-password`                | anyone + OTP                      | set a new password with the OTP                            |
| `POST /events`                             | admin                             | create event (+ create its Sheet tab)                      |
| `GET /events`                              | admin: all · user: assigned only | list events                                                |
| `GET /events/{id}` · `PATCH /events/{id}` | admin (user: read if assigned)    | view / edit event                                          |
| `GET /events/{id}/access`                  | admin                             | who can use this event                                     |
| `POST /events/{id}/access`                 | admin                             | grant access to a user (by email)                          |
| `DELETE /events/{id}/access/{userId}`      | admin                             | revoke access                                              |
| `GET /me/events`                           | logged in                         | events I can use (feeds the event dropdown)                |
| `GET /assignees`                           | logged in                         | current (active) names for the Assigned To dropdown        |
| `GET /assignees?all=true`                  | admin                             | all names incl. removed ones                               |
| `POST /assignees`                          | admin                             | add a name                                                 |
| `DELETE /assignees/{id}`                   | admin                             | remove a name (soft — dropdown only, past rows untouched) |
| `POST /scan`                               | logged in + event access          | image + event → Groq → fields (not saved)                |
| `POST /leads`                              | logged in + event access          | fields + event + Assigned To + request-id → one Sheet row |
| `GET /admin/logs`                          | admin                             | recent audit entries (handy for debugging)                 |

---

## 5. Phase-by-phase detail

### Phase 0 — Skeleton  (S)

- Repo **`card2lead`**, public, under **`Shiti-Sharma09`**. Feature-branch → PR workflow.
- Restructure the backend into clear folders:
  `app/core` (config, logging, security), `app/db` (SQLite + models),
  `app/auth`, `app/events`, `app/access`, `app/assignees`, `app/groq`,
  `app/sheets`, `app/api` (routers), `app/main.py`.
- Config from `.env` (+ `.env.example` in the repo). No secret in code.
- **Logging:** structured lines to stdout **and** a rotating file
  (`logs/app.log`). One `log_event(action, **detail)` helper that also writes an
  `audit_log` row. Passwords / tokens / keys are never logged.
- `GET /health`. Dockerfile + `docker-compose.yml`. README stub.
- **Done when:** `docker compose up` boots, `/health` returns ok, `app.db` and
  `logs/app.log` appear.

### Phase 1 — Login  (M)

- `users` table + password hashing (bcrypt).
- `POST /auth/register` — email + password (min 8), role defaults to `user`,
  duplicate email rejected.
- `POST /auth/login` — JWT valid **7 days**. No refresh token; log in again when
  it expires.
- `GET /auth/me`.
- **Admin seed:** on first boot, if `ADMIN_EMAIL` isn't in the DB, create it
  with `ADMIN_PASSWORD` and role `admin`.
- **Token invalidation without a blocklist:** each request checks the user still
  exists, is active, and hasn't changed their password since the token was
  issued (`password_changed_at`).
- **Rate limits:** login 5/min per IP, register 3/min per IP.
- `forgot-password` / `reset-password` shipped as **stubs** ("email not
  configured yet") — switched on when SMTP creds arrive.
- Audit: `USER_REGISTERED`, `USER_LOGIN`, `LOGIN_FAILED`.
- **Done when:** register → login → `/auth/me` works; wrong password → 401 +
  `LOGIN_FAILED`; the seeded admin can log in.

### Phase 2 — Events & lists  (M)

- `events` table + `assignees` table.
- `POST /events` (admin): name, description, location, organizer, start_date,
  end_date. On create we also:
  1. call the Sheets API to **add a tab** named after the event,
  2. write the header row,
  3. save the tab's numeric id on the event record.
     If the Google call fails, the event is **not** created (no half-state) and the
     admin gets a clear error.
- `GET /events`, `GET /events/{id}`, `PATCH /events/{id}`.
- **Assigned To list:** `GET /assignees` (active names), `POST /assignees` (add),
  `DELETE /assignees/{id}` (soft-remove). Admin-only for add/remove.
- Tab-name sanitisation + uniqueness; event name unique.
- Audit: `EVENT_CREATED`, `EVENT_UPDATED`, `SHEET_TAB_CREATED`,
  `ASSIGNEE_ADDED`, `ASSIGNEE_REMOVED`.
- **Done when:** admin creates "Test Event" → a new tab with the right headers
  shows up in your Google Sheet; admin adds "Priya" and removes "Nitish" and
  `GET /assignees` reflects it.

### Phase 3 — Access control  (M)

- `event_access` table.
- `POST /events/{id}/access` (admin): body = a user's email. The user must have
  registered already; if not, the response says "ask them to register first"
  (invite-by-email can be added later).
- `DELETE /events/{id}/access/{userId}` (admin): revoke.
- `GET /events/{id}/access` (admin): list.
- Dependency `require_event_access(event_id)` on `/scan` and `/leads`:
  logged in → event exists & active → this user is assigned. Admins pass
  automatically.
- `GET /events` now returns only assigned events for non-admins;
  `GET /me/events` feeds the dropdown.
- Audit: `ACCESS_GRANTED`, `ACCESS_REVOKED`, `ACCESS_DENIED`.
- **Done when:** an unassigned user gets 403 on an event; after the admin grants,
  200; after revoke, 403 again; editing the event id in the URL never helps.

### Phase 4 — Groq scan  (M)

- New `app/groq/client.py`.
- Model id from `.env` (`GROQ_MODEL`, default `qwen/qwen3.8-27b` — the one you
  tested). Endpoint, key, timeout from `.env`.
- Flow: image bytes → light resize/cleanup (reused helper) → base64 data URL →
  **non-streaming** `chat.completions.create` → parse JSON (tolerating
  ```json fences) → map to `{name, company, title, email, phone}` → run the
  existing phone/email normalisation.
- **Retry:** one retry with backoff on 429 / 5xx, then a clean error.
- **Global guard:** stay under ~25 calls/minute and ~1,000/day (just below the
  free-tier ceiling). When hit, return `429` with a friendly "limit reached"
  message.
- **Mock mode:** empty `GROQ_API_KEY` → return sample card data (build the
  frontend without spending quota).
- `POST /scan` (auth + event access): multipart `image` + `event_id` → returns
  the fields. **Does not save.**
- Audit: `GROQ_REQUEST`, `GROQ_FAILED`, `RATE_LIMIT_HIT`.
- **Done when:** mock mode returns the sample; with the key, a dummy card returns
  sensible fields.

### Phase 5 — Save to Sheet  (M)

- `app/sheets/writer.py`:
  - one process-wide lock so appends happen one at a time (each append is
    < 1 second; at 10–30 users the queue never grows — unnoticeable, and it
    makes duplicate/overwritten rows impossible);
  - `spreadsheets.values.append` to the event's tab;
  - up to 3 retries with exponential backoff on 429 / 5xx;
  - if every retry fails → return an error. **The client is never told "saved"
    unless the row is really in the Sheet.**
- **Idempotency:** the client sends a `request_id` generated when the review
  screen opens. Same id again within a few minutes → return the first result,
  write nothing new.
- `POST /leads` (auth + event access): body = fields + `event_id` +
  `assigned_to` + `request_id`. `assigned_to` must be a currently-active name.
  Row = `[ISO timestamp, user email, event name, name, company, title, email, phone, notes, assigned_to]`.
- Audit: `LEAD_SUBMITTED`, `SHEET_WRITE_OK`, `SHEET_WRITE_FAILED`,
  `DUPLICATE_IGNORED`.
- **Done when:** a save puts one correct row in the right tab; a double submit
  with the same `request_id` still yields one row; a forced Sheet failure shows
  the user a real error.

### Phase 6 — Frontend wiring  (M)

- `lib/config.js`: API base URL from a Vite env var → the new backend.
- **New `Login` screen:** email + password, with a "create account" toggle.
  Store the JWT (memory + `localStorage`); `lib/api.js` attaches
  `Authorization: Bearer …` to every call; any `401` → back to Login.
- **New `EventPicker` screen:** dropdown from `GET /me/events`; the choice is
  kept in app state and sent with `/scan` and `/leads`. If the user is assigned
  to nothing, show "ask your admin for access".
- **`Review` screen:**
  - remove the confidence / amber "please verify" logic (no confidence scores);
  - keep the **Assigned To** dropdown, but populate it from `GET /assignees`
    (admin-managed) instead of a fixed list;
  - plain editable fields + the Notes box.
- On save: send `event_id` + `assigned_to` + a generated `request_id`.
- **Admin screens (minimal):** create/list events, add/remove Assigned To names,
  grant/revoke event access by email. Plain forms — no design polish.
- **Done when:** a full run works on your phone via ngrok: login → pick event →
  scan a card → review (pick Assigned To) → save → row in the Sheet.

### Phase 7 — Docs + deploy  (S)

- `README.md` (run locally, env vars, architecture), `DEPLOY.md`
  (Render now; small-VM + Docker steps for later), Postman collection covering
  every endpoint, complete `.env.example`.
- Security pass: no secrets in the repo, `.env` git-ignored, CORS locked to the
  frontend URL, rate limits on, logs checked for leaks.
- Deploy to Render, do one full run against the public URL.

---

## 6. Environment variables


| Var                                                                 | Example                 | Used for                                   |
| ------------------------------------------------------------------- | ----------------------- | ------------------------------------------ |
| `APP_ENV`                                                           | `dev` / `prod`          | log verbosity, CORS strictness             |
| `DATABASE_URL`                                                      | `sqlite:///./app.db`    | SQLite file location                       |
| `JWT_SECRET`                                                        | (random 32+ chars)      | signing login tokens                       |
| `JWT_EXPIRES_DAYS`                                                  | `7`                     | token lifetime                             |
| `ADMIN_EMAIL`                                                       | `you@company.com`       | seed admin on first boot                   |
| `ADMIN_PASSWORD`                                                    | (strong)                | seed admin password                        |
| `GROQ_API_KEY`                                                      | `gsk_…`                | Groq auth (blank → mock mode)             |
| `GROQ_MODEL`                                                        | `qwen/qwen3.8-27b`      | which Groq model                           |
| `GROQ_MAX_PER_MIN` / `GROQ_MAX_PER_DAY`                             | `25` / `1000`           | stay under the free tier                   |
| `GOOGLE_SERVICE_ACCOUNT_FILE`                                       | `./secrets/gsa.json`    | Sheets API auth (mounted, never committed) |
| `GOOGLE_SHEET_ID`                                                   | `1AbC…`                | the one spreadsheet                        |
| `TIMEZONE`                                                          | `Asia/Kolkata`          | how the Timestamp column is written        |
| `CORS_ORIGINS`                                                      | `https://your-frontend` | who may call the API from a browser        |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASS` / `SMTP_FROM` | (Brevo)                 | forgot-password (+ later, thank-you email) |

---

## 7. Things YOU need to set up

Ordered by when they're needed.

### 7.1  GitHub repo  — before Phase 0  ✅ decided

- Repo **`card2lead`**, **public**, under **`Shiti-Sharma09`**
  (<https://github.com/Shiti-Sharma09/card2lead>).
- Feature branch + PR per phase.

### 7.2  Admin login  — before Phase 1  ✅ decided

- `ADMIN_EMAIL = card.admin@gmaail.com`  (as given — see note)
- `ADMIN_PASSWORD = Test@2003`
- These live **only** in `.env` (git-ignored) and Render's env settings — never
  in the code, especially with a **public** repo.
- Notes: the email is written `gmaail.com` (double "a"); it works fine as a
  login id, but "forgot password" would need a real mailbox — change it later if
  that matters. Recommend changing `ADMIN_PASSWORD` after first login.

### 7.3  Google Cloud + the Sheet  — before Phase 2

1. Go to **console.cloud.google.com** → create a **new project** (free, **no
   billing needed**).
2. **APIs & Services → Library** → open **Google Sheets API** → **Enable**.
   *(Drive API is NOT needed — we only add tabs to one existing sheet.)*
3. **APIs & Services → Credentials → Create credentials → Service account** →
   give it any name → **Create and continue** → skip roles → **Done**.
4. Click the new service account → **Keys → Add key → Create new key → JSON** →
   a `.json` file downloads. **Send me that file.**
5. Create **one Google Sheet** in your Google Drive. From its URL,
   `docs.google.com/spreadsheets/d/`**`THIS_LONG_ID`**`/edit` — **send me that
   ID**.
6. In the Sheet → **Share** → paste the service account's email (looks like
   `name@project-id.iam.gserviceaccount.com`, it's in the JSON) → set to
   **Editor** → Send. Keep the Sheet shared with your own Google account so you
   can watch rows land.

- Cost: none. Sheets API free quota (~300 writes/min) is far above our ~25/min.

### 7.4  Groq  — for Phase 4

- Key already received — it goes in `.env` only, never in the repo.
- **Please rotate it once more before the real deployment** (it has been shared
  in chat). New key → just send it.
- The free tier is **1,000 cards/day / 30 per minute**. Fine for dummy-card
  testing. For a real event that might exceed 1,000 scans in a day, add a small
  paid Groq plan beforehand.

### 7.5  Render (test hosting)  — before Phase 7

1. **render.com** → sign up **with your GitHub account** (no credit card).
2. **New → Web Service** → connect the repo → pick the branch.
3. Runtime: **Docker** (we provide the Dockerfile).
4. In the Render dashboard → **Environment** → add every var from
   `.env.example` (I'll give you the exact values to paste).
5. Render gives a public **`https://<name>.onrender.com`** URL — that's the app.

- Known free-tier limits: it **sleeps after ~15 min idle** (first request after
  is slow, ~30–60 s) and **SQLite resets on each redeploy** — the admin is
  re-created automatically from `.env`, and leads are safe because they live in
  the Google Sheet. Move to a small always-on VM before the real event
  (`DEPLOY.md` will have the steps).

### 7.6  Brevo (email/SMTP)  — any time; not blocking

Only needed for "forgot password" (and later the optional thank-you email).
Password login works without it.

1. Sign up at **brevo.com** (free).
2. **Senders, Domains & Dedicated IPs → Senders** → add and **verify a sender
   email you control**.
3. **SMTP & API → SMTP** → note the **host** (`smtp-relay.brevo.com`),
   **port** (`587`), **login**, and the **SMTP key**.
4. Send me those 4 values (or paste them into Render's environment yourself).

- Free tier: 300 emails/day.

---

## 8. Login & email — the agreed approach

- **Now:** self-register with email + password (min 8). Password login. A
  registered account has **no event access** until an admin grants it, so open
  registration is safe.
- **Forgot password:** email OTP — a stub in Phase 1, switched on when Brevo
  creds arrive. Blocks nothing else.
- **Thank-you email to the person on the card:** written but **commented out**
  for now (you're testing with dummy cards).

---

## 9. Testing approach ****(no load test — your call)

- **Per phase:** a short script or Postman run proving that phase's "Done when"
  line, committed with the code.
- **Auth / access:** automated checks — unassigned user blocked, revoke works,
  URL tampering fails, wrong password logged.
- **Groq:** mock-mode check runs with no key; one manual real-card check.
- **Sheet writer:** automated checks for the duplicate-submit guard and for
  "failure returns an error, not a success".
- **End to end:** manual run on your phone via ngrok at the end of Phase 6, then
  again against the live Render URL in Phase 7.

---

## 10. Risks & things to watch


| Risk                                                                               | Effect                                                                                                | Plan                                                                                         |
| ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Groq free tier =**1,000 cards/day**, 30/min                                        | Scans stop mid-event if exceeded                                                                      | Friendly limit message; add a small paid tier before the real event                          |
| `qwen/qwen3.8-27b` may behave differently over the API than in the Groq playground | Extraction quality varies                                                                             | Model id in`.env`; test with real dummy cards early in Phase 4                               |
| Render free tier wipes SQLite on redeploy / sleeps when idle                       | Lose events, assignments and assignee names (not leads — those are in the Sheet); slow first request | Admin re-seeded from`.env`; move to a small VM before the event                              |
| One shared spreadsheet                                                             | Anyone with the link sees every event's tabs                                                          | Share it only with the right people; separate spreadsheet*files* per event is a later option |
| Groq key shared in chat                                                            | Could be misused                                                                                      | Rotate once more before production                                                           |
| No SMTP yet                                                                        | "Forgot password" inactive                                                                            | Password login works without it; add Brevo any time                                          |

---

## 11. Explicitly out of scope (keeping it lean)

Separate spreadsheet *files* per event · a real database server (Postgres/Mongo)
· Redis / queues / background workers · refresh tokens / token blocklist /
sessions table · autoscaling / load balancer / Kubernetes · serverless (Lambda)
· confidence scores + "please verify" UI · storing card images · Drive API /
creating spreadsheets in code · per-event email templates · load testing.

---

## 12. Locked decisions


| #                | Decision                                                                                                 |
| ---------------- | -------------------------------------------------------------------------------------------------------- |
| Repo             | `card2lead`, **public**, under `Shiti-Sharma09`; branch + PR per phase                                   |
| Admin seed       | `card.admin@gmaail.com` / `Test@2003` (in `.env` + Render only)                                          |
| `assigned_to`    | **required** on every save                                                                               |
| Assigned To list | **global** — one list for all events                                                                    |
| Starting names   | seed with`NITISH`, `HARSHAD` (admin can add/remove after)                                                |
| Frontend hosting | **one Render service** serves the built React app **and** the API from a single URL — no CORS to manage |
| Sheet columns    | the 10 below, in this order, nothing extra                                                               |
| Timestamp        | written in IST (`Asia/Kolkata`)                                                                          |
| Event names      | must be unique (each becomes a Sheet tab)                                                                |
| No-access user   | sees an empty event picker + "ask your admin for access"                                                 |

**The 10 Sheet columns (per event tab):**


| #  | Column      | Filled by                                         |
| -- | ----------- | ------------------------------------------------- |
| 1  | Timestamp   | server (IST)                                      |
| 2  | User Email  | server (logged-in user)                           |
| 3  | Event       | server (the tab / selected event)                 |
| 4  | Name        | Groq → user can edit on review                   |
| 5  | Company     | Groq → editable                                  |
| 6  | Title       | Groq → editable                                  |
| 7  | Email       | Groq → editable                                  |
| 8  | Phone       | Groq → editable                                  |
| 9  | Notes       | user types on review                              |
| 10 | Assigned To | user picks from the admin-managed list (required) |

### Still needed later (not blocking the start)

- **Phase 2:** the Google service-account **JSON** + the **Sheet ID**
  (create the Google project + Sheet per §7.3; hand me the JSON as a file at
  that point — don't paste it in chat, it's a credential).
- **Phase 4:** the **re-rotated Groq key** (the current one has been shared in
  chat).

**Ready to start Phase 0 + 1 on your "go".**
