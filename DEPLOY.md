# Deploying card2lead

One Docker image serves **both** the React app and the API on a single port.
Render builds it straight from the `Dockerfile` at the repo root.

---

## Option A — Render (recommended for now)

No credit card. Gives a public HTTPS URL.

### 1. Create the service

1. Go to <https://render.com> and sign up **with GitHub**.
2. **New → Web Service** → connect `Shiti-Sharma09/card2lead` → pick the branch
   (`main` once the phase PRs are merged).
3. **Runtime: Docker.** Leave build/start commands blank — the `Dockerfile`
   handles both.
4. Instance type: **Free**.

### 2. Environment variables

In the service's **Environment** tab, add:

| Key | Value |
|---|---|
| `APP_ENV` | `prod` |
| `JWT_SECRET` | a long random string — `python -c "import secrets;print(secrets.token_urlsafe(48))"` |
| `ADMIN_EMAIL` | `card.admin@gmail.com` |
| `ADMIN_PASSWORD` | a strong password |
| `GROQ_API_KEY` | your Groq key (leave unset for mock mode) |
| `GROQ_MODEL` | `qwen/qwen3.8-27b` |
| `GOOGLE_SHEET_ID` | your sheet id |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | `/etc/secrets/gsa.json` |
| `TIMEZONE` | `Asia/Kolkata` |
| `CORS_ORIGINS` | your Render URL, e.g. `https://card2lead.onrender.com` (or leave `*` — the app and API share an origin anyway) |

### 3. The Google service-account key

Render → the service → **Environment → Secret Files** →
**Add Secret File**:

- **Filename:** `/etc/secrets/gsa.json`
- **Contents:** paste the whole JSON key file

(That's why `GOOGLE_SERVICE_ACCOUNT_FILE` above points at `/etc/secrets/gsa.json`.)

### 4. Deploy & check

- Render builds and starts it. Open `https://<name>.onrender.com/health` →
  `{"status":"ok", ...}`.
- Open `https://<name>.onrender.com/` → the login screen.
- Log in as the admin, create an event, grant yourself access, scan a card.

### Free-tier caveats

- **Sleeps after ~15 min idle** — the first request after that takes 30–60 s.
- **SQLite resets on every redeploy.** Leads are safe (they live in the Google
  Sheet); the admin is re-created automatically from the env vars, but events,
  access grants and any added assignee names have to be re-entered. Move to
  Option B before a real event.

---

## Option B — a small always-on VM (before a real event)

Any tiny Linux box with Docker (an always-free cloud VM, or a cheap VPS).

```bash
git clone https://github.com/Shiti-Sharma09/card2lead.git
cd card2lead

# secrets — never committed
mkdir -p backend/secrets
#   put the Google key at backend/secrets/gsa.json
cp backend/.env.example backend/.env
#   edit backend/.env: APP_ENV=prod, a real JWT_SECRET, ADMIN_*, GROQ_API_KEY,
#   GOOGLE_SHEET_ID, and DATABASE_URL=sqlite:///./data/app.db

docker compose up -d --build      # -> http://<server>:8000
```

- `docker compose` keeps SQLite on a named volume, so nothing resets across
  restarts or rebuilds.
- Put nginx / Caddy in front for HTTPS, or use the provider's load balancer.
- Update: `git pull && docker compose up -d --build`.

---

## What DevOps / whoever hosts it needs

| Thing | Value |
|---|---|
| Build | the root `Dockerfile` (multi-stage: builds the React app, then the API image) |
| Start | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (the image's `CMD`) |
| Port | `$PORT` (Render sets it) or `8000` |
| Persistent storage | a volume for SQLite if resets aren't acceptable (`DATABASE_URL=sqlite:///./data/app.db` + mount `/app/data`) |
| Secret file | the Google service-account JSON, path in `GOOGLE_SERVICE_ACCOUNT_FILE` |
| Env vars | see the table in Option A |
| External services | Groq API (outbound HTTPS), Google Sheets API (outbound HTTPS) |
| Health check | `GET /health` → 200 |

## Rotating a secret

- **Groq key:** change `GROQ_API_KEY`, redeploy.
- **Admin password:** change `ADMIN_PASSWORD`, redeploy — it re-syncs on boot.
- **JWT secret:** change `JWT_SECRET`, redeploy — everyone is logged out.
- **Google key:** replace the secret file, redeploy.
