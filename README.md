# card2lead

Event-based business-card lead capture.

An authorised user logs in, picks an **event**, photographs a business card
(read by **Groq**), reviews the fields, and saves them as a row in a
**Google Sheet** — one tab per event. An **admin** creates events, controls who
can access each one, and manages the "Assigned To" name list.

- **Backend:** Python / FastAPI, SQLite for metadata (users, events, access,
  audit log), Google Sheets for the leads themselves.
- **Frontend:** React / Vite (wired in Phase 6).
- **Plan:** see [`plan.md`](plan.md). Rationale: [`suggestions.md`](suggestions.md).
- **First prototype (frozen, reference only):** [`intial_stage/`](intial_stage/).

## Status

| Phase | What | State |
|---|---|---|
| 0 | Skeleton (config, logging, SQLite, `/health`, Docker) | ✅ |
| 1 | Auth (register, login, JWT, admin seed, rate limits) | ✅ |
| 2 | Events + Assigned To list | ⏳ |
| 3 | Per-event access control | ⏳ |
| 4 | Groq card extraction | ⏳ |
| 5 | Save to Google Sheet | ⏳ |
| 6 | Frontend wiring | ⏳ |
| 7 | Docs + deploy (Render) | ⏳ |

## Run the backend locally

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate      macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit .env (at least ADMIN_PASSWORD)
uvicorn app.main:app --reload --port 8000
```

- Health check: <http://localhost:8000/health>
- API docs (dev): <http://localhost:8000/docs>

### With Docker

```bash
cp backend/.env.example backend/.env   # edit it
docker compose up --build
```

## Tests

```bash
cd backend
pip install pytest
python -m pytest -q
```

## Configuration

All config is via environment variables — see
[`backend/.env.example`](backend/.env.example) for the full list and notes.
`.env` and any credential files are git-ignored; nothing secret is committed.
