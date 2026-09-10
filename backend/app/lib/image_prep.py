"""Light image prep before sending to Groq: honour EXIF rotation, downscale,
re-encode as JPEG. Keeps the payload (and token count) small.

HEIC (default iPhone format) is handled via pillow-heif when available.
"""

from __future__ import annotations

import io
import logging

from PIL import Image, ImageOps

log = logging.getLogger("image")

try:  # optional — iPhone HEIC support
    import pillow_heif

    pillow_heif.register_heif_opener()
except Exception:  # pragma: no cover
    pass

MAX_DIM = 1600
JPEG_QUALITY = 85


def prepare_image(raw: bytes) -> tuple[bytes, str]:
    """Return (jpeg_bytes, mime). Falls back to the raw bytes if PIL can't
    read the file."""
    try:
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")

        w, h = img.size
        scale = MAX_DIM / max(w, h)
        if scale < 1.0:
            img = img.resize((round(w * scale), round(h * scale)), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=JPEG_QUALITY)
        return buf.getvalue(), "image/jpeg"
    except Exception as exc:  # noqa: BLE001
        log.warning("prepare_image: could not process upload (%s); using raw bytes", exc)
        return raw, "image/jpeg"
