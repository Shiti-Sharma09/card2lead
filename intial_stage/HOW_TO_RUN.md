# How to run the initial-stage project (CARD2LEAD)

This is a **frozen snapshot** of the first version we built:
React + Vite frontend, FastAPI backend, **Google Gemini** for card reading,
data written to a local **Excel** file (`backend/data/leads_master.xlsx`).

It is kept here for reference only. Active work continues in the project root
(new standalone backend: Groq + Google Sheets + auth). Nothing here is wired to
the new backend.

> First run creates `backend/.venv`, installs dependencies, and copies
> `backend/.env.example` to `backend/.env`. With **no Gemini key** the app runs
> in **mock mode** (returns sample card data) — the whole flow still works.
> To use real extraction, put a key in `backend/.env` → `GEMINI_API_KEY=...`
> (get one at https://aistudio.google.com/apikey).

---

## A. Test on your computer

```powershell
cd "C:\Users\Shiti Sharma\OneDrive - Antino\Desktop\referral_card\intial_stage"
```

Open **two PowerShell windows**:

```powershell
# window 1  - backend API on http://localhost:8000
.\scripts\start-backend.ps1
```

```powershell
# window 2  - frontend on http://localhost:5173 (proxies /api -> :8000)
.\scripts\start-frontend.ps1
```

Then open **http://localhost:5173** in your browser.
Upload a card image → Review → **Save**. The row is appended to
`backend/data/leads_master.xlsx`.

---

## B. Test on your phone (camera needs HTTPS → use ngrok)

### One-time ngrok setup

```powershell
ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN
```

(Generic form: `ngrok config add-authtoken YOUR_TOKEN`)

### Run it

```powershell
cd "C:\Users\Shiti Sharma\OneDrive - Antino\Desktop\referral_card\intial_stage"
```

Open **two PowerShell windows**:

```powershell
# window 1  - build the frontend and serve app + API together from :8000
.\scripts\build-and-serve.ps1
```

```powershell
# window 2  - expose :8000 over HTTPS
ngrok http 8000
```

ngrok prints a line like:

```
Forwarding   https://abc123.ngrok-free.app  ->  http://localhost:8000
```

Open that **https://…ngrok-free.app** link **on your phone**.
Tap **Open Camera**, allow the camera, photograph a card, then go through
**Review → Save**.

---

## C. Run the tests (optional)

```powershell
cd "C:\Users\Shiti Sharma\OneDrive - Antino\Desktop\referral_card\intial_stage"
.\scripts\test-all.ps1
```

Or a single suite:

```powershell
cd backend
.\.venv\Scripts\python.exe tests\qa_offline.py     # 34 checks, no Gemini key needed
.\.venv\Scripts\python.exe tests\qa_live.py        # HEIC + concurrency
.\.venv\Scripts\python.exe tests\sample_cards.py   # prints extraction for 4 sample cards
```

---

## What each script does

| Script | What it does |
|---|---|
| `scripts/start-backend.ps1` | API on `:8000` with `--reload`; first run creates `backend/.venv`, installs, copies `.env` |
| `scripts/start-frontend.ps1` | Vite dev server on `:5173`, proxies `/api/*` → `:8000` |
| `scripts/build-and-serve.ps1` | `npm run build`, then FastAPI serves the built app **and** the API from `:8000` (single origin, for `ngrok http 8000`) |
| `scripts/test-all.ps1` | Full suite: compile-all, import check, `qa_offline`, `qa_live`, `sample_cards`, frontend build |
