# Suggestions — how we should build this

Plain-language plan based on your answers in `new_question_for_shiti.txt`.
Goal: **robust and simple**. No moving parts we don't need.

---

## 1. The big picture

We are building **one small backend** (Python/FastAPI) that sits between:

```
  Phone browser (React app)
          |
          |  login + scan a card
          v
  Our backend  ----->  Groq   (reads the card image -> name/company/etc.)
     |
     |  save the reviewed card
     v
  One Google Sheet   (all leads, with an "Event" column)

  Small local database (SQLite)  =  users, events, who-can-see-which-event, logs
```

Two kinds of storage, on purpose:


| What                              | Where                               | Why                                                                                              |
| --------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------ |
| The actual leads (card data)      | **Google Sheet**                    | You want the sales team to open a spreadsheet. Google handles the sharing.                       |
| Users, events, access rules, logs | **SQLite** (one file on the server) | These need fast, reliable lookups on every request. A spreadsheet is too slow and racy for that. |

---

## 2. Tech choices at a glance


| Area         | Choice                                                | Note                                                                                                |
| ------------ | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Language     | Python + FastAPI                                      | Keeps the code you already have in`backend/app`                                                     |
| Start point  | **Evolve the existing `backend/` project**            | Restructure into`auth / users / events / sheets / groq / logging` folders; don't start from scratch |
| Repo         | New repo under**`Shiti-Sharma09`**, same project name | Feature branch → PR, like before                                                                   |
| Metadata DB  | **SQLite**                                            | One file. Zero setup. Fine for 10–30 users.                                                        |
| LLM          | **Groq**, model name kept in config (`.env`)          | So we can change the model without touching code                                                    |
| Card storage | Google Sheet,**one file**, `Event` column             | You chose one file + a dropdown, not one file per event                                             |
| Auth         | JWT, 7-day expiry, no refresh token                   | Simple. Re-login when it expires.                                                                   |
| Frontend     | **Reuse the existing React app**                      | Add a login screen + an event dropdown; remove the "confidence" colours                             |
| Hosting      | **One small always-on server** (see section 7)        | Not Lambda — explained below                                                                       |

---

## 3. How login and permissions work

Three layers, checked on every protected request:

1. **Are you logged in?** — valid JWT token → we know your email.
2. **What is your role?** — `admin` or `user`.
3. **Are you allowed in this event?** — is there a row linking your account to this event?

Changing the event id in the URL does nothing, because step 3 is checked on the server every time.

### Roles

- **Admin** (seeded from `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env` on first run):
  creates/edits events, assigns users to events, revokes access.
- **User**: can only use events an admin has assigned to them. Assigned to **all,
  some, or none**. Access lasts **until the admin removes it**.

### One decision I need you to confirm — the login method

Your answers were slightly mixed (E2 said "OTP emailed on each login", E3 said
"self-register is good"), and **you have no email service yet** (G1). If login
needs an emailed code and email isn't working, nobody can log in.

**My recommendation (simplest that works today):**

- Users **self-register** with email + password (min 8 chars). One click, no email needed.
- **Password login** is the normal way in.
- **Email OTP is only used for "forgot password"** — added later, once we have SMTP.
- Registering only creates the account. It gives **no event access** until an
  admin assigns you. So self-register is safe.

If you actually want *passwordless* (code-to-email every login), we can do that,
but it can't ship until email works. Tell me which.

### Logout / stolen token (your E5 "not sure")

Keep it simple: the token just expires after 7 days, and logging out means the
app forgets the token. We also store a "password changed at" time, so if someone
changes their password, all their old tokens stop working. **No token blocklist**
— that's a database and cleanup job we don't need at this size.

---

## 4. Reading the card with Groq

- One Groq call per card. Model name lives in `.env` (you tested
  `qwen/qwen3.8-27b` in the playground — we'll use that, and if the API ever
  rejects it for images we change one line in `.env`, no redeploy of code logic).
- **No confidence scores** (your D2). The review screen just shows editable
  fields: Name, Company, Title, Email, Phone — plus a **Notes** box you type
  yourself.
- Non-streaming call. We wait for the full answer, clean it up (fix phone/email
  formatting), show it for review.
- **Mock mode stays**: if `GROQ_API_KEY` is empty, the app returns a fake sample
  card. Lets us build and demo the frontend without spending your daily quota.

### What Groq's free limits mean for you (important)

From the numbers you gave:


| Limit                    | Value                                       | What it means                                                       |
| ------------------------ | ------------------------------------------- | ------------------------------------------------------------------- |
| 30 requests / minute     | ~1 card every 2 seconds, across**everyone** | If 30 people scan at the exact same moment, some wait a few seconds |
| **1,000 requests / day** | **~1,000 cards per day total**              | This is the real ceiling                                            |
| 8,000 tokens / minute    | ~4–6 cards/minute of image data            | Similar effect to the 30/min limit                                  |

**If a real event could exceed ~1,000 cards in a day, the free tier will block
scans partway through.** For testing with dummy cards it's plenty. For the real
event, budget for Groq's paid tier (a few dollars) — flagging now so it's not a
surprise.

We'll add retry-with-wait so a brief spike just slows down instead of failing.

---

## 5. Saving to the Google Sheet

**One spreadsheet, one tab per event.** You create the spreadsheet by hand once
and share it with our service account (keep it shared with your email so you can
watch it). When an admin creates an event, the backend adds a **new tab** named
after that event. Rows for an event go into that event's tab. We only need the
**Google Sheets API** — not the Drive API — because we never create new
spreadsheet *files* in code, only tabs inside the one you made.

**Columns per tab** (one per field, no status column):

```
Timestamp | User Email | Event | Name | Company | Title | Email | Phone | Notes | Assigned To
```

- **Timestamp** and **User Email** come from the server (the logged-in user), never typed.
- **Event** repeats the tab name (handy if tabs are ever merged/exported).
- **Assigned To** is picked on the review screen from a list of names the
  **admin manages** (admin can add or remove names; removing a name only hides
  it from the dropdown, past rows keep it).
- No card images are stored (your C6).

### "Can't we add rows in parallel?" (your H1)

We can, but Google Sheets is not built for many programs writing at once — you
can get rate-limit errors or, rarely, two writes clashing. At 10–30 users the
actual volume is tiny (a row every few seconds at most).

**Plan:** the app forms a short **single-file line** for the ~half-second it
takes to append each row. You would never notice the wait, and it makes
duplicate rows or overwrites impossible. Each write retries up to 3 times if
Google is briefly busy. **If all retries fail, the app tells you "not saved"** —
it never shows a fake success.

This is about 15 lines of code, not a queue system. Not over-engineering.

### Double-tap protection (your H2)

The app sends a hidden "request id" with each save. If the same id arrives twice
within a few minutes (double tap, flaky network retry), the second one is
ignored. One scan = one row.

---

## 6. Where to host it (your H4 — the Lambda question)

Your answers say: **SQLite**, **single instance**, **no scaling**, **free tier**.
That points to **one small always-on server**, *not* serverless.

### Why not AWS Lambda

Lambda is "serverless" — it has **no permanent disk** and can run **many copies
at once**. That breaks two of your choices:

- **SQLite needs a real file on disk.** On Lambda it would be wiped constantly
  and different copies wouldn't share it. We'd be forced to switch to DynamoDB —
  a whole different database and a rewrite, for 30 users. That *is*
  over-engineering.
- Every request can hit a "cold start" (1–3 sec extra delay).

### Comparison


| Option                                                   | Truly free?             | Keeps SQLite?                                         | Cold start            | Setup effort               | Verdict                                  |
| -------------------------------------------------------- | ----------------------- | ----------------------------------------------------- | --------------------- | -------------------------- | ---------------------------------------- |
| **Small always-free VM** (e.g. Oracle Cloud Always Free) | Yes, ongoing            | ✅ Yes                                                | None                  | Medium (set up Linux once) | **Best fit** — matches all your answers |
| **Render.com** free web service                          | Yes (no card)           | ⚠️ Resets on each deploy + sleeps after 15 min idle | 30–60 sec after idle | Low (deploys from GitHub)  | **Good for testing now**                 |
| Google Cloud Run                                         | Yes (2M req/mo)         | ❌ No (stateless)                                     | 1–2 sec              | Medium                     | Needs a managed DB → more work          |
| AWS Lambda                                               | Yes (1M req/mo)         | ❌ No                                                 | 1–3 sec              | High                       | Needs DynamoDB rewrite → avoid          |
| Fly.io                                                   | Small free + needs card | ✅ (with volume)                                      | Fast                  | Medium                     | OK backup option                         |

### Recommendation

- **For testing with dummy cards now:** deploy to **Render free**. Fastest to a
  working public HTTPS URL. Accept that if we redeploy, events/assignments need
  re-adding (the admin is re-created automatically from `.env`; leads are safe
  because they live in the Google Sheet, not SQLite).
- **Before the real event:** move to a **small always-free VM** so nothing
  resets. Same code, just `docker run` on a server. I'll write both sets of
  deploy steps.

We package the app in a **Docker image**, so moving between hosts is easy.

---

## 7. Email / SMTP (your G1) — how to get it free, later

Not needed to start (login uses a password). We need SMTP only for
"forgot password" and the (commented-out) thank-you email.

**Easiest free option — Brevo (was Sendinblue):**

1. Sign up at brevo.com (free).
2. Go to **SMTP & API → SMTP**. It shows a host (`smtp-relay.brevo.com`), port
   `587`, a login, and an SMTP key.
3. Verify a sender email (or a domain) you own, under **Senders**.
4. Put those 4 values in `.env`. Free tier = **300 emails/day**, plenty here.

(Alternatives: Resend — 100/day free; Gmail app password — works but Google
throttles and it's not meant for app email. Brevo is the cleanest.)

---

## 8. Security must-dos (small but non-negotiable)

- **The Groq API key you pasted into the answers file is now in plain text — please
  rotate it** (generate a new one in the Groq console) and put the new one only
  in `.env`. `.env` will be git-ignored; it never goes in the repo.
- Same for the Google service-account JSON — mounted as a file/secret, never committed.
- Passwords stored hashed (bcrypt). JWT secret in `.env`.
- CORS locked to the frontend's real URL (an env variable).
- Basic rate limits (next section).
- Logs never print passwords, tokens, or keys (your requirement 11).

---

## 9. Rate limits (your H5)

Tie them to Groq's ceiling so we fail politely instead of hitting Groq's wall:


| Endpoint              | Limit                                             | Reason                                                                     |
| --------------------- | ------------------------------------------------- | -------------------------------------------------------------------------- |
| `POST /auth/login`    | 5 per minute per IP                               | Stops password guessing                                                    |
| `POST /auth/register` | 3 per minute per IP                               | Stops spam accounts                                                        |
| Card scan (Groq)      | ~25 per minute**total**, ~1,000 per day **total** | Just under Groq's 30/min and 1,000/day, so we queue/slow rather than error |
| Card scan per user    | 10 per minute                                     | One person can't hog the shared quota                                      |
| Save to Sheet         | 20 per minute per user                            | Well above real use                                                        |

If the daily Groq limit is hit, the scan screen shows a clear "daily limit
reached, try tomorrow or ask admin to upgrade" message.

---

## 10. What we are deliberately NOT building (anti-over-engineering)

- ❌ Separate spreadsheet **files** per event — one file, one **tab** per event
- ❌ A real database server (Postgres/Mongo) — SQLite is enough
- ❌ Redis / message queue / background workers — a tiny in-process lock covers Sheet writes
- ❌ Refresh tokens, token blocklist, sessions table — 7-day JWT + "password changed at"
- ❌ Serverless / autoscaling / load balancer / Kubernetes — one small server
- ❌ Confidence scores + "please verify" UI — removed (your D2)
- ❌ Storing card images — not stored (your C6)
- ❌ Drive API / creating spreadsheet files in code — you make the one file by hand; we only add tabs
- ❌ Per-event email templates — dropped (your F4)
- ❌ Load tests — skipped (your I2)

---

## 11. Build order (sequential, your I3)

1. **Project skeleton** — restructure `backend/`, config from `.env`, logging, SQLite setup.
2. **Auth** — register, login, JWT, admin seed, password hashing, rate limits.
3. **Events** — admin creates/edits events; list events.
4. **Access control** — assign/revoke users to events; the "are you allowed in this event?" check.
5. **Groq** — extraction via the Groq client, simple output shape, mock mode, retry.
6. **Google Sheet writer** — one sheet, the columns above, single-file-line + retry + real errors, idempotency.
7. **Card scan endpoint** — image in → Groq → cleaned fields out (for the review screen).
8. **Save endpoint** — reviewed fields + event → one row in the Sheet, with the user's email + timestamp.
9. **Frontend wiring** — login screen, event dropdown, attach token, remove confidence colours, point at the new backend.
10. **Docs** — Postman collection, `.env.example`, README with run + deploy steps (Render now, VM later).

Each step gets its own commit/PR so you can follow along.

---

## 12. What I need from you before step 5–6

1. **Confirm the login method** (section 3): password self-register + password
   login (my recommendation), or passwordless email code.
2. **Confirm "Event" is the new column** you meant in C4 (section 5).
3. **Create the Google side:**
   - Make a Google Cloud project (free, no billing needed for Sheets API).
   - Create a **service account**, download its JSON key.
   - Create **one Google Sheet**, share it (Editor) with the service account's
     email, and keep it shared with your own email.
   - Send me the JSON key (as a file) and the Sheet's ID.
   - *(Yes — Sheets API is free within generous quotas; we won't get near them.)*
4. **Rotate the Groq API key** and send me the new one for `.env` (don't paste it
   in a tracked file again).
5. **Pick the host for testing**: Render (fastest) or a VM you can get.

Nothing above blocks steps 1–4, so I can start on the skeleton and auth
immediately once you say go.

****---

## 13. Risks to keep in mind


| Risk                                                                   | Impact                                      | What we do about it                                                                     |
| ---------------------------------------------------------------------- | ------------------------------------------- | --------------------------------------------------------------------------------------- |
| Groq free tier = 1,000 cards/day                                       | Scans stop mid-event if exceeded            | Flag now; plan a cheap paid upgrade before the real event                               |
| Groq model`qwen/qwen3.8-27b` behaves differently via API vs playground | Extraction quality varies                   | Model name in`.env`; easy to switch; test early with real dummy cards                   |
| Render free tier resets SQLite on deploy                               | Lose events/assignments (not leads)         | Re-seed admin from`.env`; move to a VM before the event                                 |
| No SMTP yet                                                            | No "forgot password"                        | Password login works without it; add Brevo later                                        |
| Google Sheet is one shared file                                        | Anyone with the link sees all events' leads | Share it only with the people who should see it; we can split per-event later if needed |
