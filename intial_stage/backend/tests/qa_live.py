"""Live QA - HEIC support, concurrency safety, and real Gemini extraction.

Run:  ./.venv/Scripts/python.exe tests/qa_live.py
Gemini-specific checks are SKIPPED automatically if no key is set.
"""
import concurrent.futures as cf
import io
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFont
from fastapi.testclient import TestClient

import app.main

c = TestClient(app.main.app)
MOCK = c.get("/api/health").json().get("mock_mode", True)
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))


def font(sz, bold=False):
    for n in (("arialbd.ttf" if bold else "arial.ttf"), "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(n, sz)
        except OSError:
            continue
    return ImageFont.load_default()


def card_image():
    im = Image.new("RGB", (1000, 600), "#ffffff")
    d = ImageDraw.Draw(im)
    d.text((50, 60), "SKYLINE FREIGHT", font=font(44, True), fill="#111")
    d.text((50, 220), "Deepak Rao", font=font(38, True), fill="#111")
    d.text((50, 275), "Operations Manager", font=font(24), fill="#333")
    d.text((50, 360), "deepak@skylinefreight.in", font=font(22), fill="#333")
    d.text((50, 400), "+91 90042 11876", font=font(22), fill="#333")
    return im


img = card_image()

print(f"\n== mode: {'MOCK (no key)' if MOCK else 'LIVE (real Gemini)'} ==")

print("\n== HEIC upload (iPhone photos) ==")
buf = io.BytesIO()
try:
    img.save(buf, format="HEIF", quality=90)
    r = c.post("/api/extract", files={"image": ("card.heic", buf.getvalue(), "image/heic")})
    j = r.json()
    ok = r.status_code == 200 and not j.get("blurry")
    check("HEIC decoded + processed", ok, str(j.get("fields")))
except Exception as e:  # noqa: BLE001
    print(f"  [SKIP] HEIC encoder unavailable in this env: {e}")

print("\n== concurrency: 8 parallel /api/leads ==")
base = dict(name="Conc", company="Co", title="T", email="c@d.com",
            phone="+91 98765 43210", notes="parallel", assignedTo="NITISH")


def post_lead(i):
    rr = c.post("/api/leads", json={**base, "name": f"Conc{i}"})
    return rr.status_code, rr.json().get("row")


t0 = time.time()
with cf.ThreadPoolExecutor(max_workers=8) as ex:
    results = list(ex.map(post_lead, range(8)))
dt = time.time() - t0
codes = [s for s, _ in results]
rows = sorted(r for _, r in results if r)
check("8 concurrent writes -> all 200", all(s == 200 for s in codes), f"codes={codes}")
check("8 concurrent writes -> 8 distinct rows", len(set(rows)) == 8, f"rows={rows} ({dt:.1f}s)")

print("\n== real Gemini extraction ==")
if MOCK:
    print("  [SKIP] no GEMINI_API_KEY set")
else:
    b2 = io.BytesIO()
    img.save(b2, format="JPEG", quality=92)
    j = c.post("/api/extract", files={"image": ("c.jpg", b2.getvalue(), "image/jpeg")}).json()
    f = j.get("fields", {})
    check("name exact", f.get("name") == "Deepak Rao", f.get("name"))
    check("email exact", f.get("email") == "deepak@skylinefreight.in", f.get("email"))
    check("phone normalised", f.get("phone") == "+91 90042 11876", f.get("phone"))
    check("not mock", j.get("mock") is False)

try:
    os.remove(app.main.settings.excel_path)
    os.rmdir(os.path.dirname(app.main.settings.excel_path))
except OSError:
    pass

print(f"\n==== {len(PASS)} passed, {len(FAIL)} failed ====")
sys.exit(1 if FAIL else 0)
