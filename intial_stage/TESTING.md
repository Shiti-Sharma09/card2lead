# How to Test CARD2LEAD

There are two kinds of testing:

- **A. Automatic tests** — one command, the computer checks everything.
- **B. Try it yourself** — open the app and click through it.

Do A first. If it says "All good", do B.

---

## A. Automatic tests (one command)

Open PowerShell, then:

```powershell
cd "C:\Users\Shiti Sharma\OneDrive - Antino\Desktop\referral_card"
.\scripts\test-all.ps1
```

Wait ~1 minute. At the end you'll see a summary like:

```
  [PASS]  1. Code has no syntax errors
  [PASS]  2. App starts up cleanly
  [PASS]  3. Offline tests (34 checks)
  [PASS]  4. Live tests (HEIC, concurrency, real Gemini)
  [PASS]  5. Sample cards - extraction quality
  [PASS]  6. Web app builds

  All good.
```

**All 6 say `[PASS]`** → the backend, the OCR, the Excel saving, and the website
build are all working. If any says `[FAIL]`, scroll up to that section to see why.

What the 6 steps check, in plain words:

| Step | Checks that... |
|---|---|
| 1 | there are no typos that stop the code running |
| 2 | the server can start |
| 3 | phone numbers get cleaned to `+91 …`, bad photos are rejected politely, empty fields are caught, and a sneaky `=formula` in a name can't run inside Excel |
| 4 | iPhone photos (HEIC) work, 8 people saving at once don't corrupt the file, and the real Gemini reads a card correctly |
| 5 | shows you what Gemini pulled out of 4 sample cards, with a confidence score per field |
| 6 | the website compiles into its final form |

---

## B. Try it yourself

### B1. Start the app

Open **two** PowerShell windows.

Window 1:
```powershell
cd "C:\Users\Shiti Sharma\OneDrive - Antino\Desktop\referral_card"
.\scripts\start-backend.ps1
```

Window 2:
```powershell
cd "C:\Users\Shiti Sharma\OneDrive - Antino\Desktop\referral_card"
.\scripts\start-frontend.ps1
```

Leave both running. Open your browser at **http://localhost:5173**

### B2. Do one full capture (on your computer)

1. Click **Upload a photo**, choose a picture of a business card.
2. Wait for the spinner. The **Review** screen appears with the card image and
   the fields filled in.
3. Fields the OCR wasn't sure about have an **amber box** — check those.
4. Type something in **Notes**. Pick a name in **Assign**.
5. The **SAVE** button lights up only when every field is filled. Click it.
6. You see a green **"Lead saved"** screen.
7. Open the file **`backend\data\leads_master.xlsx`** — your lead is a new row.

### B3. Test it on your phone (camera)

Window 1 (stop it with Ctrl+C first if it's running):
```powershell
.\scripts\build-and-serve.ps1
```

Window 2:
```powershell
ngrok http 8000
```

ngrok prints a link like `https://abc123.ngrok-free.app`. Open **that link on
your phone**. Tap **Open Camera**, allow the camera, take a photo of a card, and
go through Review → SAVE like above.

---

## C. Things to deliberately try to break (in the app)

| Try this | It should... |
|---|---|
| Upload a PDF or a Word file | say "That file isn't a readable image. Use a JPEG or PNG photo." |
| Upload a very blurry photo | show a "too blurry" screen and make you retake |
| Use a card with no phone number | leave Phone empty with an amber "Not detected — please fill", and keep SAVE disabled until you type one |
| Use a card with two phone numbers | show both as `+91 ….., +91 …..` in one box |
| Type an email with no `@` | show a small red note and keep SAVE disabled |
| **Open** `leads_master.xlsx` in Excel, then click SAVE | say "…is open in Excel. Close it and press Save again." Close the file, click SAVE — now it works. |
| Turn on airplane mode, click SAVE | say "Network error while saving. Check your connection and retry." |

---

## D. Useful to know

| Thing | Where |
|---|---|
| Your saved leads | `backend\data\leads_master.xlsx` |
| Start over (delete all test leads) | run: `Remove-Item backend\data -Recurse -Force` |
| Error messages while it runs | the black PowerShell window (Window 1) |
| Change the Assign names / blur strictness | `backend\.env`, then restart Window 1 |
