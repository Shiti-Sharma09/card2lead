// Downscale + re-encode to JPEG before upload:
//  - keeps big phone photos under the server's size limit
//  - speeds up the upload and OCR round trip
//  - normalizes odd formats (HEIC/PNG) to JPEG when the browser can decode them
// Falls back to the original blob whenever anything is unsupported.

export async function downscaleToJpeg(input, maxSide = 1800, quality = 0.9) {
  try {
    if (typeof createImageBitmap !== 'function') return input

    const bitmap = await createImageBitmap(input).catch(() => null)
    if (!bitmap) return input

    const { width, height } = bitmap
    const scale = Math.min(1, maxSide / Math.max(width, height))
    const w = Math.max(1, Math.round(width * scale))
    const h = Math.max(1, Math.round(height * scale))

    const canvas = document.createElement('canvas')
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      bitmap.close?.()
      return input
    }
    ctx.drawImage(bitmap, 0, 0, w, h)
    bitmap.close?.()

    const out = await new Promise((resolve) =>
      canvas.toBlob((b) => resolve(b), 'image/jpeg', quality),
    )
    return out && out.size > 0 ? out : input
  } catch {
    return input
  }
}
