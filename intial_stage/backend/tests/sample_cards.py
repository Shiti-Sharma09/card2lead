"""Generate a few synthetic business cards and print what Gemini extracts.

Run:  ./.venv/Scripts/python.exe tests/sample_cards.py
Use it to eyeball extraction quality and confidence scores.
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFont
from fastapi.testclient import TestClient

import app.main

c = TestClient(app.main.app)


def font(sz, bold=False):
    for n in (("arialbd.ttf" if bold else "arial.ttf"), "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(n, sz)
        except OSError:
            continue
    return ImageFont.load_default()


def render(lines, size=(1000, 560), bg="#ffffff", fg="#111111"):
    im = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(im)
    y = 50
    for text, sz, bold in lines:
        d.text((55, y), text, font=font(sz, bold), fill=fg)
        y += int(sz * 1.7)
    b = io.BytesIO()
    im.save(b, format="JPEG", quality=92)
    return b.getvalue()


CARDS = {
    "full / two phones": [
        ("NEXUS ROBOTICS", 44, True), ("Automation Solutions", 20, False),
        ("Priya Venkatesan", 34, True), ("VP, Business Development", 22, False),
        ("priya.v@nexusrobotics.io", 20, False),
        ("+91 80 4123 9876  |  +91 99860 45521", 20, False),
    ],
    "minimal / missing title+phone": [
        ("Arjun Mehta", 38, True), ("Greenfield Labs", 24, False),
        ("arjun@greenfieldlabs.com", 22, False),
    ],
    "dark background": [
        ("BRIGHTWAVE MEDIA", 40, True), ("Sana Kapoor", 34, True),
        ("Head of Partnerships", 22, False), ("sana@brightwave.media", 20, False),
        ("+91 98111 22334", 20, False),
    ],
    "name only": [("Rohan Iyer", 40, True)],
}

for label, lines in CARDS.items():
    bg, fg = ("#0f172a", "#ffffff") if "dark" in label else ("#ffffff", "#111111")
    img = render(lines, bg=bg, fg=fg)
    j = c.post("/api/extract", files={"image": ("card.jpg", img, "image/jpeg")}).json()
    print(f"\n----- {label} -----")
    if j.get("blurry"):
        print("  (rejected as blurry)")
        continue
    f, cf_ = j.get("fields", {}), j.get("confidence", {})
    for k in ("name", "company", "title", "email", "phone"):
        print(f"  {k:8} {f.get(k, '')!r:45}  conf={cf_.get(k)}")
    if j.get("mock"):
        print("  [MOCK MODE - sample data, not real extraction]")
