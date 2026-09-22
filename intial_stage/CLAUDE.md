# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**CARD2LEAD** — photograph a business card → Google Gemini reads the 5 fields
(name, company, title, email, phone) → user reviews/corrects → the lead is
appended as one row to a master `.xlsx`. Single-user, run off a laptop and
exposed to a phone over an ngrok HTTPS tunnel. Scope decisions live in
`plan.md` and `questions_for_shiti.txt`; code comments cite those as `AQ1`, `AQ7`, etc.

Environment is **Windows + PowerShell**. The repo root is not a git repo.

## Commands

All helper scripts are in `scripts/` and are run from the repo root.

```powershell
./scripts/start-backend.ps1      # API on :8000 with --reload; first run creates backend/.venv, installs, copies .env
./scripts/start-frontend.ps1     # Vite dev server on :5173, proxies /api/* -> :8000
./scripts/build-and-serve.ps1    # npm run build, then FastAPI serves app + API from :8000 (single origin for `ngrok http 8000`)
./scripts/test-all.ps1           # full suite: compileall, import check, qa_offline, qa_live, sample_cards, frontend build
```

Tests are **plain scripts, not pytest** (exit 0 = pass). Run one directly:

```powershell
cd backend
./.venv/Scripts/python.exe tests/qa_offline.py     # 34 assertions, no Gemini key needed
./.venv/Scripts/python.exe tests/qa_live.py        # HEIC + concurrency; real-Gemini checks auto-skip with no key
./.venv/Scripts/python.exe tests/sample_cards.py   # prints extraction + per-field confidence for 4 sample cards
```

Frontend build only: `cd frontend; npm run build`. There is no frontend lint/test setup.

## Mock mode (important)

When `GEMINI_API_KEY` is empty, `Settings.mock_mode` is true and `/api/extract`
returns realistic sample data. **The entire flow — camera, blur gate, review,
Excel write — works with no key.** Adding the key later switches to real
extraction with no code changes. `GET /api/health` reports `mock_mode`.

## Architecture

### Backend (`backend/app/`, FastAPI, sync route handlers)

Route handlers are `def` not `async def` on purpose — Starlette runs them in a
threadpool so blocking OpenCV/Gemini/openpyxl work never stalls the event loop.

- **`POST /api/extract`** (`routes/extract.py`): read bytes → reject empty / over
  `MAX_UPLOAD_MB` / undecodable → server-side sharpness gate (`image_ops.sharpness_score`
  vs `BLUR_THRESHOLD`) → `image_ops.light_cleanup` (orient/resize/denoise/CLAHE/mild
  deskew only — no perspective crop, per AQ7) → `gemini_client.extract_fields`
  (or mock) → `normalize` (phone forced to `+91 …`, emails lowercased+deduped,
  multiple values joined by comma) → `ExtractResponse` with per-field confidence 0–100.
- **`POST /api/leads`** (`routes/leads.py`): `LeadRequest` → **all 7 fields
  required** (`name, company, title, email, phone, notes, assignedTo`) else `422`
  → `excel_store.append_lead`. Returns `409` when the file is locked (open in
  Excel) — the frontend surfaces "close it and press Save again".
- **`GET /api/health`**, **`GET /api/config`**: `/config` is what the frontend
  reads on startup (app name, assignees list, confidence threshold, mock flag).

### Cross-cutting backend details

- **`services/excel_store.py`**: all writes serialized through a process-wide
  `threading.Lock`. Safe for the single-process server only; a multi-worker or
  multi-machine deploy would additionally need a cross-process file lock.
  `_safe_cell` strips a leading `= + - @` so a card value like `=cmd()` can't
  become a live Excel formula.
- **`services/gemini_client.py`**: one vision call returns strict JSON (`fields` +
  `confidence`). Prompt forbids guessing — unreadable field → `""` and confidence 0.
- **`config.py`**: `get_settings()` returns one `@lru_cache`d `Settings`, loaded
  from `backend/.env` via python-dotenv. `EXCEL_PATH` is resolved relative to
  `backend/` when not absolute.
- **`main.py`**: if `frontend/dist/` exists it is mounted at `/` (mounted **last**
  so it never shadows `/api`). This is what lets one ngrok tunnel serve both —
  no CORS to configure.

### Frontend (`frontend/src/`, React 18 + Vite 5 + Tailwind 3, no TypeScript)

`App.jsx` is a single state machine over one `screen` string:
`landing → camera | (upload) → processing → (blurry | review) → success`.

- `lib/blur.js` runs a **client-side** sharpness check before upload;
  `lib/image.js` downscales to JPEG. The client and server blur thresholds are
  **independent and tuned separately** — they run on different image scales.
- `lib/api.js` is the only place that talks to the backend (`/api/extract`,
  `/api/leads`, `/api/config`).
- The captured image is held in memory (object URL) and **never uploaded to disk
  storage or persisted** (AQ: card image is in-memory only).

## Configuration

`backend/.env` (copy from `.env.example`):

| Var | Default | Effect |
|---|---|---|
| `GEMINI_API_KEY` | *(empty)* | empty → mock mode |
| `GEMINI_MODEL` | `gemini-2.5-flash` | swap model, no code change |
| `EXCEL_PATH` | `data/leads_master.xlsx` | master file, relative to `backend/` |
| `ASSIGNEES` | `NITISH,HARSHAD` | **is** the Assign dropdown; comma-separated |
| `CONFIDENCE_THRESHOLD` | `95` | fields below get the amber "please verify" flag |
| `BLUR_THRESHOLD` | `120` | server sharpness gate |
| `MAX_UPLOAD_MB` | `12` | reject larger uploads |
| `CORS_ORIGINS` | `*` | fine for single-user ngrok |

Frontend: `VITE_BLUR_THRESHOLD` (client blur cutoff), `VITE_API_PROXY` (dev proxy target).

`backend/data/` (the leads file) and both `.env` files are gitignored.

## `_deployed-backend-ref/` — reference only, do not run as part of this app

A checked-in copy (with its own `.git`) of a separate **existing production
backend**: Node/Express + MongoDB/Mongoose, Google Vision + Document AI, Zoho CRM
SDK, JWT auth, node-cron. Per `new_requirements.txt` and `new_question_for_shiti.txt`
the planned next phase is to **integrate this FastAPI app into that Node backend**,
reusing its auth, user/employee access control, DB models, and API conventions
rather than shipping a parallel service. Treat it as the integration target and
source of existing patterns, not as code to modify casually.
