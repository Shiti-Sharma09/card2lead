"""Light image cleanup + a sharpness score, both backed by OpenCV.

Per the plan (AQ7 = option A) this is LIGHT only:
orient -> resize -> denoise -> CLAHE contrast -> mild deskew.
No card-edge detection / perspective crop.
"""

from __future__ import annotations

import io
import logging

import cv2
import numpy as np
from PIL import Image, ImageOps

log = logging.getLogger("card2lead.image")

# Optional HEIC/HEIF support (common on iPhones). Safe if the package is absent.
try:  # pragma: no cover - depends on optional dependency
    import pillow_heif

    pillow_heif.register_heif_opener()
    log.info("HEIC/HEIF support enabled")
except Exception:  # noqa: BLE001
    pass


def is_decodable(image_bytes: bytes) -> bool:
    """True if PIL can open the bytes as an image."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as im:
            im.verify()
        return True
    except Exception:  # noqa: BLE001
        return False


def _pil_to_cv(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def _encode_jpeg(mat: np.ndarray, quality: int = 90) -> bytes:
    ok, buf = cv2.imencode(".jpg", mat, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("Failed to JPEG-encode the processed image")
    return buf.tobytes()


def sharpness_score(image_bytes: bytes) -> float:
    """Variance of the Laplacian on a downscaled grayscale copy. Higher = sharper."""
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    gray = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        # Not a JPEG/PNG OpenCV can read (e.g. HEIC). Fall back to PIL.
        try:
            with Image.open(io.BytesIO(image_bytes)) as im:
                gray = np.array(ImageOps.exif_transpose(im).convert("L"))
        except Exception:  # noqa: BLE001
            return 0.0
    h, w = gray.shape[:2]
    scale = 1024 / max(h, w)
    if scale < 1:
        gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _estimate_skew(gray: np.ndarray) -> float:
    """Median angle of near-horizontal Hough lines, clamped to +/-10 degrees."""
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=180)
    if lines is None:
        return 0.0
    angles: list[float] = []
    for entry in lines[:120]:
        _, theta = entry[0]
        deg = np.degrees(theta) - 90.0
        if -10.0 <= deg <= 10.0:
            angles.append(deg)
    if not angles:
        return 0.0
    return float(np.median(angles))


def light_cleanup(image_bytes: bytes, max_side: int = 1600) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img).convert("RGB")
    mat = _pil_to_cv(img)

    # resize
    h, w = mat.shape[:2]
    if max(h, w) < 16:
        # too small to process meaningfully; just hand it on
        return _encode_jpeg(mat, 90)
    scale = max_side / max(h, w)
    if scale < 1:
        mat = cv2.resize(mat, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    # light denoise
    mat = cv2.fastNlMeansDenoisingColored(mat, None, 3, 3, 7, 21)

    # CLAHE contrast on the L channel only (keeps colour sane)
    lab = cv2.cvtColor(mat, cv2.COLOR_BGR2LAB)
    l_ch, a_ch, b_ch = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_ch = clahe.apply(l_ch)
    mat = cv2.cvtColor(cv2.merge((l_ch, a_ch, b_ch)), cv2.COLOR_LAB2BGR)

    # mild deskew
    gray = cv2.cvtColor(mat, cv2.COLOR_BGR2GRAY)
    angle = _estimate_skew(gray)
    if abs(angle) > 0.5:
        ch, cw = mat.shape[:2]
        rot = cv2.getRotationMatrix2D((cw / 2, ch / 2), angle, 1.0)
        mat = cv2.warpAffine(
            mat, rot, (cw, ch), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )

    return _encode_jpeg(mat, 90)
