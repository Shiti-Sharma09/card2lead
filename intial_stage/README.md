# CARD2LEAD

Business-card OCR lead capture. Photograph a card → Gemini reads the fields →
you review/correct → the lead is appended to a master Excel file.

Built to the spec in [`requirements.txt`](requirements.txt) and the decisions in
[`questions_for_shiti.txt`](questions_for_shiti.txt). Execution plan:
[`plan.md`](plan.md).

---

## What works right now (before the Gemini key)

The app runs in **mock mode** when `GEMINI_API_KEY` is empty: `/api/extract`
returns realistic sample data so you can test the entire flow —
camera → blur gate → review screen → Excel write. Drop the key in later and it
switches to real extraction with **no code changes**.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.10+ | `py --version` |
| Node.js | 18+ | `node --version` |
| ngrok | any | only for phone testing; `ngrok config add-authtoken <token>` once |

---

## Run it (development — two terminals)

```powershell
# Terminal 1 — API on http://localhost:8000
./scripts/start-backend.ps1

# Terminal 2 — web app on http://localhost:5173
./scripts/start-frontend.ps1
```

Open <http://localhost:5173>. The dev server proxies `/api/*` to the backend.
Camera works on `localhost` without HTTPS.

> First run creates `backend/.venv`, installs dependencies, and copies
> `backend/.env.example` → `backend/.env`.

## Run it on your phone (ngrok — one terminal + tunnel)

```powershell
# Terminal 1 — builds the frontend, serves app + API together on :8000
./scripts/build-and-serve.ps1

# Terminal 2
ngrok http 8000
```

Open the `https://….ngrok-free.app` URL on your phone. One origin, so the
camera (which needs HTTPS off localhost) works and there is no CORS to configure.

> ngrok's free URL changes on every restart. A free **reserved domain**
> (ngrok dashboard → Domains) gives you a stable link:
> `ngrok http --domain=your-name.ngrok-free.app 8000`.

---

## Add the Gemini key (when you have it)

1. Get a key at <https://aistudio.google.com/apikey> (free tier is fine to start).
2. Edit `backend/.env`:
   ```
   GEMINI_API_KEY=your_key_here
   ```
3. Restart the backend. Check <http://localhost:8000/api/health> —
   `"mock_mode": false` means it's live.

---

## Where the leads go

`backend/data/leads_master.xlsx` — created automatically on the first save.
One row per lead:

| Name | Company | Title | Email | Phone Number | Notes | Assigned To | Timestamp |
|------|---------|-------|-------|--------------|-------|-------------|-----------|

- **Keep this file closed while capturing.** If it's open in Excel the save
  fails with a clear "close it and press Save again" message — no data is lost.
- Every save is a new row (no duplicate detection, by design).
- Change the location with `EXCEL_PATH` in `backend/.env`.

---

## Configuration (`backend/.env`)

| Var | Default | Purpose |
|-----|---------|---------|
| `GEMINI_API_KEY` | *(empty)* | empty → mock mode |
| `GEMINI_MODEL` | `gemini-2.5-flash` | swap model without code change |
| `EXCEL_PATH` | `data/leads_master.xlsx` | master file location (relative to `backend/`) |
| `ASSIGNEES` | `NITISH,HARSHAD` | **the Assign dropdown** — add names here, comma-separated |
| `CONFIDENCE_THRESHOLD` | `95` | fields below this self-reported score get an amber "please verify" flag |
| `BLUR_THRESHOLD` | `120` | backend sharpness gate for uploaded photos |
| `CORS_ORIGINS` | `*` | fine for single-user ngrok |
| `MAX_UPLOAD_MB` | `12` | reject bigger uploads |

Frontend blur cutoff: `VITE_BLUR_THRESHOLD` in `frontend/.env` (defaults to 120).
The frontend and backend thresholds are **independent** — they run on different
image scales, so tune them separately on a handful of real cards.

---

## Project layout

```
backend/          FastAPI app
  app/
    main.py           routes + static frontend mount
    config.py         env config
    models.py         request/response schemas
    routes/           /api/extract, /api/leads
    services/         image_ops · gemini_client · normalize · excel_store
frontend/         React + Vite + Tailwind SPA
  src/
    App.jsx           screen flow (landing → camera → processing → review → success)
    screens/          Landing · Camera · Review · Success · Blurry
    lib/              api.js · blur.js (client sharpness check) · config.js
    components/        Field · AssignSelect · Toast · Spinner · Logo
scripts/          PowerShell helpers
```

---

## API

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/extract` | multipart `image` → `{ blurry, mock, fields, confidence }` |
| `POST` | `/api/leads` | reviewed lead JSON → appends a row; `409` if the file is open |
| `GET`  | `/api/health` | mock-mode / model / paths |
| `GET`  | `/api/config` | values the frontend reads on startup |

Interactive docs while the backend runs: <http://localhost:8000/docs>

---

## Not in this phase (see `plan.md` §8)

Outlook login · AWS/on-prem deploy · referral backend API · saving the card
image · multi-user concurrent Excel writes · offline queue · multi-card photos ·
non-English cards.
