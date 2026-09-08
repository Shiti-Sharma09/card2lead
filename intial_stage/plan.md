# CARD2LEAD — Execution Plan

Project: Business Card OCR Lead Capture Application
**Date:** 2026-09-03
**Target for this phase:** Working app used by 1 person (you), shared to your phone over an ngrok HTTPS tunnel, storing leads in one master Excel file.
**Timeline:** 2 working days (~20 hrs)

---

## 1. Plan at a Glance

### 1.1 Decisions locked in (from `questions_for_shiti.txt`)


| Area                   | Decision                                                                           |
| ---------------------- | ---------------------------------------------------------------------------------- |
| App type               | Mobile-friendly**web app** (React SPA), opened in the phone browser                |
| Frontend               | React + Vite + Tailwind CSS                                                        |
| Backend                | Python + FastAPI                                                                   |
| Camera                 | Browser camera (`getUserMedia`) **+** "Upload from gallery" option                 |
| Blur check             | If the photo is blurry/shaky →**force a retake** (no "use anyway")                |
| Cards per photo        | Exactly 1                                                                          |
| Image cleanup          | **Light only** — orient, resize, denoise, auto-contrast, mild deskew              |
| Card image             | Held in memory only,**never saved** to disk                                        |
| OCR / extraction       | **Google Gemini 2.5 Flash** (vision → structured JSON in one call)                |
| Fields                 | Name, Company, Title, Email, Phone (5 only)                                        |
| Multiple phones/emails | Joined into one field, comma-separated                                             |
| Phone format           | Normalized to a single style with**`+91` prefix** every time                       |
| Confidence             | Gemini self-rates each field 0–100;**< 95 → amber "please verify"**              |
| Review screen          | Editable form**with the captured card image shown beside it**                      |
| Required to save       | **All fields** (Name, Company, Title, Email, Phone, Notes, Assign)                 |
| Notes                  | Free-text area                                                                     |
| Assign                 | Dropdown`NITISH`, `HARSHAD` (config list, extendable), **no default**              |
| Metadata               | Capture**timestamp** stored with each lead                                         |
| Storage                | One master`.xlsx` on the backend machine; **1 row per lead**; duplicates = new row |
| Excel retrieval        | You open the file off disk yourself (no in-app download needed)                    |
| Auth                   | None for now (link is enough)                                                      |
| Hosting now            | Laptop +**ngrok** HTTPS tunnel                                                     |
| Branding               | App name**CARD2LEAD**, clean text logo, free hand on visual polish                 |

### 1.2 Build phases


| # | Phase                       | Main deliverable                                                                                                 | Est. |
| - | --------------------------- | ---------------------------------------------------------------------------------------------------------------- | ---- |
| 0 | Project setup               | Repo, frontend + backend scaffold, Gemini key wired, run scripts, ngrok                                          | 2 hr |
| 1 | Capture screen              | Landing page, live camera, capture-to-image, upload option, client blur check → retake gate                     | 3 hr |
| 2 | Extraction API              | `/api/extract`: image cleanup (OpenCV) → Gemini → structured JSON + per-field confidence + phone normalization | 4 hr |
| 3 | Review / Edit screen        | Pre-filled form, card image panel, amber low-confidence flags, Notes, Assign dropdown, all-required validation   | 4 hr |
| 4 | Save to Excel               | `/api/leads`: create master file w/ headers if missing, append row, handle "file is open" error, success screen  | 2 hr |
| 5 | Polish & error states       | CARD2LEAD branding, mobile layout, spinners, error toasts, retry buttons                                         | 3 hr |
| 6 | Real-device test + handover | End-to-end test on phone via ngrok, tune blur threshold + prompt on 5–10 real cards, write README               | 2 hr |

### 1.3 Two-day split


| Day       | Phases            | Goal at end of day                                                                            |
| --------- | ----------------- | --------------------------------------------------------------------------------------------- |
| **Day 1** | 0, 1, 2, start 3  | Can capture a card on the phone and see Gemini-extracted fields come back                     |
| **Day 2** | finish 3, 4, 5, 6 | Full flow works end-to-end; a reviewed lead lands as a row in`leads_master.xlsx`; README done |

---

## 2. How the App Works (end-to-end)

```
 Phone browser (React SPA)
   |
   |  1. Landing screen: "CARD2LEAD" + [ Open Camera ] + [ Upload photo ]
   v
 Camera screen: live video -> user snaps -> frame captured to an in-memory image
   |
   |  2. Client-side sharpness check (variance-of-Laplacian on a small canvas)
   |       blurry?  --yes-->  "Image looks blurry. Please retake." [ Retake ]   (hard gate)
   |       sharp?   --------> continue
   v
 POST /api/extract   (multipart: the image)
   |
 FastAPI backend
   |  3. Light cleanup with OpenCV: fix orientation, resize, denoise, CLAHE contrast, mild deskew
   |  4. Backend sharpness guard (safety net) -> if blurry, return {blurry:true}
   |  5. Call Gemini 2.5 Flash with a strict JSON instruction + the cleaned image
   |  6. Parse JSON -> { name, company, title, email, phone, confidence:{...} }
   |  7. Normalize: phone -> "+91 ..." style, email -> trimmed/lowercased
   v
 Response JSON back to the browser (image itself is discarded server-side)
   |
   v
 Review / Edit screen
   |  - Left: the captured card image (from browser memory)
   |  - Right: form pre-filled with the 5 fields
   |  - Any field with confidence < 95 is highlighted amber: "Please verify"
   |  - Missing field = empty box + "Not detected - please fill"
   |  - Notes (textarea)   +   Assign (dropdown: NITISH / HARSHAD, nothing pre-selected)
   |  - [ SAVE ] is disabled until every field is filled and email/phone look valid
   v
 POST /api/leads   (final reviewed values as JSON; no image)
   |
 FastAPI backend
   |  8. Validate all required fields present
   |  9. Open leads_master.xlsx (create with header row if it doesn't exist)
   |  10. Append one row, save, close
   |       file locked (open in Excel)? -> return a clear error; user closes file, hits Save again
   v
 Success screen: "Lead saved for {ASSIGNEE}"  +  [ Capture another ]
```

`★ Insight ─────────────────────────────────────`

- **Why the image never touches disk:** you asked for it to be thrown away after OCR. Keeping it purely in RAM during the request (and only in the browser for the review screen) means there is no cleanup job to write, no storage to fill up, and no privacy surface to worry about later.
- **Why one Gemini call instead of OCR + parser:** a plain OCR API returns a wall of text and we'd still have to guess which line is the name vs. the title. A vision LLM reads the layout and returns labelled fields directly, which is what makes "any card format, any font" realistic in a 2-day build.
- **Why a hard retake gate:** blur is the #1 cause of bad extractions. Catching it on-device (before any upload or API cost) and refusing to proceed keeps garbage out of the pipeline entirely.
  `─────────────────────────────────────────────────`

---

## 3. Architecture & Repo Layout

```
referral_card/
├─ requirements.txt              # original spec (unchanged)
├─ questions_for_shiti.txt       # Q&A (unchanged)
├─ plan.md                       # this file
├─ README.md                     # how to run (written in Phase 6)
│
├─ backend/
│  ├─ app/
│  │  ├─ main.py                 # FastAPI app, CORS, routes
│  │  ├─ config.py               # env vars: GEMINI_API_KEY, EXCEL_PATH, thresholds, assignees
│  │  ├─ routes/
│  │  │  ├─ extract.py           # POST /api/extract
│  │  │  └─ leads.py             # POST /api/leads
│  │  ├─ services/
│  │  │  ├─ image_ops.py         # OpenCV light cleanup + sharpness score
│  │  │  ├─ gemini_client.py     # prompt + call + JSON parsing
│  │  │  ├─ normalize.py         # phone (+91), email, whitespace
│  │  │  └─ excel_store.py       # openpyxl create/append with lock handling
│  │  └─ models.py               # Pydantic request/response schemas
│  ├─ requirements.txt           # fastapi, uvicorn, google-genai, opencv-python-headless, pillow, openpyxl, python-multipart
│  └─ .env.example
│
└─ frontend/
   ├─ index.html
   ├─ src/
   │  ├─ main.jsx
   │  ├─ App.jsx                 # simple screen router (Landing / Camera / Review / Success)
   │  ├─ screens/
   │  │  ├─ Landing.jsx
   │  │  ├─ Camera.jsx           # getUserMedia + capture + upload + blur check
   │  │  ├─ Review.jsx           # form + image panel + validation
   │  │  └─ Success.jsx
   │  ├─ lib/
   │  │  ├─ api.js               # fetch wrappers
   │  │  └─ blur.js              # variance-of-Laplacian sharpness score
   │  ├─ components/             # Field, AmberHint, Spinner, Toast, AssignSelect
   │  └─ theme.css               # CARD2LEAD colors / Tailwind layer
   ├─ tailwind.config.js
   ├─ vite.config.js             # dev proxy /api -> backend
   └─ .env.example               # VITE_API_BASE
```

**Tech stack**


| Layer        | Choice                                                                    | Notes                                                                                          |
| ------------ | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Frontend     | React 18 + Vite + Tailwind                                                | Small SPA, 4 screens, no router library needed                                                 |
| Camera       | `navigator.mediaDevices.getUserMedia({video:{facingMode:"environment"}})` | Rear camera;`<input type="file" accept="image/*" capture="environment">` fallback for upload   |
| Blur check   | Plain JS Laplacian variance on a 320px downscaled canvas                  | No OpenCV.js in the browser — keeps the bundle light                                          |
| Backend      | FastAPI + Uvicorn                                                         | Async, tiny, fast to stand up                                                                  |
| Image ops    | `opencv-python-headless` + Pillow                                         | Headless = no GUI deps, smaller install                                                        |
| Vision model | Gemini**2.5 Flash** via `google-genai` SDK                                | Fast + cheap + strong English OCR;`gemini-2.0-flash` as fallback model id                      |
| Excel        | `openpyxl`                                                                | Load → append → save; header row auto-created                                                |
| Tunnel       | ngrok (or cloudflared)                                                    | One HTTPS URL for the frontend; backend stays local, reached via Vite proxy or a second tunnel |

---

## 4. API Contract

### `POST /api/extract`

**Request:** `multipart/form-data` with `image` (JPEG/PNG from camera or upload).

**Response 200:**

```json
{
  "blurry": false,
  "fields": {
    "name":    "Rahul Sharma",
    "company": "ABC Technologies",
    "title":   "Sales Director",
    "email":   "rahul@abc.com",
    "phone":   "+91 98765 43210"
  },
  "confidence": {
    "name": 98, "company": 96, "title": 72, "email": 99, "phone": 91
  }
}
```

- `blurry: true` (with empty fields) → frontend shows the retake screen.
- A field Gemini could not find → `""` and confidence `0`.
- Multiple phones/emails → `"+91 98765 43210, +91 98765 43211"`.

### `POST /api/leads`

**Request:**

```json
{
  "name": "Rahul Sharma",
  "company": "ABC Technologies",
  "title": "Sales Director",
  "email": "rahul@abc.com",
  "phone": "+91 98765 43210",
  "notes": "Met at AI conference. Interested in AI dev services.",
  "assignedTo": "HARSHAD"
}
```

**Response 200:** `{ "ok": true, "row": 42 }`
**Response 409:** `{ "ok": false, "error": "excel_locked", "message": "leads_master.xlsx is open. Close it and press Save again." }`
**Response 422:** `{ "ok": false, "error": "validation", "fields": ["title"] }`

### `GET /api/health` → `{ "ok": true }` (sanity check for ngrok wiring)

---

## 5. Key Implementation Details

### 5.1 Client-side blur gate (`frontend/src/lib/blur.js`)

- Draw the captured frame to an offscreen canvas downscaled to ~320px wide.
- Convert to grayscale, apply a 3×3 Laplacian kernel, compute the **variance** of the result.
- Low variance = few sharp edges = blurry. Start threshold **~120** (tuned on real cards in Phase 6).
- Below threshold → show `"Image looks blurry — please retake."` with only a **Retake** button. No bypass.
- The backend repeats this check as a safety net for uploaded (non-camera) images.

### 5.2 Light image cleanup (`backend/app/services/image_ops.py`)

In order: EXIF-orient → resize longest side to ~1600px → light denoise (`fastNlMeansDenoising`) → CLAHE contrast on the L channel → mild deskew (largest-text-block angle, clamp to ±10°) → re-encode JPEG q90. **No card-edge detection / perspective crop** (per your AQ7 = option A).

### 5.3 Gemini extraction (`backend/app/services/gemini_client.py`)

- Model: `gemini-2.5-flash`, `response_mime_type: application/json`, low temperature.
- Prompt gives the model the exact JSON shape and rules:
  - Return only these 5 fields + a `confidence` object (0–100 per field).
  - Empty string for anything not clearly on the card — **do not guess**.
  - Combine multiple emails/phones with `", "`.
  - Confidence reflects how clearly the value was printed/legible.
- Response parsed into the Pydantic model; a parse failure → one retry, then a friendly error to the UI.

### 5.4 Normalization (`backend/app/services/normalize.py`)

- **Phone:** keep digits only per number → strip a leading `0`, `91`, or `+91` → take the last 10 digits → format as `"+91 XXXXX XXXXX"`. Re-join multiple numbers with `", "`. If a number isn't 10 digits after cleanup, keep the best-effort value with a `+91 ` prefix and drop its confidence below 95 so it gets flagged.
- **Email:** trim + lowercase; leave as-is otherwise (user edits on review screen).

### 5.5 Review screen rules (`frontend/src/screens/Review.jsx`)

- All 5 fields + Notes + Assign are **required**. `SAVE` stays disabled until:
  - every field non-empty, **and**
  - email contains `@` and a `.` after it, **and**
  - phone has at least 10 digits.
- Fields with confidence `< 95` render with an amber border + `"Please verify"` hint; editing clears the amber.
- Empty (not-detected) fields show `"Not detected — please fill"`.
- Card image sits in a panel beside the form (stacks above the form on narrow phones).
- Assign dropdown loads from a config array `["NITISH","HARSHAD"]`; placeholder `"Select assignee"`, no default.

> Note: "Notes required" follows your `AQ1` answer ("keep every field required"). It's controlled by one flag in the code, so we can relax just Notes later without a rewrite.

### 5.6 Excel store (`backend/app/services/excel_store.py`)

- Path from `EXCEL_PATH` env var, default `./data/leads_master.xlsx`.
- If the file doesn't exist → create it with the header row.
- Columns, in order:


| Name | Company | Title | Email | Phone Number | Notes | Assigned To | Timestamp |
| ---- | ------- | ----- | ----- | ------------ | ----- | ----------- | --------- |

- `Timestamp` = server local time, `YYYY-MM-DD HH:MM:SS`.
- Append → save. If `PermissionError` (file open in Excel) → return the `409 excel_locked` response; the UI tells the user to close the file and press Save again. No data lost — they just retry.
- Duplicates are never checked — every save is a new row (your `F5`).

---

## 6. Config Knobs (env vars)


| Var                    | Where    | Default                    | Purpose                         |
| ---------------------- | -------- | -------------------------- | ------------------------------- |
| `GEMINI_API_KEY`       | backend  | —                         | Google AI Studio key            |
| `GEMINI_MODEL`         | backend  | `gemini-2.5-flash`         | swap model without code change  |
| `EXCEL_PATH`           | backend  | `./data/leads_master.xlsx` | where the master file lives     |
| `ASSIGNEES`            | backend  | `NITISH,HARSHAD`           | dropdown options (extend later) |
| `CONFIDENCE_THRESHOLD` | backend  | `95`                       | below this → amber flag        |
| `BLUR_THRESHOLD`       | frontend | `120`                      | Laplacian-variance cutoff       |
| `VITE_API_BASE`        | frontend | `/api`                     | API location (proxy in dev)     |

---

## 7. Risks & Mitigations


| Risk                                    | Impact                                  | Mitigation                                                                                                                                                   |
| --------------------------------------- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Gemini API key not ready in time        | Blocks all testing                      | Start with a personal Google AI Studio free key on Day 1; move to Antino billing later.**This is the one hard dependency — please get a key before Day 1.** |
| Blur threshold too strict/loose         | Users annoyed or bad scans slip through | `BLUR_THRESHOLD` is a single tunable value; calibrate on 5–10 real cards in Phase 6                                                                         |
| Gemini returns malformed JSON           | Extraction fails                        | `response_mime_type=application/json` + one retry + graceful UI error ("couldn't read card, try again")                                                      |
| Master`.xlsx` open in Excel during Save | Save fails                              | Detected and surfaced as a clear, recoverable message; retry succeeds                                                                                        |
| iOS Safari camera quirks                | Camera won't start on iPhone            | `playsinline` + `facingMode` fallback + the Upload option always works as plan B                                                                             |
| ngrok URL changes each restart          | Confusing to share                      | Documented in README; a reserved ngrok domain (free tier allows one static domain) removes the problem                                                       |
| Deskew rotates a good image wrongly     | Slightly worse OCR                      | Angle clamped to ±10°; skip rotation if the detected angle is tiny or uncertain                                                                            |

### QA hardening pass (done after the first build)

A round of edge-case testing (34 backend assertions + HEIC + concurrency) added:

| Area | Fix |
| ---- | --- |
| Excel formula injection | OCR/notes values starting `= + - @` are quote-prefixed so Excel can't execute them; also stops `+91 …` being mangled |
| Excel illegal chars / length | Control chars stripped, cells capped at 32,767 chars |
| Corrupt master workbook | Auto-quarantined to `*.corrupt-<ts>.xlsx`, fresh file started, capture never blocked |
| Concurrent saves | Serialised with an in-process lock (8 parallel writes → 8 clean rows) |
| Non-image / HEIC / corrupt upload | Clear `400 "use a JPEG or PNG"` instead of a misleading "blurry"; **HEIC now decoded** (`pillow-heif`) so iPhone photos work |
| Blocking event loop | Routes made sync `def` → run in Starlette's threadpool |
| Hung Gemini call | 30 s timeout (`GEMINI_TIMEOUT_MS`) + 1 s back-off before the single retry |
| Camera on plain HTTP / old browser | Explicit "needs HTTPS — use Upload" message instead of a generic failure |
| Huge / oversized phone photos | Client downscales to ≤1800 px JPEG before upload |

---

## 8. Explicitly Out of Scope (this phase)

These were discussed and deferred — noted here so expectations are clear:

- **Outlook / Microsoft login** for 5–10 users → Phase 2 (you flagged this in `AQ3`).
- **AWS / on-prem deployment** with a real domain + SSL → Phase 2; for now it's laptop + ngrok.
- **Backend API integration** with the antino.com/referral platform → Phase 3 (no API docs yet).
- **Pluggable storage layer** → not built; Excel only (`G2`).
- **Saving the card image**, raw-OCR-text column, "captured by" user, GPS/event → not now (`B6`, `E4`, `E5`).
- **Concurrent writes** to the Excel file are now safe *within the single server process* (serialised by an in-process lock — verified with 8 parallel saves). A **multi-worker / multi-machine** deployment would still need a cross-process file lock or a database (`F4`).
- **Offline / queue-and-sync** → not needed, internet always available (`H4`).
- **Multiple cards per photo**, non-English cards → not supported (`B4`, `C4`).

---

## 9. Definition of Done (this phase)

1. On a phone, open the ngrok URL → see the CARD2LEAD landing screen.
2. Tap **Open Camera**, photograph a business card (or **Upload** one).
3. A blurry shot is rejected with a Retake prompt; a sharp shot proceeds.
4. Within a few seconds the Review screen shows the 5 fields pre-filled, with the card image beside them and low-confidence fields flagged amber.
5. Edit any field; fill Notes; pick an assignee. `SAVE` enables only when everything is valid.
6. Tap **SAVE** → success screen. A new row appears in `leads_master.xlsx` with all 8 columns populated, including the timestamp.
7. Repeat capture works without reloading.
8. `README.md` explains how to start the backend, the frontend, and ngrok, where the Excel file is, and how to change the assignee list / thresholds.

---

## 10. Immediate Next Steps

1. **You:** create a Google AI Studio API key (free tier is fine) and paste it into `backend/.env` when scaffolding is ready.
2. **Me:** Phase 0 — scaffold `backend/` and `frontend/`, wire the key, get `/api/health` green through an ngrok tunnel.
3. **Me:** Phase 1 — camera + blur gate on the phone.
4. Check in at the end of Day 1 against the "Day 1 goal" above.
